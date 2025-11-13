"""
Behavior Analyzer Module
Tracks and analyzes user behavior for fraud detection
"""

import time
import hashlib
import numpy as np
from datetime import datetime
from models import db, BehaviorLog


class BehaviorAnalyzer:
    """
    Tracks user behavior throughout the voting process
    Collects features for AI fraud detection
    """
    
    def __init__(self):
        self.sessions = {}  # In-memory session tracking
    
    def start_session(self, voter_id, session_id, ip_address, user_agent):
        """
        Initialize behavior tracking for a new session
        
        Args:
            voter_id: Voter ID
            session_id: Session identifier
            ip_address: IP address
            user_agent: Browser user agent
        """
        device_fingerprint = self._generate_device_fingerprint(ip_address, user_agent)
        
        self.sessions[session_id] = {
            'voter_id': voter_id,
            'start_time': time.time(),
            'ip_address': ip_address,
            'user_agent': user_agent,
            'device_fingerprint': device_fingerprint,
            'registration_start': None,
            'registration_end': None,
            'survey_start': None,
            'survey_end': None,
            'voting_start': None,
            'voting_end': None,
            'page_visits': [],
            'form_corrections': 0
        }
    
    def log_registration_start(self, session_id):
        """Mark registration start time"""
        if session_id in self.sessions:
            self.sessions[session_id]['registration_start'] = time.time()
    
    def log_registration_end(self, session_id, corrections=0):
        """
        Mark registration completion
        
        Args:
            session_id: Session ID
            corrections: Number of form corrections/errors
        """
        if session_id in self.sessions:
            self.sessions[session_id]['registration_end'] = time.time()
            self.sessions[session_id]['form_corrections'] = corrections
    
    def log_survey_start(self, session_id):
        """Mark survey start time"""
        if session_id in self.sessions:
            self.sessions[session_id]['survey_start'] = time.time()
    
    def log_survey_end(self, session_id, responses):
        """
        Mark survey completion and analyze responses
        
        Args:
            session_id: Session ID
            responses: List of survey responses (1, 0, -1)
        """
        if session_id in self.sessions:
            self.sessions[session_id]['survey_end'] = time.time()
            self.sessions[session_id]['survey_responses'] = responses
    
    def log_voting_start(self, session_id):
        """Mark voting start time"""
        if session_id in self.sessions:
            self.sessions[session_id]['voting_start'] = time.time()
    
    def log_voting_end(self, session_id):
        """Mark voting completion"""
        if session_id in self.sessions:
            self.sessions[session_id]['voting_end'] = time.time()
    
    def log_page_visit(self, session_id, page_name):
        """Track page navigation pattern"""
        if session_id in self.sessions:
            self.sessions[session_id]['page_visits'].append({
                'page': page_name,
                'timestamp': time.time()
            })
    
    def calculate_metrics(self, session_id):
        """
        Calculate behavioral metrics for fraud detection
        
        Returns:
            dict: Behavioral metrics
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        metrics = {}
        
        # Registration duration
        if session['registration_start'] and session['registration_end']:
            metrics['registration_duration'] = int(
                session['registration_end'] - session['registration_start']
            )
        else:
            metrics['registration_duration'] = None
        
        # Survey duration
        if session['survey_start'] and session['survey_end']:
            metrics['survey_duration'] = int(
                session['survey_end'] - session['survey_start']
            )
            
            # Survey response variance
            if 'survey_responses' in session:
                responses = session['survey_responses']
                metrics['survey_response_variance'] = float(np.var(responses))
                metrics['survey_entropy'] = self._calculate_entropy(responses)
        else:
            metrics['survey_duration'] = None
            metrics['survey_response_variance'] = None
            metrics['survey_entropy'] = None
        
        # Voting duration
        if session['voting_start'] and session['voting_end']:
            metrics['voting_duration'] = int(
                session['voting_end'] - session['voting_start']
            )
            metrics['candidate_selection_speed'] = metrics['voting_duration'] // 3  # 3 positions
        else:
            metrics['voting_duration'] = None
            metrics['candidate_selection_speed'] = None
        
        # Total session duration
        metrics['total_session_duration'] = int(time.time() - session['start_time'])
        
        # Other metrics
        metrics['form_corrections'] = session.get('form_corrections', 0)
        metrics['ip_address'] = session['ip_address']
        metrics['device_fingerprint'] = session['device_fingerprint']
        metrics['user_agent'] = session['user_agent']
        metrics['page_navigation_pattern'] = session['page_visits']
        metrics['time_of_day'] = datetime.now().hour
        
        return metrics
    
    def save_to_database(self, voter_id, session_id):
        """
        Save behavior log to database
        
        Args:
            voter_id: Voter ID
            session_id: Session ID
        
        Returns:
            BehaviorLog: Created behavior log
        """
        metrics = self.calculate_metrics(session_id)
        
        if not metrics:
            return None
        
        behavior_log = BehaviorLog(
            voter_id=voter_id,
            session_id=session_id,
            registration_duration=metrics['registration_duration'],
            form_corrections=metrics['form_corrections'],
            survey_duration=metrics['survey_duration'],
            survey_response_variance=metrics['survey_response_variance'],
            survey_entropy=metrics['survey_entropy'],
            voting_duration=metrics['voting_duration'],
            candidate_selection_speed=metrics['candidate_selection_speed'],
            total_session_duration=metrics['total_session_duration'],
            ip_address=metrics['ip_address'],
            device_fingerprint=metrics['device_fingerprint'],
            user_agent=metrics['user_agent'],
            page_navigation_pattern=metrics['page_navigation_pattern'],
            time_of_day=metrics['time_of_day']
        )
        
        db.session.add(behavior_log)
        db.session.commit()
        
        # Clean up session
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        return behavior_log
    
    def _generate_device_fingerprint(self, ip_address, user_agent):
        """
        Generate device fingerprint from IP and user agent
        
        Args:
            ip_address: IP address
            user_agent: Browser user agent
        
        Returns:
            str: Device fingerprint hash
        """
        data = f"{ip_address}:{user_agent}".encode()
        return hashlib.sha256(data).hexdigest()[:32]
    
    def _calculate_entropy(self, values):
        """
        Calculate Shannon entropy of responses
        Low entropy = uniform/robotic
        High entropy = varied/natural
        
        Args:
            values: List of values
        
        Returns:
            float: Entropy score
        """
        if not values:
            return 0.0
        
        unique, counts = np.unique(values, return_counts=True)
        probabilities = counts / len(values)
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
        
        return float(entropy)
    
    def get_session_metrics(self, session_id):
        """
        Get current session metrics (before saving to DB)
        
        Args:
            session_id: Session ID
        
        Returns:
            dict: Current metrics
        """
        return self.calculate_metrics(session_id)


# Singleton instance
_behavior_analyzer = None

def get_behavior_analyzer():
    """Get global behavior analyzer instance"""
    global _behavior_analyzer
    if _behavior_analyzer is None:
        _behavior_analyzer = BehaviorAnalyzer()
    return _behavior_analyzer
