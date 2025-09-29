"""
Migration utilities for transitioning from legacy Gmail automation code.

Provides tools to extract configuration, migrate data structures, and
validate the transition from monolithic to modular architecture.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import ast
import importlib.util

from ..core.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LegacyMigrator:
    """
    Handles migration from legacy Gmail automation code to new modular structure.

    Extracts configuration, validates data formats, and provides utilities
    for transitioning existing automation rules and settings.
    """

    def __init__(self, legacy_file_path: Path):
        """
        Initialize legacy migrator.

        Args:
            legacy_file_path: Path to legacy gmail_automation.py file
        """
        self.legacy_file_path = legacy_file_path
        self.legacy_content = ""
        self.extracted_config = {}

        if not legacy_file_path.exists():
            raise FileNotFoundError(f"Legacy file not found: {legacy_file_path}")

        self._load_legacy_file()

    def _load_legacy_file(self) -> None:
        """Load and parse legacy file content."""
        try:
            with open(self.legacy_file_path, 'r', encoding='utf-8') as f:
                self.legacy_content = f.read()
            logger.info(f"Loaded legacy file: {self.legacy_file_path}")
        except Exception as e:
            logger.error(f"Failed to load legacy file: {e}")
            raise

    def extract_email_categories(self) -> Dict[str, Any]:
        """
        Extract email categories configuration from legacy code.

        Returns:
            Dictionary containing extracted categories configuration
        """
        categories = {}

        try:
            # Look for CATEGORY_RULES or similar patterns
            category_pattern = r'CATEGORY_RULES\s*=\s*({.*?})'
            match = re.search(category_pattern, self.legacy_content, re.DOTALL)

            if match:
                category_text = match.group(1)
                # Try to safely evaluate the dictionary
                try:
                    categories = ast.literal_eval(category_text)
                    logger.info(f"Extracted {len(categories)} categories from legacy code")
                except (ValueError, SyntaxError) as e:
                    logger.warning(f"Could not parse category rules: {e}")

            # Look for individual category definitions
            if not categories:
                categories = self._extract_individual_categories()

        except Exception as e:
            logger.error(f"Error extracting categories: {e}")

        return categories

    def _extract_individual_categories(self) -> Dict[str, Any]:
        """Extract categories from individual variable definitions."""
        categories = {}

        # Common patterns for category definitions
        patterns = [
            r'(\w+_CATEGORY)\s*=\s*["\']([^"\']+)["\']',
            r'categories\[["\'"]([^"\']+)["\'"]]\s*=\s*({.*?})',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, self.legacy_content, re.DOTALL)
            for match in matches:
                try:
                    if len(match.groups()) == 2:
                        if match.group(2).startswith('{'):
                            # Dictionary definition
                            cat_config = ast.literal_eval(match.group(2))
                            categories[match.group(1)] = cat_config
                        else:
                            # Simple string definition
                            categories[match.group(1)] = {"name": match.group(2)}
                except Exception as e:
                    logger.warning(f"Could not parse category definition: {e}")

        return categories

    def extract_classification_rules(self) -> Dict[str, Any]:
        """
        Extract classification rules and scoring weights.

        Returns:
            Dictionary containing scoring weights and rule configurations
        """
        rules = {
            "scoring_weights": {},
            "global_settings": {},
            "classification_rules": {}
        }

        try:
            # Extract scoring weights
            weight_patterns = [
                r'DOMAIN_WEIGHT\s*=\s*([\d.]+)',
                r'SUBJECT_WEIGHT\s*=\s*([\d.]+)',
                r'CONTENT_WEIGHT\s*=\s*([\d.]+)',
                r'CONFIDENCE_THRESHOLD\s*=\s*([\d.]+)',
            ]

            for pattern in weight_patterns:
                match = re.search(pattern, self.legacy_content)
                if match:
                    weight_name = pattern.split('\\s*')[0].lower()
                    rules["scoring_weights"][weight_name] = float(match.group(1))

            # Extract global settings
            settings_patterns = [
                r'MAX_CATEGORIES\s*=\s*(\d+)',
                r'ENABLE_CONTENT_ANALYSIS\s*=\s*(True|False)',
                r'CASE_SENSITIVE\s*=\s*(True|False)',
            ]

            for pattern in settings_patterns:
                match = re.search(pattern, self.legacy_content)
                if match:
                    setting_name = pattern.split('\\s*')[0].lower()
                    value = match.group(1)
                    if value in ['True', 'False']:
                        rules["global_settings"][setting_name] = value == 'True'
                    else:
                        rules["global_settings"][setting_name] = int(value)

            logger.info("Extracted classification rules from legacy code")

        except Exception as e:
            logger.error(f"Error extracting classification rules: {e}")

        return rules

    def generate_new_config(self, output_dir: Path) -> Tuple[Path, Path]:
        """
        Generate new configuration files from extracted data.

        Args:
            output_dir: Directory to save new configuration files

        Returns:
            Tuple of (base_config_path, custom_config_path)
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Extract data
            categories = self.extract_email_categories()
            rules = self.extract_classification_rules()

            # Create base configuration
            base_config = {
                "categories": self._transform_categories(categories),
                "global_settings": rules.get("global_settings", {}),
                "scoring_weights": rules.get("scoring_weights", {})
            }

            # Save base configuration
            base_config_path = output_dir / "email_categories.json"
            with open(base_config_path, 'w', encoding='utf-8') as f:
                json.dump(base_config, f, indent=2, ensure_ascii=False)

            # Create empty custom configuration
            custom_config_path = output_dir / "custom_email_rules.json"
            custom_config = {
                "categories": {},
                "global_settings": {},
                "scoring_weights": {}
            }

            with open(custom_config_path, 'w', encoding='utf-8') as f:
                json.dump(custom_config, f, indent=2, ensure_ascii=False)

            logger.info(f"Generated configuration files in {output_dir}")
            return base_config_path, custom_config_path

        except Exception as e:
            logger.error(f"Error generating configuration files: {e}")
            raise

    def _transform_categories(self, legacy_categories: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform legacy category format to new format.

        Args:
            legacy_categories: Legacy category definitions

        Returns:
            Transformed categories in new format
        """
        transformed = {}

        for category_name, category_data in legacy_categories.items():
            if isinstance(category_data, dict):
                # Transform to new format
                transformed_category = {
                    "priority": category_data.get("priority", 5),
                    "domains": {
                        "high_confidence": category_data.get("domains", {}).get("high", []),
                        "medium_confidence": category_data.get("domains", {}).get("medium", [])
                    },
                    "keywords": {
                        "subject_high": category_data.get("keywords", {}).get("subject", []),
                        "subject_medium": category_data.get("keywords", {}).get("subject_medium", []),
                        "content_high": category_data.get("keywords", {}).get("content", []),
                        "content_medium": category_data.get("keywords", {}).get("content_medium", [])
                    },
                    "exclusions": category_data.get("exclusions", []),
                    "negative_keywords": category_data.get("negative_keywords", [])
                }
                transformed[category_name] = transformed_category
            else:
                # Simple category definition
                transformed[category_name] = {
                    "priority": 5,
                    "domains": {"high_confidence": [], "medium_confidence": []},
                    "keywords": {"subject_high": [], "subject_medium": [], "content_high": [], "content_medium": []},
                    "exclusions": [],
                    "negative_keywords": []
                }

        return transformed

    def validate_migration(self, config_dir: Path) -> List[str]:
        """
        Validate the migrated configuration.

        Args:
            config_dir: Directory containing new configuration files

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        try:
            # Load and validate new configuration
            config = Config(config_dir=config_dir)
            config_issues = config.validate()
            issues.extend(config_issues)

            # Check if essential categories were migrated
            if not config.categories:
                issues.append("No categories found in migrated configuration")

            # Check if scoring weights are reasonable
            weights = config.scoring_weights
            if weights.domain_high_confidence <= 0:
                issues.append("Domain high confidence weight should be positive")

            if weights.confidence_threshold <= 0:
                issues.append("Confidence threshold should be positive")

            logger.info(f"Migration validation complete: {len(issues)} issues found")

        except Exception as e:
            issues.append(f"Error validating migration: {e}")
            logger.error(f"Migration validation failed: {e}")

        return issues

    def create_migration_report(self, output_path: Path) -> None:
        """
        Create a detailed migration report.

        Args:
            output_path: Path to save the migration report
        """
        try:
            categories = self.extract_email_categories()
            rules = self.extract_classification_rules()

            report = {
                "migration_summary": {
                    "legacy_file": str(self.legacy_file_path),
                    "legacy_file_size": self.legacy_file_path.stat().st_size,
                    "categories_found": len(categories),
                    "scoring_weights_found": len(rules.get("scoring_weights", {})),
                    "global_settings_found": len(rules.get("global_settings", {}))
                },
                "extracted_categories": categories,
                "extracted_rules": rules,
                "recommendations": self._generate_recommendations(categories, rules)
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"Migration report saved to {output_path}")

        except Exception as e:
            logger.error(f"Error creating migration report: {e}")
            raise

    def _generate_recommendations(self, categories: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """Generate migration recommendations based on extracted data."""
        recommendations = []

        if not categories:
            recommendations.append("No categories found - consider manually defining email categories")

        if not rules.get("scoring_weights"):
            recommendations.append("No scoring weights found - using default weights")

        if len(categories) > 20:
            recommendations.append("Large number of categories found - consider consolidating similar categories")

        return recommendations