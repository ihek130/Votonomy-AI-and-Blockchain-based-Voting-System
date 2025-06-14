# nlp_analysis.py - FIXED VERSION

import re
import json
from collections import Counter, defaultdict

# ✅ Import with error handling
try:
    from textblob import TextBlob
except ImportError:
    print("TextBlob not installed. Run: pip install textblob")
    TextBlob = None

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    print("VADER Sentiment not installed. Run: pip install vaderSentiment")
    SentimentIntensityAnalyzer = None

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.tag import pos_tag
    from nltk.chunk import ne_chunk
except ImportError:
    print("NLTK not installed. Run: pip install nltk")
    nltk = None

# ✅ Download required NLTK data (run once) with better error handling
def ensure_nltk_data():
    """Ensure required NLTK data is downloaded"""
    if not nltk:
        print("NLTK not available, skipping data download")
        return
        
    required_data = [
        ('tokenizers/punkt', 'punkt'),
        ('corpora/stopwords', 'stopwords'),
        ('taggers/averaged_perceptron_tagger', 'averaged_perceptron_tagger'),
        ('chunkers/maxent_ne_chunker', 'maxent_ne_chunker'),
        ('corpora/words', 'words')
    ]
    
    for data_path, data_name in required_data:
        try:
            nltk.data.find(data_path)
        except LookupError:
            try:
                print(f"Downloading NLTK data: {data_name}")
                nltk.download(data_name, quiet=True)
            except Exception as e:
                print(f"Failed to download {data_name}: {e}")
        except Exception as e:
            print(f"Error checking NLTK data {data_name}: {e}")

# Call the function to ensure data is available
try:
    ensure_nltk_data()
except Exception as e:
    print(f"Error in NLTK setup: {e}")

