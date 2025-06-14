# content_validator.py - FIXED VERSION

import re
from collections import Counter
from textblob import TextBlob

class ContentValidator:
    def __init__(self):
        # ✅ EXPANDED Topic-specific relevant keywords for each survey section
        self.topic_keywords = {
            'economic_response': [
                # Economic terms
                'economy', 'economic', 'money', 'income', 'salary', 'wage', 'price', 'cost', 'expensive', 'cheap',
                'inflation', 'deflation', 'unemployment', 'employment', 'job', 'work', 'business', 'trade', 'market',
                'tax', 'taxation', 'budget', 'debt', 'loan', 'bank', 'finance', 'financial', 'investment',
                'poverty', 'wealth', 'rich', 'poor', 'afford', 'expensive', 'currency', 'rupee', 'dollar',
                # Pakistani economic context
                'imf', 'world bank', 'exports', 'imports', 'agriculture', 'industry', 'manufacturing',
                'gdp', 'growth', 'recession', 'development', 'progress', 'economy', 'economic', 'fiscal',
                # Common related words
                'spend', 'spending', 'earn', 'earning', 'save', 'saving', 'buy', 'sell', 'purchase', 'pay', 'payment',
                # Simple sentiment words
                'good', 'bad', 'great', 'terrible', 'excellent', 'poor', 'amazing', 'awful', 'best', 'worst',
                # Urdu/Pakistani words
                'mehnga', 'mehngai', 'paisa', 'tankhwah', 'naukri', 'kaam', 'rozgar', 'acha', 'bura'
            ],
            
            'government_response': [
                # Government & politics
                'government', 'governance', 'minister', 'ministry', 'policy', 'policies', 'administration',
                'leadership', 'leader', 'prime minister', 'president', 'parliament', 'assembly', 'senate',
                'corruption', 'transparency', 'accountability', 'performance', 'management', 'decision',
                'law', 'legal', 'justice', 'court', 'judge', 'rights', 'constitution', 'democratic', 'democracy',
                # Pakistani political context
                'pti', 'pmln', 'ppp', 'party', 'election', 'vote', 'voting', 'politician', 'political',
                'nawaz', 'imran', 'bilawal', 'khan', 'sharif', 'bhutto', 'federal', 'provincial',
                # Common government words
                'public', 'service', 'official', 'department', 'office', 'minister', 'authority', 'power',
                'reform', 'change', 'improve', 'system', 'institution', 'bureaucracy',
                # Simple sentiment words
                'good', 'bad', 'great', 'terrible', 'excellent', 'poor', 'amazing', 'awful', 'best', 'worst',
                'effective', 'ineffective', 'honest', 'corrupt', 'transparent', 'opaque', 'accountable',
                # Urdu/Pakistani words
                'hukumat', 'sarkar', 'wazir', 'sifarish', 'rishwat', 'insaaf', 'acha', 'bura', 'theek'
            ],
            
            'security_response': [
                # Security & law enforcement
                'security', 'safety', 'safe', 'unsafe', 'danger', 'dangerous', 'crime', 'criminal', 'theft',
                'robbery', 'murder', 'violence', 'peaceful', 'peace', 'police', 'officer', 'law', 'order',
                'terrorism', 'terrorist', 'bomb', 'blast', 'attack', 'protection', 'guard', 'patrol',
                # Pakistani security context
                'ranger', 'army', 'military', 'border', 'afghanistan', 'india', 'kashmir', 'balochistan',
                'tribal', 'fata', 'ttp', 'law enforcement', 'intelligence', 'isi',
                # Common security words
                'secure', 'protect', 'defend', 'threat', 'risk', 'fear', 'afraid', 'worry', 'concern',
                'arrest', 'catch', 'caught', 'prisoner', 'jail', 'court', 'judge',
                # Simple sentiment words
                'good', 'bad', 'great', 'terrible', 'excellent', 'poor', 'amazing', 'awful', 'best', 'worst',
                # Urdu/Pakistani words
                'aman', 'khauf', 'dar', 'police', 'army', 'foj', 'security', 'mehfooz'
            ],
            
            'education_healthcare_response': [
                # Education terms
                'education', 'school', 'college', 'university', 'student', 'teacher', 'learning', 'study',
                'literacy', 'illiteracy', 'degree', 'qualification', 'classroom', 'books', 'curriculum',
                'academic', 'scholar', 'knowledge', 'skill', 'training', 'course', 'class',
                # Healthcare terms
                'health', 'healthcare', 'hospital', 'doctor', 'medicine', 'medical', 'treatment', 'patient',
                'disease', 'illness', 'clinic', 'nurse', 'surgery', 'emergency', 'vaccine', 'vaccination',
                'covid', 'pandemic', 'mental health', 'pharmacy', 'ambulance', 'specialist',
                # Common words
                'care', 'facility', 'service', 'quality', 'access', 'free', 'public', 'private',
                # Simple sentiment words
                'good', 'bad', 'great', 'terrible', 'excellent', 'poor', 'amazing', 'awful', 'best', 'worst',
                # Urdu/Pakistani words
                'taleem', 'sehat', 'hospital', 'doctor', 'dawai', 'ilaj', 'school', 'acha', 'bura'
            ],
            
            'infrastructure_response': [
                # Infrastructure terms
                'infrastructure', 'road', 'highway', 'bridge', 'transport', 'transportation', 'traffic',
                'electricity', 'power', 'gas', 'water', 'sewage', 'drainage', 'internet', 'network',
                'construction', 'building', 'development', 'project', 'metro', 'bus', 'train', 'railway',
                # Pakistani infrastructure context
                'cpec', 'china', 'motorway', 'islamabad', 'lahore', 'karachi', 'peshawar', 'quetta',
                'k-electric', 'wapda', 'sui gas', 'ptcl', 'load shedding', 'outage',
                # Common infrastructure words
                'build', 'repair', 'maintain', 'improve', 'upgrade', 'modern', 'facility', 'supply',
                'connect', 'connection', 'access', 'service', 'system', 'technology',
                # Simple sentiment words
                'good', 'bad', 'great', 'terrible', 'excellent', 'poor', 'amazing', 'awful', 'best', 'worst',
                # Urdu/Pakistani words
                'bijli', 'pani', 'sadak', 'load shedding', 'gas', 'acha', 'bura', 'theek'
            ],
            
            'future_expectations_response': [
                # Future & expectations
                'future', 'hope', 'hopeful', 'expect', 'expectation', 'wish', 'want', 'need', 'should',
                'will', 'would', 'could', 'next', 'coming', 'ahead', 'forward', 'progress', 'improve',
                'better', 'worse', 'change', 'reform', 'plan', 'vision', 'goal', 'target', 'priority',
                'pakistan', 'country', 'nation', 'people', 'citizen', 'society', 'community',
                # Common future words
                'tomorrow', 'years', 'time', 'long', 'term', 'development', 'growth', 'success',
                'dream', 'desire', 'achieve', 'accomplish', 'build', 'create', 'make',
                # Simple sentiment words
                'good', 'bad', 'great', 'terrible', 'excellent', 'poor', 'amazing', 'awful', 'best', 'worst',
                'positive', 'negative', 'optimistic', 'pessimistic', 'bright', 'dark',
                # Urdu/Pakistani words
                'mustaqbil', 'kal', 'umeed', 'khwab', 'tareekh', 'qaum', 'mulk', 'behtar', 'acha', 'bura'
            ]
        }
        
        # ✅ LESS STRICT - Much fewer spam patterns, focus only on obvious spam
        self.spam_patterns = [
            r'^(.)\1{10,}',  # Only very long repeated characters like aaaaaaaaaa
            r'^[0-9\s\W]{20,}$',  # Only very long strings of just numbers/symbols
            r'\b(test123|asdfgh|qwerty)\b'  # Only obvious test patterns
        ]
        
        # ✅ MUCH MORE LENIENT requirements
        self.min_word_count = 1  # Allow even single words
        self.min_relevant_words = 0  # Don't require any specific relevant words
        self.min_sentence_count = 0  # Don't require complete sentences
        
        # ✅ Common simple words that should always be accepted
        self.acceptable_simple_words = [
            'good', 'bad', 'great', 'terrible', 'excellent', 'poor', 'amazing', 'awful', 'best', 'worst',
            'yes', 'no', 'okay', 'ok', 'fine', 'nice', 'wrong', 'right', 'correct', 'incorrect',
            'happy', 'sad', 'angry', 'pleased', 'satisfied', 'disappointed', 'frustrated',
            'love', 'hate', 'like', 'dislike', 'appreciate', 'enjoy',
            'perfect', 'horrible', 'awesome', 'pathetic', 'useless', 'helpful',
            # Urdu/Pakistani simple words
            'acha', 'bura', 'theek', 'galat', 'sahi', 'ganda', 'shandar', 'bekar',
            'khush', 'naraz', 'pareshani', 'khushi', 'gam', 'dukh'
        ]

    def is_relevant_content(self, text, topic):
        """Check if the response is relevant to the given topic - MUCH MORE LENIENT"""
        if not text or len(text.strip()) < 1:
            return False, "Response is empty"
        
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        # ✅ Accept any simple acceptable word immediately
        for word in words:
            if word in self.acceptable_simple_words:
                return True, "Contains acceptable response word"
        
        # ✅ Only check for very obvious spam patterns
        for pattern in self.spam_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return False, f"Contains spam pattern"
        
        # ✅ Accept very short responses (1-3 words) more liberally
        if len(words) <= 3:
            # For very short responses, just check they're not completely random
            non_alpha_count = sum(1 for char in text_lower if not char.isalpha() and char != ' ')
            if non_alpha_count > len(text_lower) * 0.5:  # More than 50% non-alphabetic
                return False, "Too many non-alphabetic characters"
            return True, "Short response accepted"
        
        # ✅ For longer responses, check for some basic relevance
        relevant_keywords = self.topic_keywords.get(topic, [])
        relevant_word_count = 0
        
        for word in words:
            if word in relevant_keywords:
                relevant_word_count += 1
        
        # ✅ Very lenient relevance check - just need some indication of relevance OR reasonable length
        if relevant_word_count >= 1 or len(words) >= 5:
            return True, "Content appears relevant"
        
        # ✅ Check for excessive repetition only in longer responses
        if len(words) >= 5:
            word_freq = Counter(words)
            most_common_word, freq = word_freq.most_common(1)[0]
            if freq > len(words) * 0.7:  # Same word used more than 70% of the time
                return False, "Excessive word repetition detected"
        
        return True, "Content accepted"  # Default to accepting

    def analyze_content_quality(self, responses_dict):
        """Analyze the overall quality of all responses - MUCH MORE LENIENT"""
        
        quality_report = {
            'overall_valid': True,
            'total_responses': len(responses_dict),
            'valid_responses': 0,
            'invalid_responses': 0,
            'issues': [],
            'topic_validity': {},
            'quality_score': 0.0
        }
        
        valid_count = 0
        
        for topic, response in responses_dict.items():
            if response and response.strip():
                is_valid, reason = self.is_relevant_content(response, topic)
                
                quality_report['topic_validity'][topic] = {
                    'valid': is_valid,
                    'reason': reason,
                    'word_count': len(response.split()),
                    'response_length': len(response)
                }
                
                if is_valid:
                    valid_count += 1
                else:
                    quality_report['issues'].append(f"{topic}: {reason}")
            else:
                # Empty responses are marked as valid but neutral
                quality_report['topic_validity'][topic] = {
                    'valid': True,
                    'reason': "No response provided",
                    'word_count': 0,
                    'response_length': 0
                }
                valid_count += 1
        
        quality_report['valid_responses'] = valid_count
        quality_report['invalid_responses'] = len(responses_dict) - valid_count
        quality_report['quality_score'] = (valid_count / len(responses_dict)) * 100
        
        # ✅ MUCH MORE LENIENT: Accept if at least 50% of responses are valid (down from 60%)
        quality_report['overall_valid'] = quality_report['quality_score'] >= 50.0
        
        return quality_report

    def suggest_improvements(self, topic, invalid_reason):
        """Suggest how to improve invalid responses"""
        
        topic_suggestions = {
            'economic_response': "Try simple words like 'good', 'bad', 'expensive', 'cheap', or share any thought about money, jobs, or prices.",
            'government_response': "Try simple words like 'good', 'bad', 'corrupt', 'honest', or share any thought about politicians or government.",
            'security_response': "Try simple words like 'safe', 'unsafe', 'good', 'bad', or share any thought about safety or police.",
            'education_healthcare_response': "Try simple words like 'good', 'bad', 'poor', 'excellent', or share any thought about schools or hospitals.",
            'infrastructure_response': "Try simple words like 'good', 'bad', 'poor', 'excellent', or share any thought about roads, electricity, or water.",
            'future_expectations_response': "Try simple words like 'hope', 'good', 'bad', 'better', 'worse', or share any thought about Pakistan's future."
        }
        
        return topic_suggestions.get(topic, "Please provide any relevant response - even a single word like 'good' or 'bad' is acceptable.")

# ✅ Global validator instance
content_validator = ContentValidator()

def validate_survey_content(responses_dict):
    """Main function to validate survey content before saving - MUCH MORE LENIENT"""
    return content_validator.analyze_content_quality(responses_dict)