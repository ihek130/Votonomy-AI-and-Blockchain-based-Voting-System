"""
Fraud Detector Module
Main AI-driven fraud detection using Isolation Forest
"""

import os
import pickle
import numpy as np
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from models import db, BehaviorLog, FraudAlert


class FraudDetector:
    """
    AI-driven fraud detection using Isolation Forest algorithm
    Detects anomalous voting behavior in real-time
    """
    
    def __init__(self, model_path='fraud_detection/models'):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.feature_names = [
            'registration_duration',
            'form_corrections',
            'survey_duration',
            'survey_response_variance',
            'survey_entropy',
            'voting_duration',
            'candidate_selection_speed',
            'total_session_duration',
            'time_of_day'
        ]
        
        self._ensure_model_directory()
        self._load_or_initialize_model()
    
    def _ensure_model_directory(self):
        """Create model directory if it doesn't exist"""
        os.makedirs(self.model_path, exist_ok=True)
    
    def _load_or_initialize_model(self):
        """Load existing model or create new one"""
        model_file = os.path.join(self.model_path, 'isolation_forest.pkl')
        scaler_file = os.path.join(self.model_path, 'scaler.pkl')
        
        if os.path.exists(model_file) and os.path.exists(scaler_file):
            # Load existing model
            with open(model_file, 'rb') as f:
                self.model = pickle.load(f)
            with open(scaler_file, 'rb') as f:
                self.scaler = pickle.load(f)
            print("✅ Loaded existing fraud detection model")
        else:
            # Initialize new model
            self.model = IsolationForest(
                contamination=0.05,  # Expect ~5% anomalies
                random_state=42,
                n_estimators=100
            )
            self.scaler = StandardScaler()
            print("✅ Initialized new fraud detection model")
            
            # Try to train on existing data
            self._train_on_existing_data()
    
    def _train_on_existing_data(self):
        """Train model on existing behavior logs"""
        behaviors = BehaviorLog.query.limit(1000).all()  # Use recent 1000 samples
        
        if len(behaviors) < 50:
            print("⚠️  Insufficient data for training (need 50+, have {})".format(len(behaviors)))
            return
        
        # Extract features
        X = self._extract_features_from_logs(behaviors)
        
        if X is None or len(X) == 0:
            print("⚠️  No valid features extracted")
            return
        
        # Train model
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.model.fit(X_scaled)
        
        # Save model
        self._save_model()
        
        print(f"✅ Trained fraud detection model on {len(behaviors)} samples")
    
    def _extract_features_from_logs(self, behavior_logs):
        """
        Extract feature vectors from behavior logs
        
        Args:
            behavior_logs: List of BehaviorLog objects
        
        Returns:
            numpy.ndarray: Feature matrix
        """
        features = []
        
        for log in behavior_logs:
            # Skip incomplete records
            if not all([
                log.registration_duration is not None,
                log.survey_duration is not None,
                log.voting_duration is not None
            ]):
                continue
            
            feature_vector = [
                log.registration_duration or 0,
                log.form_corrections or 0,
                log.survey_duration or 0,
                log.survey_response_variance or 0,
                log.survey_entropy or 0,
                log.voting_duration or 0,
                log.candidate_selection_speed or 0,
                log.total_session_duration or 0,
                log.time_of_day or 12
            ]
            
            features.append(feature_vector)
        
        return np.array(features) if features else None
    
    def assess_behavior(self, behavior_log):
        """
        Assess individual voter behavior for anomalies
        
        Args:
            behavior_log: BehaviorLog object or dict
        
        Returns:
            dict: Risk assessment
        """
        # Extract features
        if isinstance(behavior_log, dict):
            feature_vector = [
                behavior_log.get('registration_duration', 0),
                behavior_log.get('form_corrections', 0),
                behavior_log.get('survey_duration', 0),
                behavior_log.get('survey_response_variance', 0),
                behavior_log.get('survey_entropy', 0),
                behavior_log.get('voting_duration', 0),
                behavior_log.get('candidate_selection_speed', 0),
                behavior_log.get('total_session_duration', 0),
                behavior_log.get('time_of_day', 12)
            ]
        else:
            feature_vector = [
                behavior_log.registration_duration or 0,
                behavior_log.form_corrections or 0,
                behavior_log.survey_duration or 0,
                behavior_log.survey_response_variance or 0,
                behavior_log.survey_entropy or 0,
                behavior_log.voting_duration or 0,
                behavior_log.candidate_selection_speed or 0,
                behavior_log.total_session_duration or 0,
                behavior_log.time_of_day or 12
            ]
        
        # Check for suspicious values
        red_flags = self._check_threshold_anomalies(feature_vector)
        
        # If model is trained, use it
        isolation_score = 0.0
        if self.model is not None:
            try:
                X = np.array([feature_vector])
                X_scaled = self.scaler.transform(X)
                
                # Get anomaly score (-1 = anomaly, 1 = normal)
                prediction = self.model.predict(X_scaled)[0]
                
                # Get anomaly score (lower = more anomalous)
                anomaly_score = self.model.score_samples(X_scaled)[0]
                
                # Convert to risk score (0-100)
                # Anomaly score typically ranges from -0.5 to 0.5
                # More negative = more anomalous
                isolation_score = max(0, min(100, (0.5 - anomaly_score) * 100))
                
            except Exception as e:
                print(f"Error in model prediction: {str(e)}")
                isolation_score = 0.0
        
        # Combine threshold-based and ML-based detection
        threshold_risk = len(red_flags) * 20  # Each red flag adds 20 points
        # If ML model isn't trained, rely more on threshold detection
        if isolation_score == 0.0:
            combined_risk = min(100, threshold_risk)
        else:
            combined_risk = min(100, (threshold_risk * 0.6 + isolation_score * 0.4))
        
        return {
            'risk_score': combined_risk,
            'isolation_forest_score': isolation_score,
            'threshold_risk': threshold_risk,
            'red_flags': red_flags,
            'severity': self._get_severity(combined_risk),
            'action_recommended': self._get_recommended_action(combined_risk)
        }
    
    def _check_threshold_anomalies(self, feature_vector):
        """
        Check for rule-based anomalies
        
        Args:
            feature_vector: List of feature values
        
        Returns:
            list: Red flags detected
        """
        red_flags = []
        
        reg_duration = feature_vector[0]
        form_corrections = feature_vector[1]
        survey_duration = feature_vector[2]
        survey_variance = feature_vector[3]
        survey_entropy = feature_vector[4]
        voting_duration = feature_vector[5]
        total_duration = feature_vector[7]
        
        # Registration anomalies (Adjusted for better bot detection)
        if reg_duration < 25:
            red_flags.append("Extremely fast registration (<25s)")
        elif reg_duration > 600:
            red_flags.append("Unusually slow registration (>10min)")
        
        if form_corrections > 10:
            red_flags.append("Excessive form corrections")
        
        # Survey anomalies (More sensitive)
        if survey_duration < 30:
            red_flags.append("Very fast survey completion (<30s)")
        
        if survey_variance < 0.2:
            red_flags.append("Very low survey response variance (<0.2)")
        
        if survey_entropy < 1.0:
            red_flags.append("Low survey entropy (robotic pattern)")
        
        # Voting anomalies (More sensitive)
        if voting_duration < 10:
            red_flags.append("Extremely fast voting (<10s)")
        elif voting_duration > 600:
            red_flags.append("Unusually slow voting (>10min)")
        
        # Session anomalies
        if total_duration < 60:
            red_flags.append("Suspiciously short session (<1min)")
        
        return red_flags
    
    def _get_severity(self, risk_score):
        """Get severity level from risk score"""
        if risk_score >= 85:
            return 'critical'
        elif risk_score >= 70:
            return 'high'
        elif risk_score >= 50:
            return 'medium'
        else:
            return 'low'
    
    def _get_recommended_action(self, risk_score):
        """Get recommended action based on risk score"""
        if risk_score >= 85:
            return 'block_and_alert'  # Block and notify admin immediately
        elif risk_score >= 70:
            return 'flag_for_review'  # Allow but flag for admin review
        elif risk_score >= 50:
            return 'monitor'  # Monitor closely
        else:
            return 'allow'  # Normal behavior
    
    def create_fraud_alert(self, voter_id, behavior_log, assessment):
        """
        Create fraud alert in database
        
        Args:
            voter_id: Voter ID
            behavior_log: BehaviorLog object
            assessment: Risk assessment dict
        
        Returns:
            FraudAlert: Created alert
        """
        alert = FraudAlert(
            voter_id=voter_id,
            alert_type='behavioral_anomaly',
            severity=assessment['severity'],
            risk_score=assessment['risk_score'],
            description=f"Anomalous behavior detected: {', '.join(assessment['red_flags'][:3])}",
            detected_patterns={
                'isolation_forest_score': assessment['isolation_forest_score'],
                'threshold_risk': assessment['threshold_risk'],
                'registration_duration': behavior_log.registration_duration if hasattr(behavior_log, 'registration_duration') else None,
                'survey_duration': behavior_log.survey_duration if hasattr(behavior_log, 'survey_duration') else None,
                'voting_duration': behavior_log.voting_duration if hasattr(behavior_log, 'voting_duration') else None
            },
            red_flags=assessment['red_flags'],
            status='open'
        )
        
        db.session.add(alert)
        db.session.commit()
        
        return alert
    
    def retrain_model(self):
        """
        Retrain model with latest data
        Should be run periodically (e.g., daily)
        """
        # Get recent behavior logs (last 1000)
        behaviors = BehaviorLog.query.order_by(
            BehaviorLog.created_at.desc()
        ).limit(1000).all()
        
        if len(behaviors) < 50:
            print("⚠️  Insufficient data for retraining")
            return False
        
        # Extract features
        X = self._extract_features_from_logs(behaviors)
        
        if X is None or len(X) < 50:
            print("⚠️  Insufficient valid features")
            return False
        
        # Retrain
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.model.fit(X_scaled)
        
        # Save updated model
        self._save_model()
        
        print(f"✅ Retrained fraud detection model on {len(behaviors)} samples")
        return True
    
    def _save_model(self):
        """Save model and scaler to disk"""
        model_file = os.path.join(self.model_path, 'isolation_forest.pkl')
        scaler_file = os.path.join(self.model_path, 'scaler.pkl')
        
        with open(model_file, 'wb') as f:
            pickle.dump(self.model, f)
        
        with open(scaler_file, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        print("✅ Saved fraud detection model")
    
    def get_statistics(self):
        """Get fraud detection statistics"""
        total_logs = BehaviorLog.query.count()
        total_alerts = FraudAlert.query.count()
        open_alerts = FraudAlert.query.filter_by(status='open').count()
        critical_alerts = FraudAlert.query.filter_by(severity='critical').count()
        
        return {
            'total_behavior_logs': total_logs,
            'total_alerts': total_alerts,
            'open_alerts': open_alerts,
            'critical_alerts': critical_alerts,
            'model_trained': self.model is not None
        }


# Singleton instance
_fraud_detector = None

def get_fraud_detector():
    """Get global fraud detector instance"""
    global _fraud_detector
    if _fraud_detector is None:
        _fraud_detector = FraudDetector()
    return _fraud_detector
