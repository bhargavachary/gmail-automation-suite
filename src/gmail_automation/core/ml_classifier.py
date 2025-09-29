"""
Machine Learning classifier for Gmail Automation Suite.

Provides Random Forest and other ML-based classification methods
with support for trained models and feature extraction.
"""

import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

try:
    import joblib
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestClassifier
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from ..models.email import Email, ClassificationResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MLClassifierError(Exception):
    """Machine learning classifier related errors."""
    pass


class RandomForestEmailClassifier:
    """
    Random Forest classifier for email classification.

    Uses pre-trained Random Forest model with TF-IDF features
    for email classification based on subject and content.
    """

    def __init__(self, model_dir: Path):
        """
        Initialize Random Forest classifier.

        Args:
            model_dir: Directory containing trained model files
        """
        if not ML_AVAILABLE:
            raise MLClassifierError(
                "Machine learning dependencies not available. "
                "Install with: pip install gmail-automation-suite[ml]"
            )

        self.model_dir = model_dir
        self.model = None
        self.vectorizer = None
        self.feature_names = None
        self.label_encoder = None

        self._load_model()

    def _load_model(self) -> None:
        """Load the trained Random Forest model and components."""
        try:
            # Load the main model
            model_path = self.model_dir / "random_forest_classifier.joblib"
            if not model_path.exists():
                raise MLClassifierError(f"Model file not found: {model_path}")

            self.model = joblib.load(model_path)
            logger.info(f"Loaded Random Forest model from {model_path}")

            # Load feature names
            feature_names_path = self.model_dir / "rf_feature_names.json"
            if feature_names_path.exists():
                with open(feature_names_path, 'r') as f:
                    self.feature_names = json.load(f)
                logger.info(f"Loaded {len(self.feature_names)} feature names")

            # Try to load vectorizer if available
            vectorizer_path = self.model_dir / "tfidf_vectorizer.joblib"
            if vectorizer_path.exists():
                self.vectorizer = joblib.load(vectorizer_path)
                logger.info("Loaded TF-IDF vectorizer")
            else:
                logger.warning("TF-IDF vectorizer not found, will create new one")

            # Try to load label encoder if available
            label_encoder_path = self.model_dir / "label_encoder.joblib"
            if label_encoder_path.exists():
                self.label_encoder = joblib.load(label_encoder_path)
                logger.info("Loaded label encoder")

        except Exception as e:
            logger.error(f"Error loading Random Forest model: {e}")
            raise MLClassifierError(f"Failed to load model: {e}")

    def _extract_features(self, email: Email) -> np.ndarray:
        """
        Extract features from email for classification.

        Args:
            email: Email object to extract features from

        Returns:
            Feature vector as numpy array
        """
        try:
            # Combine text fields
            text_content = " ".join([
                email.headers.subject or "",
                email.content.combined_text or "",
                email.metadata.snippet or ""
            ]).strip()

            if not text_content:
                # Return zero vector if no content
                if self.feature_names:
                    return np.zeros(len(self.feature_names))
                else:
                    return np.zeros(1000)  # Default size

            # Use existing vectorizer or create simple features
            if self.vectorizer:
                features = self.vectorizer.transform([text_content])
                return features.toarray()[0]
            else:
                # Simple fallback feature extraction
                return self._simple_feature_extraction(text_content)

        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            # Return zero vector on error
            if self.feature_names:
                return np.zeros(len(self.feature_names))
            else:
                return np.zeros(1000)

    def _simple_feature_extraction(self, text: str) -> np.ndarray:
        """
        Simple feature extraction when vectorizer is not available.

        Args:
            text: Text content to extract features from

        Returns:
            Simple feature vector
        """
        # Basic text features
        features = []

        # Convert text to string if it's not already
        text_str = str(text).lower()

        # Length features
        features.append(len(text_str))
        features.append(len(text_str.split()))

        # Keyword presence features
        banking_keywords = ['bank', 'payment', 'transaction', 'account', 'credit', 'debit']
        shopping_keywords = ['order', 'purchase', 'delivery', 'cart', 'buy', 'shop']
        social_keywords = ['friend', 'family', 'personal', 'social', 'meeting']

        for keywords in [banking_keywords, shopping_keywords, social_keywords]:
            features.append(sum(1 for kw in keywords if kw in text_str))

        # Pad or truncate to expected size
        if self.feature_names:
            expected_size = len(self.feature_names)
            while len(features) < expected_size:
                features.append(0.0)
            features = features[:expected_size]
        else:
            # Default padding to 1000 features
            while len(features) < 1000:
                features.append(0.0)
            features = features[:1000]

        return np.array(features)

    def classify(self, email: Email) -> Optional[ClassificationResult]:
        """
        Classify email using Random Forest model.

        Args:
            email: Email object to classify

        Returns:
            ClassificationResult if successful, None otherwise
        """
        try:
            if not self.model:
                raise MLClassifierError("Model not loaded")

            # Extract features
            features = self._extract_features(email)

            # Reshape for single prediction
            features = features.reshape(1, -1)

            # Get prediction and probability
            prediction = self.model.predict(features)[0]
            probabilities = self.model.predict_proba(features)[0]

            # Get confidence (max probability)
            confidence = float(np.max(probabilities))

            # Decode label if encoder is available
            if self.label_encoder:
                try:
                    category = str(self.label_encoder.inverse_transform([prediction])[0])
                except Exception as e:
                    logger.warning(f"Label decoding failed: {e}")
                    category = str(prediction)
            else:
                category = str(prediction)

            # Create classification result
            result = ClassificationResult(
                category=category,
                confidence=confidence,
                method="random_forest",
                scores={"rf_confidence": confidence},
                metadata={
                    "model_type": "RandomForest",
                    "feature_count": len(features[0]),
                    "prediction_raw": str(prediction)
                }
            )

            logger.info(f"RF classified email as '{category}' with confidence {confidence:.3f}")
            return result

        except Exception as e:
            logger.error(f"Random Forest classification failed: {e}")
            return None

    def classify_batch(self, emails: List[Email]) -> List[Tuple[Email, Optional[ClassificationResult]]]:
        """
        Classify multiple emails efficiently.

        Args:
            emails: List of Email objects to classify

        Returns:
            List of (Email, ClassificationResult) tuples
        """
        results = []
        total_emails = len(emails)

        logger.info(f"Starting Random Forest batch classification of {total_emails} emails")

        for i, email in enumerate(emails, 1):
            try:
                result = self.classify(email)
                results.append((email, result))

                if i % 10 == 0 or i == total_emails:
                    logger.info(f"RF processed {i}/{total_emails} emails")

            except Exception as e:
                logger.warning(f"Failed to classify email {i}: {e}")
                results.append((email, None))

        successful = sum(1 for _, result in results if result is not None)
        logger.info(f"RF batch classification complete: {successful}/{total_emails} emails classified")

        return results


