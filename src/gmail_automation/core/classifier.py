"""
Email classification engine for Gmail Automation Suite.

Provides multiple classification methods including rule-based, LLM-based,
and machine learning approaches with configurable scoring and confidence thresholds.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models.email import Email, ClassificationResult
from ..core.config import Config, CategoryConfig, ScoringWeights
from ..core.email_cache import EmailCache
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

    def __init__(self, config: Config, model_dir: Optional[str] = None, cache_dir: Optional[Path] = None):
        """
        Initialize email classifier.

        Args:
            config: Configuration object
            model_dir: Directory containing ML models (optional)
            cache_dir: Directory for email cache (optional)
        """
        self.config = config
        self.rule_classifier = RuleBasedClassifier(config)

        # Initialize email cache
        if cache_dir:
            self.cache = EmailCache(cache_dir)
        else:
            # Default cache location
            default_cache = Path("data") / "cache"
            self.cache = EmailCache(default_cache)

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

        logger.info("Email classifier initialized with caching enabled")

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

    def classify_batch(self, emails: List[Email], method: str = "rule_based", use_cache: bool = True) -> List[Tuple[Email, Optional[ClassificationResult]]]:
        """
        Classify multiple emails efficiently with caching support.

        Args:
            emails: List of Email objects to classify
            method: Classification method to use
            use_cache: Whether to use cached results and store new classifications

        Returns:
            List of (Email, ClassificationResult) tuples
        """
        results = []
        total_emails = len(emails)
        cached_count = 0
        new_classifications = 0

        logger.info(f"Starting batch classification of {total_emails} emails using {method} (cache: {use_cache})")

        # Separate cached and uncached emails
        emails_to_process = []
        if use_cache:
            for email in emails:
                cached_result = self.cache.get_cached_classification(email.metadata.message_id)
                if cached_result:
                    # Use cached result
                    category, confidence = cached_result
                    result = ClassificationResult(
                        category=category,
                        confidence=confidence,
                        method=f"{method}_cached"
                    )
                    results.append((email, result))
                    cached_count += 1
                else:
                    emails_to_process.append(email)
        else:
            emails_to_process = emails

        logger.info(f"Found {cached_count} cached results, processing {len(emails_to_process)} new emails")

        # Process uncached emails
        if emails_to_process:
            # Use batch processing for ML methods if available
            if (method == "ml" or method == "random_forest") and self.ml_classifier:
                try:
                    new_results = self.ml_classifier.classify_batch(emails_to_process, "random_forest")
                    results.extend(new_results)
                    new_classifications = len([r for _, r in new_results if r is not None])
                except Exception as e:
                    logger.error(f"ML batch classification failed: {e}")
                    new_results = [(email, None) for email in emails_to_process]
                    results.extend(new_results)
            else:
                # Multithreaded batch processing for rule-based and other methods
                max_workers = min(8, len(emails_to_process))
                logger.info(f"Using {max_workers} threads for classification")

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all classification tasks
                    future_to_email = {
                        executor.submit(self._classify_email_thread_safe, email, method): email
                        for email in emails_to_process
                    }

                    # Collect results as they complete
                    processed_count = 0
                    for future in as_completed(future_to_email):
                        email = future_to_email[future]
                        try:
                            result = future.result()
                            results.append((email, result))
                            if result:
                                new_classifications += 1

                            processed_count += 1
                            if processed_count % 10 == 0 or processed_count == len(emails_to_process):
                                logger.info(f"Processed {processed_count}/{len(emails_to_process)} new emails")

                        except Exception as e:
                            logger.warning(f"Failed to classify email: {e}")
                            results.append((email, None))

            # Store new classifications in cache
            if use_cache:
                for email, result in results[cached_count:]:  # Only new results
                    try:
                        self.cache.store_email(email, result, method)
                    except Exception as e:
                        logger.warning(f"Failed to cache email {email.metadata.message_id}: {e}")

        # Log classification summary
        successful = sum(1 for _, result in results if result is not None)
        logger.info(f"Batch classification complete: {successful}/{total_emails} emails classified "
                   f"({cached_count} from cache, {new_classifications} newly classified)")

        return results

    def classify_batch_from_message_ids(self, gmail_client, message_ids: List[str], method: str = "rule_based", use_cache: bool = True, apply_labels: bool = False, batch_size: int = 100) -> List[Tuple[Email, Optional[ClassificationResult]]]:
        """
        Classify emails from message IDs efficiently, checking cache before fetching emails.
        This is much faster than fetching all emails first then checking cache.

        Args:
            gmail_client: Gmail client instance
            message_ids: List of Gmail message IDs
            method: Classification method to use
            use_cache: Whether to use cached results and store new classifications
            apply_labels: Whether to apply labels incrementally after each batch
            batch_size: Number of emails to process before applying labels (default: 100)

        Returns:
            List of (Email, ClassificationResult) tuples
        """
        results = []
        total_emails = len(message_ids)
        cached_count = 0
        new_classifications = 0
        total_labeled = 0

        logger.info(f"Starting efficient batch classification of {total_emails} emails using {method} (cache: {use_cache}, apply_labels: {apply_labels})")

        # Filter out already labeled messages if we're applying labels
        if apply_labels and use_cache:
            logger.info("Filtering out already-labeled messages...")
            unlabeled_ids = [mid for mid in message_ids if not self.cache.is_labeled(mid)]
            already_labeled = len(message_ids) - len(unlabeled_ids)
            if already_labeled > 0:
                logger.info(f"Skipping {already_labeled} already-labeled emails")
                total_labeled = already_labeled
            message_ids = unlabeled_ids

        if not message_ids:
            logger.info("All emails are already labeled!")
            return results

        # Separate cached and uncached message IDs
        message_ids_to_fetch = []
        cached_results = []

        if use_cache:
            logger.info("Checking cache for all message IDs...")
            for message_id in message_ids:
                cached_result = self.cache.get_cached_classification(message_id)
                if cached_result:
                    # Store cached result with placeholder email (we'll need minimal email data)
                    category, confidence = cached_result
                    result = ClassificationResult(
                        category=category,
                        confidence=confidence,
                        method=f"{method}_cached"
                    )
                    cached_results.append((message_id, result))
                    cached_count += 1
                else:
                    message_ids_to_fetch.append(message_id)
        else:
            message_ids_to_fetch = message_ids

        logger.info(f"Found {cached_count} cached results, need to fetch {len(message_ids_to_fetch)} emails")

        # Fetch only uncached emails
        emails_to_process = []
        if message_ids_to_fetch:
            logger.info(f"Fetching {len(message_ids_to_fetch)} uncached emails from Gmail...")
            emails_to_process = list(gmail_client.get_messages_batch(message_ids_to_fetch))
            logger.info(f"Successfully fetched {len(emails_to_process)} emails")

        # Process uncached emails
        new_results = []
        if emails_to_process:
            # Use the existing batch classification logic for new emails
            if (method == "ml" or method == "random_forest") and self.ml_classifier:
                try:
                    new_results = self.ml_classifier.classify_batch(emails_to_process, "random_forest")
                    new_classifications = len([r for _, r in new_results if r is not None])
                except Exception as e:
                    logger.error(f"ML batch classification failed: {e}")
                    new_results = [(email, None) for email in emails_to_process]
            else:
                # Multithreaded batch processing for rule-based and other methods
                max_workers = min(8, len(emails_to_process))
                logger.info(f"Using {max_workers} threads for classification")

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all classification tasks
                    future_to_email = {
                        executor.submit(self._classify_email_thread_safe, email, method): email
                        for email in emails_to_process
                    }

                    # Collect results as they complete
                    processed_count = 0
                    for future in as_completed(future_to_email):
                        email = future_to_email[future]
                        try:
                            result = future.result()
                            new_results.append((email, result))
                            if result:
                                new_classifications += 1

                            processed_count += 1
                            if processed_count % 10 == 0 or processed_count == len(emails_to_process):
                                logger.info(f"Processed {processed_count}/{len(emails_to_process)} new emails")

                        except Exception as e:
                            logger.warning(f"Failed to classify email: {e}")
                            new_results.append((email, None))

            # Store new classifications in cache
            if use_cache:
                for email, result in new_results:
                    try:
                        self.cache.store_email(email, result, method)
                    except Exception as e:
                        logger.warning(f"Failed to cache email {email.metadata.message_id}: {e}")

        # For cached results, only fetch minimal data if we're NOT applying labels
        # (if applying labels, we don't need to return all the cached emails)
        if cached_results and not apply_labels:
            logger.info(f"Fetching minimal email data for {len(cached_results)} cached results...")
            cached_message_ids = [msg_id for msg_id, _ in cached_results]
            result_map = {msg_id: result for msg_id, result in cached_results}

            # Fetch emails in batches with progress tracking
            fetched_count = 0
            fetch_batch_size = 100
            for i in range(0, len(cached_message_ids), fetch_batch_size):
                batch_ids = cached_message_ids[i:i + fetch_batch_size]
                try:
                    batch_emails = list(gmail_client.get_messages_batch(batch_ids, format="minimal"))
                    for email in batch_emails:
                        result = result_map.get(email.metadata.message_id)
                        if result:
                            results.append((email, result))
                            fetched_count += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch batch of cached emails: {e}")
                    # Try individual fetches for this batch
                    for message_id in batch_ids:
                        try:
                            email = gmail_client.get_message(message_id, format="minimal")
                            result = result_map.get(email.metadata.message_id)
                            if result:
                                results.append((email, result))
                                fetched_count += 1
                        except Exception as e2:
                            logger.warning(f"Failed to get minimal email data for cached result {message_id}: {e2}")
                            cached_count -= 1

                # Progress update
                progress_pct = (fetched_count / len(cached_results)) * 100
                logger.info(f"Progress: {fetched_count}/{len(cached_results)} cached emails fetched ({progress_pct:.1f}%)")

        # Add new results
        results.extend(new_results)

        # Apply labels incrementally if requested
        if apply_labels:
            logger.info("Applying labels incrementally...")
            labels = gmail_client.get_labels()
            labeled_in_batch = []

            # Process all results (cached + new) in batches
            all_to_label = [(email, result) for email, result in results if result is not None]

            batch_num = 0
            for i in range(0, len(all_to_label), batch_size):
                batch_to_label = all_to_label[i:i + batch_size]
                batch_num += 1

                logger.info(f"\n{'='*70}")
                logger.info(f"Processing batch {batch_num}/{(len(all_to_label) + batch_size - 1) // batch_size} ({len(batch_to_label)} emails)")
                logger.info(f"{'='*70}")

                # Sample emails to show (first 3 in batch)
                sample_size = min(3, len(batch_to_label))

                for idx, (email, result) in enumerate(batch_to_label):
                    try:
                        label_name = result.category

                        # Create label if it doesn't exist
                        if label_name not in labels:
                            logger.info(f"Creating label: {label_name}")
                            gmail_client.create_label(label_name)
                            labels = gmail_client.get_labels()

                        label_id = labels[label_name]
                        gmail_client.add_label(email.metadata.message_id, label_id)
                        labeled_in_batch.append(email.metadata.message_id)
                        total_labeled += 1

                        # Show sample emails from this batch
                        if idx < sample_size:
                            subject = email.headers.subject[:60] + "..." if len(email.headers.subject) > 60 else email.headers.subject
                            sender = email.headers.from_address[:40] + "..." if len(email.headers.from_address) > 40 else email.headers.from_address
                            logger.info(f"  ✓ [{idx+1}/{len(batch_to_label)}] {label_name}")
                            logger.info(f"    From: {sender}")
                            logger.info(f"    Subject: {subject}")

                    except Exception as e:
                        logger.warning(f"Failed to apply label to {email.metadata.message_id}: {e}")

                # Mark batch as labeled in cache
                if labeled_in_batch:
                    try:
                        self.cache.batch_mark_labeled(labeled_in_batch)
                        logger.info(f"\n✓ Batch {batch_num} complete: Labeled {len(labeled_in_batch)} emails and marked in cache")
                        logger.info(f"  Total progress: {total_labeled}/{len(all_to_label)} emails labeled ({(total_labeled/len(all_to_label)*100):.1f}%)")
                        if batch_num < (len(all_to_label) + batch_size - 1) // batch_size:
                            logger.info(f"  Moving to next batch...\n")
                        labeled_in_batch = []
                    except Exception as e:
                        logger.warning(f"Failed to mark batch as labeled in cache: {e}")

            logger.info(f"\n{'='*70}")
            logger.info(f"🎉 All batches complete! Total labels applied: {total_labeled}/{len(all_to_label)}")
            logger.info(f"{'='*70}")

        # Log classification summary
        successful = sum(1 for _, result in results if result is not None)
        logger.info(f"Efficient batch classification complete: {successful}/{len(message_ids)} emails classified "
                   f"({cached_count} from cache, {new_classifications} newly classified)")

        if apply_labels:
            logger.info(f"Labels applied to {total_labeled} emails")

        return results

    def _classify_email_thread_safe(self, email: Email, method: str) -> Optional[ClassificationResult]:
        """
        Thread-safe version of classify_email for use in ThreadPoolExecutor.

        Args:
            email: Email to classify
            method: Classification method

        Returns:
            ClassificationResult or None if failed
        """
        try:
            return self.classify_email(email, method)
        except Exception as e:
            logger.warning(f"Thread-safe classification failed for email {email.metadata.message_id}: {e}")
            return None

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