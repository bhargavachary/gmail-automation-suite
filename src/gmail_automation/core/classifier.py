"""
Email classification engine for Gmail Automation Suite.

Provides multiple classification methods including rule-based, LLM-based,
and machine learning approaches with configurable scoring and confidence thresholds.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import logging

from ..models.email import Email, ClassificationResult
from ..core.config import Config, CategoryConfig, ScoringWeights
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Optional ML classifier import
try:
    from .ml_classifier import MLClassifierManager
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class EmailClassifierError(Exception):
    """Email classification related errors."""
    pass


class RuleBasedClassifier:
    """
    Rule-based email classifier using domain, keyword, and content matching.

    Uses configurable scoring weights and confidence thresholds to classify
    emails based on predefined rules and patterns.
    """

    def __init__(self, config: Config):
        """
        Initialize rule-based classifier.

        Args:
            config: Configuration object with categories and scoring weights
        """
        self.config = config
        self.scoring_weights = config.scoring_weights

    def classify(self, email: Email) -> Optional[ClassificationResult]:
        """
        Classify email using rule-based approach.

        Args:
            email: Email object to classify

        Returns:
            ClassificationResult if classification is confident enough, None otherwise
        """
        try:
            # Get email data for classification
            email_data = email.get_classification_data()

            # Calculate scores for each category
            category_scores = {}
            detailed_scores = {}

            for category_name, category_config in self.config.categories.items():
                score, score_details = self._calculate_category_score(email_data, category_config)
                category_scores[category_name] = score
                detailed_scores[category_name] = score_details

            # Find best category
            if not category_scores:
                return None

            best_category = max(category_scores, key=category_scores.get)
            best_score = category_scores[best_category]

            # Check confidence threshold
            if best_score < self.config.global_settings.confidence_threshold:
                logger.debug(f"Classification confidence too low: {best_score}")
                return None

            # Create classification result
            result = ClassificationResult(
                category=best_category,
                confidence=best_score,
                method="rule_based",
                scores=category_scores,
                metadata={
                    "detailed_scores": detailed_scores,
                    "threshold": self.config.global_settings.confidence_threshold,
                    "sender_domain": email_data["sender_domain"]
                }
            )

            logger.info(f"Classified email as '{best_category}' with confidence {best_score:.2f}")
            return result

        except Exception as e:
            logger.error(f"Error in rule-based classification: {e}")
            raise EmailClassifierError(f"Classification failed: {e}")

    def _calculate_category_score(self, email_data: Dict[str, str], category_config: CategoryConfig) -> Tuple[float, Dict[str, float]]:
        """
        Calculate score for a specific category.

        Args:
            email_data: Email data dictionary
            category_config: Category configuration

        Returns:
            Tuple of (total_score, detailed_scores)
        """
        score_details = {}
        total_score = 0.0

        # Domain matching
        domain_score = self._calculate_domain_score(email_data["sender_domain"], category_config.domains)
        score_details["domain"] = domain_score
        total_score += domain_score

        # Subject keyword matching
        subject_score = self._calculate_keyword_score(email_data["subject"], category_config.keywords)
        score_details["subject"] = subject_score
        total_score += subject_score

        # Content keyword matching (if enabled)
        if self.config.global_settings.enable_content_analysis:
            content_score = self._calculate_content_score(email_data["content"], category_config.keywords)
            score_details["content"] = content_score
            total_score += content_score

        # Apply exclusions
        exclusion_penalty = self._calculate_exclusion_penalty(email_data, category_config.exclusions)
        score_details["exclusion"] = exclusion_penalty
        total_score += exclusion_penalty

        # Apply negative keywords
        negative_penalty = self._calculate_negative_keyword_penalty(email_data, category_config.negative_keywords)
        score_details["negative"] = negative_penalty
        total_score += negative_penalty

        # Apply priority bonus
        priority_bonus = (10 - category_config.priority) * self.scoring_weights.priority_bonus
        score_details["priority"] = priority_bonus
        total_score += priority_bonus

        return total_score, score_details

    def _calculate_domain_score(self, sender_domain: str, domain_config: Dict[str, List[str]]) -> float:
        """Calculate score based on sender domain matching."""
        if not sender_domain:
            return 0.0

        # Check high confidence domains
        high_confidence_domains = domain_config.get("high_confidence", [])
        if any(domain.lower() in sender_domain.lower() for domain in high_confidence_domains):
            return self.scoring_weights.domain_high_confidence

        # Check medium confidence domains
        medium_confidence_domains = domain_config.get("medium_confidence", [])
        if any(domain.lower() in sender_domain.lower() for domain in medium_confidence_domains):
            return self.scoring_weights.domain_medium_confidence

        return 0.0

    def _calculate_keyword_score(self, text: str, keyword_config: Dict[str, List[str]]) -> float:
        """Calculate score based on keyword matching in subject."""
        if not text:
            return 0.0

        score = 0.0
        text_lower = text.lower() if not self.config.global_settings.case_sensitive else text

        # High priority keywords
        high_keywords = keyword_config.get("subject_high", [])
        for keyword in high_keywords:
            keyword_check = keyword.lower() if not self.config.global_settings.case_sensitive else keyword
            if keyword_check in text_lower:
                score += self.scoring_weights.subject_high

        # Medium priority keywords
        medium_keywords = keyword_config.get("subject_medium", [])
        for keyword in medium_keywords:
            keyword_check = keyword.lower() if not self.config.global_settings.case_sensitive else keyword
            if keyword_check in text_lower:
                score += self.scoring_weights.subject_medium

        return score

    def _calculate_content_score(self, content: str, keyword_config: Dict[str, List[str]]) -> float:
        """Calculate score based on keyword matching in content."""
        if not content:
            return 0.0

        score = 0.0
        content_lower = content.lower() if not self.config.global_settings.case_sensitive else content

        # High priority keywords
        high_keywords = keyword_config.get("content_high", [])
        for keyword in high_keywords:
            keyword_check = keyword.lower() if not self.config.global_settings.case_sensitive else keyword
            if keyword_check in content_lower:
                score += self.scoring_weights.content_high

        # Medium priority keywords
        medium_keywords = keyword_config.get("content_medium", [])
        for keyword in medium_keywords:
            keyword_check = keyword.lower() if not self.config.global_settings.case_sensitive else keyword
            if keyword_check in content_lower:
                score += self.scoring_weights.content_medium

        return score

    def _calculate_exclusion_penalty(self, email_data: Dict[str, str], exclusions: List[str]) -> float:
        """Calculate penalty for exclusion matches."""
        if not exclusions:
            return 0.0

        # Check all email fields for exclusions
        all_text = " ".join([
            email_data.get("subject", ""),
            email_data.get("content", ""),
            email_data.get("sender", "")
        ])

        text_check = all_text.lower() if not self.config.global_settings.case_sensitive else all_text

        for exclusion in exclusions:
            exclusion_check = exclusion.lower() if not self.config.global_settings.case_sensitive else exclusion
            if exclusion_check in text_check:
                return self.scoring_weights.exclusion_penalty

        return 0.0

    def _calculate_negative_keyword_penalty(self, email_data: Dict[str, str], negative_keywords: List[str]) -> float:
        """Calculate penalty for negative keyword matches."""
        if not negative_keywords:
            return 0.0

        penalty = 0.0
        all_text = " ".join([
            email_data.get("subject", ""),
            email_data.get("content", "")
        ])

        text_check = all_text.lower() if not self.config.global_settings.case_sensitive else all_text

        for keyword in negative_keywords:
            keyword_check = keyword.lower() if not self.config.global_settings.case_sensitive else keyword
            if keyword_check in text_check:
                penalty += self.scoring_weights.negative_keyword_penalty

        return penalty


class EmailClassifier:
    """
    Main email classification engine with multiple classification methods.

    Supports rule-based, LLM-based, and machine learning classification
    with configurable fallback strategies and confidence thresholds.
    """

    def __init__(self, config: Config, model_dir: Optional[str] = None):
        """
        Initialize email classifier.

        Args:
            config: Configuration object
            model_dir: Directory containing ML models (optional)
        """
        self.config = config
        self.rule_classifier = RuleBasedClassifier(config)

        # Initialize ML classifier if available
        if ML_AVAILABLE and model_dir:
            try:
                from pathlib import Path
                self.ml_classifier = MLClassifierManager(Path(model_dir))
                logger.info("ML classifier manager initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize ML classifier: {e}")
                self.ml_classifier = None
        else:
            self.ml_classifier = None

        # Placeholder for future classifiers
        self.llm_classifier = None

        logger.info("Email classifier initialized")

    def classify_email(self, email: Email, method: str = "rule_based") -> Optional[ClassificationResult]:
        """
        Classify a single email using specified method.

        Args:
            email: Email object to classify
            method: Classification method ("rule_based", "llm", "ml", "hybrid")

        Returns:
            ClassificationResult if successful, None otherwise
        """
        try:
            if method == "rule_based":
                return self.rule_classifier.classify(email)
            elif method == "llm":
                # Placeholder for LLM classifier
                logger.warning("LLM classifier not yet implemented")
                return None
            elif method == "ml" or method == "random_forest":
                if self.ml_classifier:
                    return self.ml_classifier.classify_email(email, "random_forest")
                else:
                    logger.warning("ML classifier not available")
                    return None
            elif method == "hybrid":
                # Try multiple methods with fallback
                return self._hybrid_classify(email)
            else:
                raise EmailClassifierError(f"Unknown classification method: {method}")

        except Exception as e:
            logger.error(f"Classification failed for email {email.metadata.message_id}: {e}")
            raise EmailClassifierError(f"Classification error: {e}")

    def classify_batch(self, emails: List[Email], method: str = "rule_based") -> List[Tuple[Email, Optional[ClassificationResult]]]:
        """
        Classify multiple emails efficiently.

        Args:
            emails: List of Email objects to classify
            method: Classification method to use

        Returns:
            List of (Email, ClassificationResult) tuples
        """
        results = []
        total_emails = len(emails)

        logger.info(f"Starting batch classification of {total_emails} emails using {method}")

        # Use batch processing for ML methods if available
        if (method == "ml" or method == "random_forest") and self.ml_classifier:
            try:
                results = self.ml_classifier.classify_batch(emails, "random_forest")
            except Exception as e:
                logger.error(f"ML batch classification failed: {e}")
                results = [(email, None) for email in emails]
        else:
            # Standard batch processing for rule-based and other methods
            for i, email in enumerate(emails, 1):
                try:
                    result = self.classify_email(email, method)
                    results.append((email, result))

                    if i % 10 == 0 or i == total_emails:
                        logger.info(f"Processed {i}/{total_emails} emails")

                except Exception as e:
                    logger.warning(f"Failed to classify email {i}: {e}")
                    results.append((email, None))

        # Log classification summary
        successful = sum(1 for _, result in results if result is not None)
        logger.info(f"Batch classification complete: {successful}/{total_emails} emails classified")

        return results

    def _hybrid_classify(self, email: Email) -> Optional[ClassificationResult]:
        """
        Hybrid classification using multiple methods with fallback.

        Args:
            email: Email to classify

        Returns:
            Best classification result
        """
        # Try rule-based first (most reliable)
        rule_result = self.rule_classifier.classify(email)
        if rule_result and rule_result.confidence >= self.config.global_settings.confidence_threshold:
            rule_result.method = "hybrid_rule"
            return rule_result

        # Future: Add LLM and ML fallbacks here
        # For now, return rule-based result even if low confidence
        if rule_result:
            rule_result.method = "hybrid_rule_low_confidence"
            return rule_result

        return None

    def get_classification_stats(self, results: List[Tuple[Email, Optional[ClassificationResult]]]) -> Dict[str, Any]:
        """
        Generate classification statistics from batch results.

        Args:
            results: List of classification results

        Returns:
            Statistics dictionary
        """
        total_emails = len(results)
        classified_count = sum(1 for _, result in results if result is not None)

        # Category distribution
        category_counts = defaultdict(int)
        confidence_scores = []

        for email, result in results:
            if result:
                category_counts[result.category] += 1
                confidence_scores.append(result.confidence)

        stats = {
            "total_emails": total_emails,
            "classified_emails": classified_count,
            "unclassified_emails": total_emails - classified_count,
            "classification_rate": classified_count / total_emails if total_emails > 0 else 0.0,
            "category_distribution": dict(category_counts),
            "average_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0,
            "confidence_range": {
                "min": min(confidence_scores) if confidence_scores else 0.0,
                "max": max(confidence_scores) if confidence_scores else 0.0
            }
        }

        return stats