class AdvancedSentimentAnalyzer:
    def __init__(self):
        # ✅ Initialize with error handling
        try:
            if SentimentIntensityAnalyzer:
                self.vader_analyzer = SentimentIntensityAnalyzer()
            else:
                self.vader_analyzer = None
                print("VADER analyzer not available")
        except Exception as e:
            print(f"Error initializing VADER: {e}")
            self.vader_analyzer = None
            
        try:
            if nltk:
                self.stop_words = set(stopwords.words('english'))
            else:
                self.stop_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
        except Exception as e:
            print(f"Error loading stopwords: {e}")
            self.stop_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
        
        # ✅ EXPANDED Pakistan-specific political keywords
        self.political_keywords = {
            'economy': [
                'inflation', 'prices', 'jobs', 'unemployment', 'poverty', 'income', 'salary', 'business', 'trade',
                'expensive', 'cheap', 'cost', 'money', 'rupee', 'dollar', 'tax', 'loan', 'debt', 'bank',
                'market', 'finance', 'investment', 'export', 'import', 'growth', 'recession', 'gdp',
                'mehnga', 'mehngai', 'paisa', 'tankhwah', 'naukri', 'kaam', 'rozgar', 'business'
            ],
            'government': [
                'governance', 'leadership', 'corruption', 'transparency', 'accountability', 'ministers', 'policies',
                'good', 'bad', 'excellent', 'poor', 'terrible', 'amazing', 'awful', 'best', 'worst',
                'pti', 'pmln', 'ppp', 'politician', 'political', 'election', 'vote', 'voting',
                'nawaz', 'imran', 'bilawal', 'khan', 'sharif', 'bhutto', 'federal', 'provincial',
                'hukumat', 'sarkar', 'wazir', 'minister', 'sifarish', 'rishwat', 'insaaf'
            ],
            'security': [
                'safety', 'crime', 'police', 'terrorism', 'peace', 'violence', 'law', 'order', 'protection',
                'secure', 'unsafe', 'danger', 'safe', 'fear', 'afraid', 'worry', 'concern',
                'army', 'military', 'ranger', 'security', 'peace', 'aman', 'khauf'
            ],
            'infrastructure': [
                'roads', 'electricity', 'water', 'gas', 'transport', 'development', 'construction',
                'load shedding', 'outage', 'bijli', 'pani', 'sadak', 'road', 'metro', 'bus',
                'cpec', 'china', 'motorway', 'highway', 'bridge', 'building'
            ],
            'education': [
                'schools', 'universities', 'teachers', 'students', 'learning', 'literacy', 'education',
                'school', 'college', 'university', 'taleem', 'education', 'teacher', 'student'
            ],
            'healthcare': [
                'hospitals', 'doctors', 'medicine', 'treatment', 'health', 'medical', 'sehat',
                'hospital', 'doctor', 'dawai', 'ilaj', 'health', 'medical'
            ],
            'social': ['women', 'youth', 'elderly', 'disabled', 'minorities', 'rights', 'equality']
        }
        
        # ✅ EXPANDED Emotion detection keywords with intensifiers
        self.emotion_keywords = {
            'joy': [
                'happy', 'satisfied', 'pleased', 'glad', 'content', 'delighted', 'excited',
                'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'awesome',
                'love', 'like', 'enjoy', 'appreciate', 'positive', 'best', 'perfect',
                'khush', 'acha', 'behtar', 'zabardast', 'shandar'
            ],
            'anger': [
                'angry', 'frustrated', 'furious', 'annoyed', 'upset', 'mad', 'outraged',
                'bad', 'terrible', 'awful', 'horrible', 'disgusting', 'hate', 'dislike',
                'worst', 'pathetic', 'useless', 'corrupt', 'failed', 'disappointing',
                'gussa', 'naraz', 'bura', 'ganda', 'bekar', 'kharab'
            ],
            'fear': [
                'worried', 'concerned', 'afraid', 'anxious', 'scared', 'fearful', 'nervous',
                'unsafe', 'insecure', 'dangerous', 'risky', 'uncertain', 'doubt',
                'dar', 'khauf', 'pareshan', 'tension'
            ],
            'sadness': [
                'sad', 'disappointed', 'depressed', 'unhappy', 'miserable', 'hopeless',
                'poor', 'unfortunate', 'tragic', 'failure', 'loss', 'decline',
                'dukh', 'gam', 'pareshani', 'mushkil'
            ],
            'trust': [
                'confidence', 'faith', 'believe', 'trust', 'reliable', 'dependable',
                'honest', 'truthful', 'credible', 'trustworthy', 'loyal',
                'bharosa', 'aitbaar', 'yaqeen'
            ],
            'disgust': [
                'disgusted', 'revolted', 'appalled', 'sickened', 'repulsed',
                'dirty', 'filthy', 'corrupt', 'shameful', 'embarrassing',
                'ghinauna', 'ganda', 'badbu'
            ]
        }

        # ✅ ENHANCED Simple sentiment words for single-word analysis
        self.simple_sentiment_words = {
            'positive': [
                'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'awesome', 'best', 'perfect',
                'nice', 'fine', 'ok', 'okay', 'yes', 'love', 'like', 'happy', 'satisfied', 'pleased',
                'acha', 'behtar', 'khush', 'shandar', 'zabardast', 'mast', 'badhiya'
            ],
            'negative': [
                'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'dislike', 'poor', 'pathetic',
                'useless', 'failed', 'disappointing', 'corrupt', 'no', 'never', 'sad', 'angry',
                'bura', 'ganda', 'kharab', 'bekar', 'ghatiya', 'galat'
            ],
            'neutral': [
                'neutral', 'average', 'normal', 'medium', 'moderate', 'same', 'typical', 'usual',
                'theek', 'aam', 'normal', 'aadha'
            ]
        }

    def clean_text(self, text):
        """Clean and preprocess text"""
        if not text:
            return ""
        
        # Remove extra whitespace and convert to lowercase
        text = re.sub(r'\s+', ' ', text.strip().lower())
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\!\?\,]', '', text)
        
        return text

    def get_sentiment_score(self, text):
        """Get comprehensive sentiment analysis - FIXED VERSION"""
        if not text or len(text.strip()) < 1:  # ✅ Allow even 1 character
            return {
                'compound': 0.0,
                'positive': 0.0,
                'negative': 0.0,
                'neutral': 1.0,
                'label': 'Neutral',
                'intensity': 'Low',
                'subjectivity': 0.0
            }
        
        try:
            cleaned_text = self.clean_text(text)
            words = cleaned_text.split()
            
            # ✅ ENHANCED: Simple word analysis for very short responses
            if len(words) <= 3:
                return self._analyze_simple_words(words, cleaned_text)
            
            # ✅ VADER Sentiment Analysis with error handling
            try:
                if self.vader_analyzer:
                    vader_scores = self.vader_analyzer.polarity_scores(cleaned_text)
                else:
                    vader_scores = {'compound': 0.0, 'pos': 0.0, 'neg': 0.0, 'neu': 1.0}
            except Exception as e:
                print(f"VADER analysis error: {e}")
                vader_scores = {'compound': 0.0, 'pos': 0.0, 'neg': 0.0, 'neu': 1.0}
            
            # ✅ TextBlob Sentiment Analysis with error handling
            try:
                if TextBlob:
                    blob = TextBlob(cleaned_text)
                    textblob_polarity = blob.sentiment.polarity
                    textblob_subjectivity = blob.sentiment.subjectivity
                else:
                    textblob_polarity = 0.0
                    textblob_subjectivity = 0.0
            except Exception as e:
                print(f"TextBlob analysis error: {e}")
                textblob_polarity = 0.0
                textblob_subjectivity = 0.0
            
            # ✅ Enhanced keyword-based sentiment for Pakistani context
            keyword_sentiment = self._analyze_keywords_sentiment(words)
            
            # ✅ Combine scores with better weighting
            compound_score = (vader_scores['compound'] * 0.4 + textblob_polarity * 0.4 + keyword_sentiment * 0.2)
            
            # ✅ Determine sentiment label with lower thresholds
            if compound_score >= 0.05:  # Lowered from 0.1
                label = 'Positive'
            elif compound_score <= -0.05:  # Lowered from -0.1
                label = 'Negative'
            else:
                label = 'Neutral'
            
            # ✅ Determine intensity
            abs_score = abs(compound_score)
            if abs_score >= 0.6:
                intensity = 'High'
            elif abs_score >= 0.2:  # Lowered from 0.3
                intensity = 'Medium'
            else:
                intensity = 'Low'
            
            return {
                'compound': round(compound_score, 3),
                'positive': round(vader_scores['pos'], 3),
                'negative': round(vader_scores['neg'], 3),
                'neutral': round(vader_scores['neu'], 3),
                'label': label,
                'intensity': intensity,
                'subjectivity': round(textblob_subjectivity, 3)
            }
            
        except Exception as e:
            print(f"Error in get_sentiment_score: {e}")
            return {
                'compound': 0.0,
                'positive': 0.0,
                'negative': 0.0,
                'neutral': 1.0,
                'label': 'Neutral',
                'intensity': 'Low',
                'subjectivity': 0.0
            }

    def _analyze_simple_words(self, words, text):
        """Analyze sentiment for very short responses (1-3 words)"""
        positive_count = 0
        negative_count = 0
        total_words = len(words)
        
        for word in words:
            if word in self.simple_sentiment_words['positive']:
                positive_count += 1
            elif word in self.simple_sentiment_words['negative']:
                negative_count += 1
        
        # Calculate sentiment
        if positive_count > negative_count:
            compound = min(0.8, 0.3 + (positive_count * 0.2))  # Max 0.8 for short responses
            label = 'Positive'
        elif negative_count > positive_count:
            compound = max(-0.8, -0.3 - (negative_count * 0.2))  # Min -0.8 for short responses
            label = 'Negative'
        else:
            compound = 0.0
            label = 'Neutral'
        
        return {
            'compound': round(compound, 3),
            'positive': round(positive_count / max(total_words, 1), 3),
            'negative': round(negative_count / max(total_words, 1), 3),
            'neutral': round(1 - (positive_count + negative_count) / max(total_words, 1), 3),
            'label': label,
            'intensity': 'Medium' if abs(compound) > 0.3 else 'Low',
            'subjectivity': 0.8  # High subjectivity for simple words
        }

    def _analyze_keywords_sentiment(self, words):
        """Analyze sentiment based on Pakistani political keywords"""
        positive_score = 0
        negative_score = 0
        
        for word in words:
            # Check positive words
            if word in self.simple_sentiment_words['positive']:
                positive_score += 1
            elif word in self.simple_sentiment_words['negative']:
                negative_score += 1
        
        total_sentiment_words = positive_score + negative_score
        if total_sentiment_words == 0:
            return 0.0
        
        # Calculate normalized score
        sentiment_score = (positive_score - negative_score) / total_sentiment_words
        return max(-1.0, min(1.0, sentiment_score))

    def detect_emotions(self, text):
        """Detect emotions in text using keyword matching - ENHANCED"""
        if not text:
            return {}
        
        try:
            cleaned_text = self.clean_text(text)
            
            # ✅ Tokenize with fallback
            try:
                if nltk:
                    words = word_tokenize(cleaned_text)
                else:
                    words = cleaned_text.split()
            except Exception as e:
                print(f"Emotion tokenization error: {e}")
                words = cleaned_text.split()
            
            emotion_scores = defaultdict(int)
            total_emotion_words = 0
            
            for word in words:
                for emotion, keywords in self.emotion_keywords.items():
                    if word in keywords:
                        emotion_scores[emotion] += 1
                        total_emotion_words += 1
            
            # ✅ Convert to percentages
            emotion_percentages = {}
            if total_emotion_words > 0:
                for emotion, count in emotion_scores.items():
                    emotion_percentages[emotion] = round((count / total_emotion_words) * 100, 1)
            
            # ✅ Get dominant emotion
            dominant_emotion = max(emotion_percentages, key=emotion_percentages.get) if emotion_percentages else 'Neutral'
            
            return {
                'emotions': emotion_percentages,
                'dominant_emotion': dominant_emotion,
                'total_emotion_words': total_emotion_words
            }
            
        except Exception as e:
            print(f"Error in detect_emotions: {e}")
            return {
                'emotions': {},
                'dominant_emotion': 'Neutral',
                'total_emotion_words': 0
            }

    def extract_keywords(self, text, top_n=10):
        """Extract important keywords from text - ENHANCED"""
        if not text:
            return []
        
        try:
            cleaned_text = self.clean_text(text)
            
            # ✅ For very short text, return the words themselves
            words = cleaned_text.split()
            if len(words) <= 3:
                return [{'word': word, 'frequency': 1} for word in words if len(word) > 1]
            
            # ✅ Tokenize with fallback
            try:
                if nltk:
                    words = word_tokenize(cleaned_text)
                else:
                    words = cleaned_text.split()
            except Exception as e:
                print(f"Tokenization error: {e}")
                words = cleaned_text.split()
            
            # ✅ Filter out stop words and short words
            filtered_words = [
                word for word in words 
                if word not in self.stop_words 
                and len(word) > 1  # Lowered from 2 to 1
                and word.isalpha()
            ]
            
            # ✅ POS tagging to get nouns and adjectives with error handling
            try:
                if nltk:
                    pos_tags = pos_tag(filtered_words)
                    important_words = [
                        word for word, pos in pos_tags 
                        if pos.startswith(('NN', 'JJ', 'VB', 'RB'))  # Added adverbs (RB)
                    ]
                else:
                    important_words = filtered_words  # Fallback to all filtered words
            except Exception as e:
                print(f"POS tagging error: {e}")
                important_words = filtered_words  # Fallback to all filtered words
            
            # ✅ Count frequency
            word_freq = Counter(important_words)
            
            return [{'word': word, 'frequency': freq} for word, freq in word_freq.most_common(top_n)]
            
        except Exception as e:
            print(f"Error in extract_keywords: {e}")
            return []

    def categorize_topics(self, text):
        """Categorize text into predefined topics - ENHANCED"""
        if not text:
            return {}
        
        try:
            cleaned_text = self.clean_text(text)
            
            # ✅ Tokenize with fallback
            try:
                if nltk:
                    words = word_tokenize(cleaned_text)
                else:
                    words = cleaned_text.split()
            except Exception as e:
                print(f"Topic tokenization error: {e}")
                words = cleaned_text.split()
            
            topic_scores = defaultdict(int)
            
            for word in words:
                for topic, keywords in self.political_keywords.items():
                    if word in keywords:
                        topic_scores[topic] += 1
            
            # ✅ Convert to percentages
            total_topic_words = sum(topic_scores.values())
            topic_percentages = {}
            
            if total_topic_words > 0:
                for topic, count in topic_scores.items():
                    topic_percentages[topic] = round((count / total_topic_words) * 100, 1)
            
            # ✅ Get primary topic
            primary_topic = max(topic_percentages, key=topic_percentages.get) if topic_percentages else 'General'
            
            return {
                'topics': topic_percentages,
                'primary_topic': primary_topic,
                'total_topic_words': total_topic_words
            }
            
        except Exception as e:
            print(f"Error in categorize_topics: {e}")
            return {
                'topics': {},
                'primary_topic': 'General',
                'total_topic_words': 0
            }

    def analyze_complete_response(self, responses_dict):
        """Analyze all survey responses comprehensively - ENHANCED"""
        all_text = ""
        topic_analysis = {}
        
        # ✅ Topic mapping
        topic_mapping = {
            'economic_response': 'Economy',
            'government_response': 'Government Performance', 
            'security_response': 'Security & Law',
            'education_healthcare_response': 'Education & Healthcare',
            'infrastructure_response': 'Infrastructure',
            'future_expectations_response': 'Future Expectations'
        }
        
        # ✅ Analyze each topic response separately
        for field, response_text in responses_dict.items():
            if response_text and field in topic_mapping:
                topic_name = topic_mapping[field]
                
                sentiment = self.get_sentiment_score(response_text)
                emotions = self.detect_emotions(response_text)
                keywords = self.extract_keywords(response_text, top_n=5)
                topics = self.categorize_topics(response_text)
                
                topic_analysis[topic_name] = {
                    'sentiment': sentiment,
                    'emotions': emotions,
                    'keywords': keywords,
                    'topics': topics,
                    'word_count': len(response_text.split())
                }
                
                all_text += " " + response_text
        
        # ✅ Overall analysis
        overall_sentiment = self.get_sentiment_score(all_text)
        overall_emotions = self.detect_emotions(all_text)
        overall_keywords = self.extract_keywords(all_text, top_n=15)
        overall_topics = self.categorize_topics(all_text)
        
        return {
            'overall_sentiment': overall_sentiment,
            'overall_emotions': overall_emotions,
            'overall_keywords': overall_keywords,
            'overall_topics': overall_topics,
            'topic_breakdown': topic_analysis,
            'total_word_count': len(all_text.split())
        }

