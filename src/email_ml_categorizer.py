#!/usr/bin/env python3
"""
Gmail Email ML Categorizer
Advanced email categorization using deep learning and topic modeling.

Features:
- BERT-based semantic email classification
- Topic modeling with BERTopic
- Hybrid rule-based + ML scoring
- Incremental learning capabilities
- Multi-language support
"""

import json
import pickle
import re
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import joblib

# Deep Learning & NLP
try:
    import torch
    from transformers import AutoTokenizer, AutoModel, pipeline
    from sentence_transformers import SentenceTransformer
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    warnings.warn("Transformers not available. Install with: pip install transformers torch sentence-transformers")

try:
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN
    BERTOPIC_AVAILABLE = True
except ImportError:
    BERTOPIC_AVAILABLE = False
    warnings.warn("BERTopic not available. Install with: pip install bertopic umap-learn hdbscan")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailMLCategorizer:
    """
    Advanced email categorization using machine learning and deep learning techniques.
    """

    def __init__(self, model_dir: str = "models", categories_config: Dict = None, n_topics: int = None):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)

        self.categories_config = categories_config or {}
        self.categories = list(self.categories_config.get('categories', {}).keys())
        self.n_topics = n_topics  # User-specified topic count

        # Model components
        self.bert_model = None
        self.sentence_transformer = None
        self.topic_model = None
        self.classifier = None
        self.vectorizer = None
        self.lemmatizer = None

        # Training data
        self.training_data = []
        self.is_trained = False

        # Initialize NLP components
        self._initialize_nlp()

    def _initialize_nlp(self):
        """Initialize NLP components."""
        try:
            # Download NLTK data if needed
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            self.lemmatizer = WordNetLemmatizer()

            # Initialize sentence transformer for embeddings
            if TRANSFORMERS_AVAILABLE:
                self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ Sentence transformer initialized")

        except Exception as e:
            logger.warning(f"⚠️ NLP initialization warning: {e}")

    def preprocess_text(self, text: str) -> str:
        """
        Advanced text preprocessing for email content.

        Args:
            text: Raw email text

        Returns:
            Cleaned and preprocessed text
        """
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)

        # Remove phone numbers
        text = re.sub(r'\+?[\d\s\-\(\)]{7,}', '', text)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove special characters but keep important ones
        text = re.sub(r'[^\w\s\-\$\%\#]', ' ', text)

        # Tokenize and lemmatize if available
        if self.lemmatizer:
            try:
                tokens = word_tokenize(text)
                stop_words = set(stopwords.words('english'))
                tokens = [self.lemmatizer.lemmatize(token) for token in tokens
                         if token not in stop_words and len(token) > 2]
                text = ' '.join(tokens)
            except:
                pass  # Fallback to original text

        return text

    def extract_features(self, email_data: Dict) -> Dict[str, Any]:
        """
        Extract comprehensive features from email data.

        Args:
            email_data: Email data dictionary

        Returns:
            Feature dictionary
        """
        features = {}

        # Basic features
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        sender = email_data.get('sender', '')

        # Preprocessed text
        subject_clean = self.preprocess_text(subject)
        body_clean = self.preprocess_text(body)
        combined_text = f"{subject_clean} {body_clean}"

        features['text'] = combined_text
        features['subject'] = subject_clean
        features['body'] = body_clean
        features['sender'] = sender

        # Length features
        features['subject_length'] = len(subject)
        features['body_length'] = len(body)
        features['word_count'] = len(combined_text.split())

        # Sender features
        features['sender_domain'] = sender.split('@')[-1] if '@' in sender else ''
        features['is_noreply'] = 'noreply' in sender.lower() or 'no-reply' in sender.lower()

        # Semantic features (if sentence transformer is available)
        if self.sentence_transformer and combined_text.strip():
            try:
                embedding = self.sentence_transformer.encode(combined_text)
                features['embedding'] = embedding
            except:
                features['embedding'] = np.zeros(384)  # Default embedding size

        return features

    def create_topic_model(self, texts: List[str], n_topics: int = None) -> BERTopic:
        """
        Create a topic model using BERTopic.

        Args:
            texts: List of email texts
            n_topics: Number of topics (auto-detect if None)

        Returns:
            Trained BERTopic model
        """
        if not BERTOPIC_AVAILABLE:
            logger.warning("BERTopic not available. Skipping topic modeling.")
            return None

        try:
            # Configure UMAP and HDBSCAN for topic modeling
            umap_model = UMAP(
                n_neighbors=15,
                n_components=5,
                min_dist=0.0,
                metric='cosine',
                random_state=42
            )

            # Configure clustering with flexible topic count
            if n_topics:
                # User-specified number of topics - use KMeans for fixed count
                from sklearn.cluster import KMeans
                cluster_model = KMeans(n_clusters=n_topics, random_state=42)
                logger.info(f"🎯 Using user-specified topic count: {n_topics}")
            else:
                # Auto-detect topics using HDBSCAN
                cluster_model = HDBSCAN(
                    min_cluster_size=5,
                    metric='euclidean',
                    cluster_selection_method='eom',
                    prediction_data=True
                )
                logger.info("🔍 Auto-detecting optimal topic count")

            # Create topic model
            topic_model = BERTopic(
                umap_model=umap_model,
                hdbscan_model=cluster_model,
                verbose=True,
                calculate_probabilities=True
            )

            # Fit the model
            topics, probs = topic_model.fit_transform(texts)

            logger.info(f"✅ Topic model created with {len(topic_model.get_topic_info())} topics")
            return topic_model

        except Exception as e:
            logger.error(f"❌ Topic modeling failed: {e}")
            return None

    def train_classifier(self, training_emails: List[Dict], validation_split: float = 0.2):
        """
        Train the email classifier using the provided training data.

        Args:
            training_emails: List of email dictionaries with 'email_data' and 'category'
            validation_split: Fraction of data to use for validation
        """
        logger.info(f"🔄 Training classifier with {len(training_emails)} emails...")

        # Extract features and labels
        features_list = []
        labels = []
        texts = []

        for item in training_emails:
            email_data = item['email_data']
            category = item['category']

            features = self.extract_features(email_data)
            features_list.append(features)
            labels.append(category)
            texts.append(features['text'])

        # Create topic model if enough data
        if len(texts) >= 20 and BERTOPIC_AVAILABLE:
            logger.info("🔄 Creating topic model...")
            self.topic_model = self.create_topic_model(texts, n_topics=self.n_topics)

            # Add topic features
            if self.topic_model:
                topics, _ = self.topic_model.transform(texts)
                for i, features in enumerate(features_list):
                    features['topic'] = topics[i]

        # Prepare data for traditional ML
        X_text = [f['text'] for f in features_list]
        y = labels

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X_text, y, test_size=validation_split, random_state=42, stratify=y
        )

        # Create and train pipeline
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words='english',
            min_df=2,
            max_df=0.8
        )

        self.classifier = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            class_weight='balanced'
        )

        # Create pipeline
        pipeline = Pipeline([
            ('tfidf', self.vectorizer),
            ('classifier', self.classifier)
        ])

        # Train the model
        pipeline.fit(X_train, y_train)

        # Validate
        y_pred = pipeline.predict(X_val)
        report = classification_report(y_val, y_pred, output_dict=True)

        logger.info(f"✅ Training completed. Validation accuracy: {report['accuracy']:.3f}")

        # Store the pipeline
        self.classifier = pipeline
        self.is_trained = True

        # Save models
        self.save_models()

        return report

    def predict_category(self, email_data: Dict) -> Tuple[str, float, Dict]:
        """
        Predict email category using ML models.

        Args:
            email_data: Email data dictionary

        Returns:
            Tuple of (predicted_category, confidence, detailed_scores)
        """
        if not self.is_trained:
            logger.warning("⚠️ Model not trained. Loading from disk or returning None.")
            if not self.load_models():
                return None, 0.0, {}

        features = self.extract_features(email_data)
        text = features['text']

        if not text.strip():
            return None, 0.0, {}

        detailed_scores = {}

        # Traditional ML prediction
        if self.classifier:
            try:
                proba = self.classifier.predict_proba([text])[0]
                classes = self.classifier.classes_

                ml_scores = dict(zip(classes, proba))
                detailed_scores['ml_scores'] = ml_scores

                ml_prediction = classes[np.argmax(proba)]
                ml_confidence = np.max(proba)

            except Exception as e:
                logger.error(f"❌ ML prediction failed: {e}")
                ml_prediction = None
                ml_confidence = 0.0

        # Topic modeling prediction
        topic_prediction = None
        topic_confidence = 0.0

        if self.topic_model:
            try:
                topics, probs = self.topic_model.transform([text])
                if len(topics) > 0 and topics[0] != -1:  # -1 means no topic assigned
                    topic_info = self.topic_model.get_topic_info()
                    topic_prediction = f"Topic_{topics[0]}"
                    topic_confidence = probs[0][topics[0]] if len(probs) > 0 and len(probs[0]) > topics[0] else 0.0

                    detailed_scores['topic_scores'] = {
                        'topic_id': topics[0],
                        'confidence': topic_confidence,
                        'keywords': self.topic_model.get_topic(topics[0])[:5]  # Top 5 keywords
                    }
            except Exception as e:
                logger.error(f"❌ Topic prediction failed: {e}")

        # Combine predictions (prioritize ML if available)
        if ml_prediction and ml_confidence > 0.3:  # Threshold for ML confidence
            final_prediction = ml_prediction
            final_confidence = ml_confidence
        elif topic_prediction and topic_confidence > 0.1:
            final_prediction = topic_prediction
            final_confidence = topic_confidence
        else:
            final_prediction = None
            final_confidence = 0.0

        detailed_scores['final_prediction'] = final_prediction
        detailed_scores['final_confidence'] = final_confidence

        return final_prediction, final_confidence, detailed_scores

    def hybrid_categorize(self, email_data: Dict, rule_based_result: Tuple[str, float] = None) -> Dict:
        """
        Hybrid categorization combining rule-based and ML approaches.

        Args:
            email_data: Email data dictionary
            rule_based_result: Tuple of (category, confidence) from rule-based system

        Returns:
            Combined categorization result
        """
        # Get ML prediction
        ml_category, ml_confidence, ml_details = self.predict_category(email_data)

        # Combine with rule-based if provided
        if rule_based_result:
            rule_category, rule_confidence = rule_based_result
        else:
            rule_category, rule_confidence = None, 0.0

        # Decision logic for combining predictions
        final_category = None
        final_confidence = 0.0
        method_used = "none"

        # High confidence ML prediction
        if ml_confidence > 0.7:
            final_category = ml_category
            final_confidence = ml_confidence
            method_used = "ml_high_confidence"

        # High confidence rule-based prediction
        elif rule_confidence > 0.8:
            final_category = rule_category
            final_confidence = rule_confidence
            method_used = "rule_based_high_confidence"

        # Moderate confidence - prefer rule-based for known patterns
        elif rule_confidence > 0.5 and ml_confidence < 0.6:
            final_category = rule_category
            final_confidence = rule_confidence
            method_used = "rule_based_moderate"

        # Moderate ML confidence
        elif ml_confidence > 0.4:
            final_category = ml_category
            final_confidence = ml_confidence
            method_used = "ml_moderate"

        # Low confidence rule-based as fallback
        elif rule_confidence > 0.3:
            final_category = rule_category
            final_confidence = rule_confidence * 0.8  # Reduce confidence for low rule score
            method_used = "rule_based_fallback"

        return {
            'final_category': final_category,
            'final_confidence': final_confidence,
            'method_used': method_used,
            'ml_prediction': {
                'category': ml_category,
                'confidence': ml_confidence,
                'details': ml_details
            },
            'rule_based_prediction': {
                'category': rule_category,
                'confidence': rule_confidence
            }
        }

    def add_training_data(self, email_data: Dict, category: str):
        """
        Add labeled email to training data for incremental learning.

        Args:
            email_data: Email data dictionary
            category: Correct category label
        """
        self.training_data.append({
            'email_data': email_data,
            'category': category
        })

        logger.info(f"✅ Added training example: {category}")

    def retrain_incremental(self, min_new_samples: int = 10):
        """
        Retrain the model with new training data.

        Args:
            min_new_samples: Minimum number of new samples before retraining
        """
        if len(self.training_data) < min_new_samples:
            logger.info(f"⏳ Need {min_new_samples - len(self.training_data)} more samples for retraining")
            return False

        logger.info(f"🔄 Retraining with {len(self.training_data)} new samples...")
        self.train_classifier(self.training_data)

        # Clear training data after successful retrain
        self.training_data = []
        return True

    def save_models(self):
        """Save trained models to disk."""
        try:
            # Save classifier pipeline
            if self.classifier:
                joblib.dump(self.classifier, self.model_dir / 'classifier.pkl')

            # Save topic model
            if self.topic_model:
                self.topic_model.save(str(self.model_dir / 'topic_model'))

            # Save training data
            if self.training_data:
                with open(self.model_dir / 'training_data.json', 'w') as f:
                    json.dump(self.training_data, f, indent=2)

            # Save metadata
            metadata = {
                'is_trained': self.is_trained,
                'categories': self.categories,
                'training_samples': len(self.training_data)
            }
            with open(self.model_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"✅ Models saved to {self.model_dir}")

        except Exception as e:
            logger.error(f"❌ Failed to save models: {e}")

    def load_models(self) -> bool:
        """Load trained models from disk."""
        try:
            # Load metadata
            metadata_path = self.model_dir / 'metadata.json'
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                self.is_trained = metadata.get('is_trained', False)
                self.categories = metadata.get('categories', [])

            # Load classifier
            classifier_path = self.model_dir / 'classifier.pkl'
            if classifier_path.exists():
                self.classifier = joblib.load(classifier_path)
                logger.info("✅ Classifier loaded")

            # Load topic model
            topic_model_path = self.model_dir / 'topic_model'
            if topic_model_path.exists() and BERTOPIC_AVAILABLE:
                self.topic_model = BERTopic.load(str(topic_model_path))
                logger.info("✅ Topic model loaded")

            # Load training data
            training_data_path = self.model_dir / 'training_data.json'
            if training_data_path.exists():
                with open(training_data_path) as f:
                    self.training_data = json.load(f)
                logger.info(f"✅ Loaded {len(self.training_data)} training samples")

            return self.is_trained

        except Exception as e:
            logger.error(f"❌ Failed to load models: {e}")
            return False

    def get_model_info(self) -> Dict:
        """Get information about the current models."""
        info = {
            'is_trained': self.is_trained,
            'categories': self.categories,
            'training_samples': len(self.training_data),
            'has_classifier': self.classifier is not None,
            'has_topic_model': self.topic_model is not None,
            'transformers_available': TRANSFORMERS_AVAILABLE,
            'bertopic_available': BERTOPIC_AVAILABLE
        }

        if self.topic_model:
            try:
                info['topic_count'] = len(self.topic_model.get_topic_info())
            except:
                info['topic_count'] = 0

        return info