class MLClassifierManager:
    """
    Manager for multiple ML classifiers.

    Coordinates between different ML approaches and provides
    unified interface for machine learning classification.
    """

    def __init__(self, model_dir: Optional[Path] = None):
        """
        Initialize ML classifier manager.

        Args:
            model_dir: Directory containing trained models
        """
        self.model_dir = model_dir or Path("data/backups/20250928")
        self.rf_classifier = None

        self._initialize_classifiers()

    def _initialize_classifiers(self) -> None:
        """Initialize available ML classifiers."""
        try:
            # Try to load Random Forest classifier
            if (self.model_dir / "random_forest_classifier.joblib").exists():
                self.rf_classifier = RandomForestEmailClassifier(self.model_dir)
                logger.info("Random Forest classifier initialized")
            else:
                logger.warning(f"Random Forest model not found in {self.model_dir}")

        except Exception as e:
            logger.error(f"Error initializing ML classifiers: {e}")

    def classify_email(self, email: Email, method: str = "random_forest") -> Optional[ClassificationResult]:
        """
        Classify email using specified ML method.

        Args:
            email: Email object to classify
            method: ML method to use ("random_forest")

        Returns:
            ClassificationResult if successful, None otherwise
        """
        try:
            if method == "random_forest":
                if self.rf_classifier:
                    return self.rf_classifier.classify(email)
                else:
                    logger.warning("Random Forest classifier not available")
                    return None
            else:
                raise MLClassifierError(f"Unknown ML method: {method}")

        except Exception as e:
            logger.error(f"ML classification failed: {e}")
            return None

    def classify_batch(self, emails: List[Email], method: str = "random_forest") -> List[Tuple[Email, Optional[ClassificationResult]]]:
        """
        Classify multiple emails using specified ML method.

        Args:
            emails: List of Email objects to classify
            method: ML method to use

        Returns:
            List of (Email, ClassificationResult) tuples
        """
        try:
            if method == "random_forest":
                if self.rf_classifier:
                    return self.rf_classifier.classify_batch(emails)
                else:
                    logger.warning("Random Forest classifier not available")
                    return [(email, None) for email in emails]
            else:
                raise MLClassifierError(f"Unknown ML method: {method}")

        except Exception as e:
            logger.error(f"ML batch classification failed: {e}")
            return [(email, None) for email in emails]

    def is_available(self, method: str = "random_forest") -> bool:
        """
        Check if specified ML method is available.

        Args:
            method: ML method to check

        Returns:
            True if method is available, False otherwise
        """
        if method == "random_forest":
            return self.rf_classifier is not None
        else:
            return False

    def get_available_methods(self) -> List[str]:
        """
        Get list of available ML methods.

        Returns:
            List of available method names
        """
        methods = []
        if self.rf_classifier:
            methods.append("random_forest")
        return methods