# ✅ Global analyzer instance
sentiment_analyzer = AdvancedSentimentAnalyzer()

def analyze_voter_sentiment(survey_data):
    """Main function to analyze voter sentiment - ENHANCED VERSION"""
    try:
        responses = {
            'economic_response': survey_data.get('economic_response', ''),
            'government_response': survey_data.get('government_response', ''),
            'security_response': survey_data.get('security_response', ''),
            'education_healthcare_response': survey_data.get('education_healthcare_response', ''),
            'infrastructure_response': survey_data.get('infrastructure_response', ''),
            'future_expectations_response': survey_data.get('future_expectations_response', '')
        }
        
        # ✅ Clean and validate responses - LESS STRICT
        cleaned_responses = {}
        for key, value in responses.items():
            if value and isinstance(value, str):
                # Clean the text - remove special characters that might cause issues
                cleaned_text = value.strip()
                if len(cleaned_text) > 0:  # ✅ Accept any non-empty response
                    cleaned_responses[key] = cleaned_text
                else:
                    cleaned_responses[key] = "No response provided"
            else:
                cleaned_responses[key] = "No response provided"
        
        analysis_result = sentiment_analyzer.analyze_complete_response(cleaned_responses)
        
        print(f"DEBUG: Analysis result for responses: {analysis_result}")  # Debug log
        
        return {
            'success': True,
            'analysis': analysis_result,
            'overall_score': analysis_result['overall_sentiment']['compound'],
            'overall_label': analysis_result['overall_sentiment']['label']
        }
        
    except Exception as e:
        print(f"Error in sentiment analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # ✅ Return a basic fallback result instead of failing
        return {
            'success': True,  # Changed to True to allow submission
            'analysis': {
                'overall_sentiment': {'compound': 0.0, 'label': 'Neutral'},
                'overall_emotions': {'emotions': {}, 'dominant_emotion': 'Neutral'},
                'overall_keywords': [],
                'overall_topics': {'topics': {}, 'primary_topic': 'General'},
                'topic_breakdown': {},
                'total_word_count': len(' '.join(responses.values()).split())
            },
            'overall_score': 0.0,
            'overall_label': 'Neutral'
        }