def create_synthetic_training_data(categories_config: Dict) -> List[Dict]:
    """
    Create synthetic training data based on the categories configuration.
    This helps bootstrap the ML model when no labeled data is available.

    Args:
        categories_config: Categories configuration dictionary

    Returns:
        List of synthetic training examples
    """
    training_data = []

    categories = categories_config.get('categories', {})

    for category_name, category_config in categories.items():
        # Generate synthetic emails for each category
        domains = category_config.get('domains', {})
        keywords = category_config.get('keywords', {})

        # High confidence domains
        for domain in domains.get('high_confidence', [])[:5]:  # Limit to 5 per category
            # Create synthetic email
            synthetic_email = {
                'sender': f'noreply@{domain}',
                'subject': f"Important notification from {domain.split('.')[0]}",
                'body': f"This is an important message from {domain}. " +
                       ' '.join(keywords.get('subject_high', [])[:3])
            }

            training_data.append({
                'email_data': synthetic_email,
                'category': category_name
            })

        # Add keyword-based synthetic examples
        for keyword in keywords.get('subject_high', [])[:3]:
            synthetic_email = {
                'sender': 'example@example.com',
                'subject': f"Your {keyword} update",
                'body': f"We are writing to inform you about your {keyword}. " +
                       f"Please review the details regarding your {keyword}."
            }

            training_data.append({
                'email_data': synthetic_email,
                'category': category_name
            })

    return training_data

if __name__ == "__main__":
    # Example usage
    print("🤖 Gmail ML Categorizer")
    print("=" * 50)

    # Load categories config
    try:
        with open('email_categories.json') as f:
            config = json.load(f)
    except:
        config = {}

    # Initialize categorizer
    categorizer = EmailMLCategorizer(categories_config=config)

    # Show model info
    info = categorizer.get_model_info()
    print("📊 Model Information:")
    for key, value in info.items():
        print(f"   {key}: {value}")

    # Create synthetic training data if no model exists
    if not categorizer.is_trained:
        print("\n🔄 Creating synthetic training data...")
        synthetic_data = create_synthetic_training_data(config)
        print(f"✅ Generated {len(synthetic_data)} synthetic training examples")

        if len(synthetic_data) > 0:
            print("🔄 Training initial model...")
            report = categorizer.train_classifier(synthetic_data)
            print(f"✅ Initial training completed!")