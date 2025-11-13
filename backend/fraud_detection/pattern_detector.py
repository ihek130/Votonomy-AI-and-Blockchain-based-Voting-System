"""
Pattern Detector Module
Detects coordinated voting attacks through multi-factor clustering
Context-aware for Pakistan's scale (220M population)
"""

import numpy as np
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from models import db, Vote, PreSurvey, IPCluster, FraudAlert, BehaviorLog, Voter


class PatternDetector:
    """
    Detects coordinated voting patterns using multi-factor analysis
    Scale-appropriate for Pakistan's 220M population
    """
    
    def __init__(self):
        # Realistic thresholds for Pakistan's scale
        self.config = {
            'minimum_cluster_size': 50,  # Need at least 50 votes to analyze
            'ip_concentration_threshold': 0.8,  # 80%+ from few IPs
            'geographic_clustering_threshold': 0.3,  # 70%+ from same district
            'survey_similarity_threshold': 0.9,  # 90%+ identical responses
            'timing_uniformity_threshold': 30,  # All within 30 seconds
            'behavior_uniformity_threshold': 0.85,  # 85%+ identical behavior
            'recent_registration_threshold': 0.7,  # 70%+ registered recently
            'minimum_red_flags': 4,  # Must have 4+ suspicious factors
            'critical_risk_threshold': 85  # Only alert if score > 85
        }
    
    def analyze_recent_votes(self, window_minutes=10):
        """
        Analyze votes in recent time window for coordinated patterns
        
        Args:
            window_minutes: Time window to analyze (default 10 minutes)
        
        Returns:
            list: Detected suspicious clusters
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_votes = Vote.query.filter(Vote.created_at >= cutoff_time).all()
        
        if len(recent_votes) < self.config['minimum_cluster_size']:
            return []  # Too few votes to analyze
        
        # Group votes by candidate
        clusters = self._group_by_candidate(recent_votes)
        
        suspicious_clusters = []
        
        for candidate_id, votes in clusters.items():
            if len(votes) < self.config['minimum_cluster_size']:
                continue  # Skip small clusters
            
            # Analyze cluster with multi-factor approach
            analysis = self._analyze_cluster(votes)
            
            if analysis['risk_score'] >= self.config['critical_risk_threshold']:
                suspicious_clusters.append({
                    'candidate_id': candidate_id,
                    'vote_count': len(votes),
                    'analysis': analysis,
                    'voter_ids': [v.voter_id for v in votes]
                })
                
                # Create fraud alert
                self._create_coordination_alert(candidate_id, votes, analysis)
        
        return suspicious_clusters
    
    def _group_by_candidate(self, votes):
        """Group votes by candidate ID"""
        clusters = defaultdict(list)
        for vote in votes:
            clusters[vote.candidate_id].append(vote)
        return dict(clusters)
    
    def _analyze_cluster(self, votes):
        """
        Multi-factor cluster analysis
        Requires MULTIPLE red flags, not just one
        
        Args:
            votes: List of Vote objects
        
        Returns:
            dict: Analysis results with risk score and red flags
        """
        analysis = {
            'size': len(votes),
            'ip_diversity': self._calculate_ip_diversity(votes),
            'geographic_spread': self._calculate_geographic_spread(votes),
            'timing_variance': self._calculate_timing_variance(votes),
            'survey_similarity': self._calculate_survey_similarity(votes),
            'registration_recency': self._check_recent_registrations(votes),
            'behavior_uniformity': self._calculate_behavior_uniformity(votes),
            'red_flags': [],
            'risk_score': 0
        }
        
        # Calculate risk score based on multiple factors
        risk_details = self._calculate_coordination_risk(analysis)
        analysis['risk_score'] = risk_details['score']
        analysis['red_flags'] = risk_details['red_flags']
        
        return analysis
    
    def _calculate_ip_diversity(self, votes):
        """
        Calculate IP address diversity
        Low diversity = suspicious (many votes from few IPs)
        High diversity = normal (votes from many IPs)
        
        Returns:
            float: 0-1 diversity score
        """
        # Get IP addresses from behavior logs
        voter_ids = [v.voter_id for v in votes]
        behaviors = BehaviorLog.query.filter(BehaviorLog.voter_id.in_(voter_ids)).all()
        
        if not behaviors:
            return 1.0  # No data, assume normal
        
        ips = [b.ip_address for b in behaviors if b.ip_address]
        
        if not ips:
            return 1.0
        
        unique_ips = len(set(ips))
        total = len(ips)
        
        diversity = unique_ips / total if total > 0 else 1.0
        
        return diversity
    
    def _calculate_geographic_spread(self, votes):
        """
        Calculate geographic diversity from CNIC patterns
        CNIC format: XXXXX-YYYYYYY-Z (first 5 = district code)
        
        Returns:
            float: 0-1 spread score
        """
        voter_ids = [v.voter_id for v in votes]
        voters = Voter.query.filter(Voter.voter_id.in_(voter_ids)).all()
        
        if not voters:
            return 1.0  # No data, assume normal
        
        # Extract district codes from CNICs
        districts = []
        for voter in voters:
            if voter.id_card and len(voter.id_card) >= 5:
                district = voter.id_card[:5]
                districts.append(district)
        
        if not districts:
            return 1.0
        
        unique_districts = len(set(districts))
        total = len(districts)
        
        spread = unique_districts / total if total > 0 else 1.0
        
        return spread
    
    def _calculate_timing_variance(self, votes):
        """
        Calculate variance in vote timing
        Low variance = suspicious (all votes at same time)
        High variance = normal (natural spread)
        
        Returns:
            float: Variance in seconds
        """
        timestamps = [v.created_at.timestamp() for v in votes]
        
        if len(timestamps) < 2:
            return 600.0  # Assume normal spread
        
        variance = float(np.var(timestamps))
        
        return variance
    
    def _calculate_survey_similarity(self, votes):
        """
        Calculate similarity of survey responses across voters
        High similarity = suspicious (copy-paste responses)
        Low similarity = normal (people have different opinions)
        
        Returns:
            float: 0-1 similarity score
        """
        voter_ids = [v.voter_id for v in votes]
        surveys = PreSurvey.query.filter(PreSurvey.voter_id.in_(voter_ids)).all()
        
        if len(surveys) < 2:
            return 0.0  # Not enough data
        
        # Extract response vectors
        response_vectors = []
        for survey in surveys:
            vector = [
                survey.economy_satisfaction, survey.economy_inflation_impact,
                survey.government_performance, survey.government_corruption,
                survey.security_safety, survey.security_law_order,
                survey.education_quality, survey.healthcare_access,
                survey.infrastructure_roads, survey.infrastructure_utilities,
                survey.future_optimism, survey.future_confidence
            ]
            response_vectors.append(vector)
        
        # Calculate pairwise cosine similarity
        similarities = []
        for i in range(len(response_vectors)):
            for j in range(i+1, len(response_vectors)):
                sim = self._cosine_similarity(response_vectors[i], response_vectors[j])
                similarities.append(sim)
        
        if not similarities:
            return 0.0
        
        avg_similarity = float(np.mean(similarities))
        
        return avg_similarity
    
    def _check_recent_registrations(self, votes):
        """
        Check what percentage registered recently (potential bulk registration)
        
        Returns:
            float: 0-1 percentage of recent registrations
        """
        voter_ids = [v.voter_id for v in votes]
        voters = Voter.query.filter(Voter.voter_id.in_(voter_ids)).all()
        
        if not voters:
            return 0.0
        
        # Consider "recent" as last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        # Note: Voter model may not have created_at, this is best-effort
        # If not available, check vote creation time as proxy
        recent_count = 0
        for vote in votes:
            if vote.created_at >= cutoff:
                recent_count += 1
        
        percentage = recent_count / len(votes) if votes else 0.0
        
        return percentage
    
    def _calculate_behavior_uniformity(self, votes):
        """
        Calculate behavioral uniformity across voters
        High uniformity = suspicious (robotic behavior)
        Low uniformity = normal (human variance)
        
        Returns:
            float: 0-1 uniformity score
        """
        voter_ids = [v.voter_id for v in votes]
        behaviors = BehaviorLog.query.filter(BehaviorLog.voter_id.in_(voter_ids)).all()
        
        if len(behaviors) < 2:
            return 0.0  # Not enough data
        
        # Extract behavioral features
        features = []
        for b in behaviors:
            if all([b.registration_duration, b.survey_duration, b.voting_duration]):
                features.append([
                    b.registration_duration,
                    b.survey_duration,
                    b.voting_duration,
                    b.total_session_duration
                ])
        
        if len(features) < 2:
            return 0.0
        
        features = np.array(features)
        
        # Calculate coefficient of variation (CV) for each feature
        # Low CV = uniform (suspicious), High CV = varied (normal)
        cvs = []
        for col in range(features.shape[1]):
            mean_val = np.mean(features[:, col])
            std_val = np.std(features[:, col])
            cv = std_val / mean_val if mean_val > 0 else 0
            cvs.append(cv)
        
        avg_cv = np.mean(cvs)
        uniformity = 1 - min(avg_cv, 1.0)  # Convert to uniformity score
        
        return float(uniformity)
    
    def _calculate_coordination_risk(self, cluster_analysis):
        """
        Calculate risk score from multiple factors
        Requires 4+ red flags to be considered suspicious
        
        Args:
            cluster_analysis: Dict with cluster metrics
        
        Returns:
            dict: Risk score and red flags
        """
        risk_score = 0
        red_flags = []
        
        # 1. IP Concentration (20% weight)
        ip_concentration = 1 - cluster_analysis['ip_diversity']
        if ip_concentration > self.config['ip_concentration_threshold']:
            risk_score += 20
            red_flags.append(f"High IP concentration ({ip_concentration:.2f})")
        
        # 2. Geographic Clustering (15% weight)
        if cluster_analysis['geographic_spread'] < self.config['geographic_clustering_threshold']:
            risk_score += 15
            red_flags.append(f"Geographic clustering ({cluster_analysis['geographic_spread']:.2f})")
        
        # 3. Timing Uniformity (15% weight)
        if cluster_analysis['timing_variance'] < self.config['timing_uniformity_threshold']:
            risk_score += 15
            red_flags.append(f"Mechanically uniform timing ({cluster_analysis['timing_variance']:.0f}s variance)")
        
        # 4. Survey Similarity (20% weight)
        if cluster_analysis['survey_similarity'] > self.config['survey_similarity_threshold']:
            risk_score += 20
            red_flags.append(f"Nearly identical surveys ({cluster_analysis['survey_similarity']:.2f})")
        
        # 5. Recent Registrations (15% weight)
        if cluster_analysis['registration_recency'] > self.config['recent_registration_threshold']:
            risk_score += 15
            red_flags.append(f"Bulk recent registrations ({cluster_analysis['registration_recency']:.2f})")
        
        # 6. Behavioral Uniformity (10% weight)
        if cluster_analysis['behavior_uniformity'] > self.config['behavior_uniformity_threshold']:
            risk_score += 10
            red_flags.append(f"Robotic behavior patterns ({cluster_analysis['behavior_uniformity']:.2f})")
        
        # 7. Cluster Size Bonus (5% weight)
        if cluster_analysis['size'] > 100:
            risk_score += 5
            red_flags.append(f"Large suspicious cluster (n={cluster_analysis['size']})")
        
        # CRITICAL: Reduce score if insufficient red flags
        if len(red_flags) < self.config['minimum_red_flags']:
            risk_score *= 0.3  # Heavily penalize if < 4 factors
            red_flags.append(f"Only {len(red_flags)} red flags (need {self.config['minimum_red_flags']}+)")
        
        return {
            'score': min(risk_score, 100),
            'red_flags': red_flags
        }
    
    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        return float(similarity)
    
    def _create_coordination_alert(self, candidate_id, votes, analysis):
        """
        Create fraud alert for coordinated attack
        
        Args:
            candidate_id: Candidate receiving coordinated votes
            votes: List of suspicious votes
            analysis: Analysis results
        """
        voter_ids = [v.voter_id for v in votes[:10]]  # Sample first 10
        
        alert = FraudAlert(
            voter_id=None,  # Cluster-level alert
            alert_type='coordinated_attack',
            severity='critical' if analysis['risk_score'] > 90 else 'high',
            risk_score=analysis['risk_score'],
            description=f"Coordinated voting pattern detected for {candidate_id}",
            detected_patterns={
                'candidate_id': candidate_id,
                'cluster_size': analysis['size'],
                'ip_diversity': analysis['ip_diversity'],
                'geographic_spread': analysis['geographic_spread'],
                'survey_similarity': analysis['survey_similarity'],
                'timing_variance': analysis['timing_variance']
            },
            red_flags=analysis['red_flags'],
            status='open'
        )
        
        db.session.add(alert)
        db.session.commit()
    
    def update_ip_clusters(self):
        """
        Update IP cluster tracking for all votes
        Run periodically to maintain cluster statistics
        """
        # Get all unique IPs from behavior logs
        behaviors = BehaviorLog.query.all()
        ip_groups = defaultdict(list)
        
        for behavior in behaviors:
            if behavior.ip_address:
                ip_groups[behavior.ip_address].append(behavior)
        
        for ip_address, behaviors_list in ip_groups.items():
            # Get or create cluster
            cluster = IPCluster.query.filter_by(ip_address=ip_address).first()
            
            if not cluster:
                cluster = IPCluster(ip_address=ip_address)
                db.session.add(cluster)
            
            # Update statistics
            cluster.voter_count = len(set(b.voter_id for b in behaviors_list))
            cluster.updated_at = datetime.utcnow()
            
            # Get votes from these voters
            voter_ids = [b.voter_id for b in behaviors_list]
            votes = Vote.query.filter(Vote.voter_id.in_(voter_ids)).all()
            
            if len(votes) >= 2:
                # Calculate cluster metrics
                cluster.vote_similarity_score = self._calculate_vote_similarity(votes)
                cluster.timing_variance = self._calculate_timing_variance(votes)
                cluster.survey_similarity = self._calculate_survey_similarity(votes)
                
                # Get voters for geographic analysis
                voters = Voter.query.filter(Voter.voter_id.in_(voter_ids)).all()
                cluster.geographic_spread = self._calculate_geographic_spread_from_voters(voters)
                
                # Assess coordination risk
                mini_analysis = {
                    'ip_diversity': 0.1,  # By definition, same IP
                    'geographic_spread': cluster.geographic_spread,
                    'timing_variance': cluster.timing_variance,
                    'survey_similarity': cluster.survey_similarity,
                    'registration_recency': 0.0,
                    'behavior_uniformity': 0.0,
                    'size': len(votes)
                }
                
                risk = self._calculate_coordination_risk(mini_analysis)
                cluster.coordination_score = risk['score']
                
                # Update risk assessment
                if cluster.coordination_score > 85:
                    cluster.risk_assessment = 'fraud'
                    cluster.flagged_at = datetime.utcnow()
                elif cluster.coordination_score > 60:
                    cluster.risk_assessment = 'suspicious'
                    cluster.flagged_at = datetime.utcnow()
                else:
                    cluster.risk_assessment = 'normal'
        
        db.session.commit()
    
    def _calculate_vote_similarity(self, votes):
        """Calculate similarity of candidate choices"""
        if len(votes) < 2:
            return 0.0
        
        # Count most common candidate per position
        position_votes = defaultdict(list)
        for vote in votes:
            position_votes[vote.position].append(vote.candidate_id)
        
        similarities = []
        for position, candidates in position_votes.items():
            counter = Counter(candidates)
            most_common_count = counter.most_common(1)[0][1] if counter else 0
            similarity = most_common_count / len(candidates) if candidates else 0
            similarities.append(similarity)
        
        return float(np.mean(similarities)) if similarities else 0.0
    
    def _calculate_geographic_spread_from_voters(self, voters):
        """Calculate geographic spread from Voter objects"""
        if not voters:
            return 1.0
        
        districts = []
        for voter in voters:
            if voter.id_card and len(voter.id_card) >= 5:
                district = voter.id_card[:5]
                districts.append(district)
        
        if not districts:
            return 1.0
        
        unique_districts = len(set(districts))
        total = len(districts)
        
        return unique_districts / total if total > 0 else 1.0


# Singleton instance
_pattern_detector = None

def get_pattern_detector():
    """Get global pattern detector instance"""
    global _pattern_detector
    if _pattern_detector is None:
        _pattern_detector = PatternDetector()
    return _pattern_detector
