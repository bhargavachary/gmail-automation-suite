"""
Configuration management for Gmail Automation Suite.

Handles loading, merging, and validation of configuration files
including email categories, rules, and system settings.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import deepmerge

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScoringWeights:
    """Configuration for classification scoring weights."""
    domain_high_confidence: float = 1.2
    domain_medium_confidence: float = 0.8
    subject_high: float = 1.0
    subject_medium: float = 0.6
    content_high: float = 0.7
    content_medium: float = 0.4
    exclusion_penalty: float = -2.0
    negative_keyword_penalty: float = -1.5
    priority_bonus: float = 0.15

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScoringWeights':
        """Create ScoringWeights from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class GlobalSettings:
    """Global configuration settings."""
    confidence_threshold: float = 2.5
    max_categories_per_email: int = 1
    enable_content_analysis: bool = True
    case_sensitive: bool = False
    language: str = "en"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalSettings':
        """Create GlobalSettings from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class CategoryConfig:
    """Configuration for a single email category."""
    priority: int
    domains: Dict[str, List[str]] = field(default_factory=dict)
    keywords: Dict[str, List[str]] = field(default_factory=dict)
    exclusions: List[str] = field(default_factory=list)
    negative_keywords: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CategoryConfig':
        """Create CategoryConfig from dictionary."""
        return cls(
            priority=data.get('priority', 5),
            domains=data.get('domains', {}),
            keywords=data.get('keywords', {}),
            exclusions=data.get('exclusions', []),
            negative_keywords=data.get('negative_keywords', [])
        )


class Config:
    """
    Central configuration manager for Gmail Automation Suite.

    Handles loading and merging of base configuration, custom rules,
    and environment-specific settings.
    """

    def __init__(self,
                 config_dir: Optional[Path] = None,
                 base_config_file: str = "email_categories.json",
                 custom_config_file: str = "custom_email_rules.json"):
        """
        Initialize configuration manager.

        Args:
            config_dir: Configuration directory path (default: ./data)
            base_config_file: Base configuration file name
            custom_config_file: Custom rules file name
        """
        self.config_dir = config_dir or Path("data")
        self.base_config_file = base_config_file
        self.custom_config_file = custom_config_file

        # Configuration data
        self._base_config: Dict[str, Any] = {}
        self._custom_config: Dict[str, Any] = {}
        self._merged_config: Dict[str, Any] = {}

        # Parsed configurations
        self.categories: Dict[str, CategoryConfig] = {}
        self.global_settings: GlobalSettings = GlobalSettings()
        self.scoring_weights: ScoringWeights = ScoringWeights()

        # Load and parse configurations
        self._load_configurations()
        self._parse_configurations()

    def _load_configurations(self) -> None:
        """Load base and custom configuration files."""
        try:
            # Load base configuration
            base_path = self.config_dir / self.base_config_file
            if base_path.exists():
                with open(base_path, 'r', encoding='utf-8') as f:
                    self._base_config = json.load(f)
                logger.info(f"Loaded base configuration from {base_path}")
            else:
                logger.warning(f"Base configuration file not found: {base_path}")
                self._base_config = self._get_default_config()

            # Load custom configuration
            custom_path = self.config_dir / self.custom_config_file
            if custom_path.exists():
                with open(custom_path, 'r', encoding='utf-8') as f:
                    self._custom_config = json.load(f)
                logger.info(f"Loaded custom configuration from {custom_path}")
            else:
                logger.info(f"No custom configuration found at {custom_path}")
                self._custom_config = {}

            # Merge configurations
            self._merged_config = deepmerge.always_merger.merge(
                self._base_config.copy(),
                self._custom_config
            )
            logger.info("Configuration files merged successfully")

        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def _parse_configurations(self) -> None:
        """Parse merged configuration into structured objects."""
        try:
            # Parse categories
            categories_data = self._merged_config.get('categories', {})
            self.categories = {
                name: CategoryConfig.from_dict(config)
                for name, config in categories_data.items()
            }

            # Parse global settings
            global_settings_data = self._merged_config.get('global_settings', {})
            self.global_settings = GlobalSettings.from_dict(global_settings_data)

            # Parse scoring weights
            scoring_weights_data = self._merged_config.get('scoring_weights', {})
            self.scoring_weights = ScoringWeights.from_dict(scoring_weights_data)

            logger.info(f"Parsed {len(self.categories)} email categories")

        except Exception as e:
            logger.error(f"Error parsing configurations: {e}")
            raise ConfigurationError(f"Failed to parse configuration: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if no base config is found."""
        return {
            "categories": {
                "👤 Personal & Social": {
                    "priority": 1,
                    "domains": {"medium_confidence": ["gmail.com", "outlook.com"]},
                    "keywords": {"subject_medium": ["personal", "meeting", "social"]},
                    "exclusions": [],
                    "negative_keywords": []
                }
            },
            "global_settings": {
                "confidence_threshold": 2.5,
                "max_categories_per_email": 1,
                "enable_content_analysis": True,
                "case_sensitive": False,
                "language": "en"
            },
            "scoring_weights": {
                "domain_high_confidence": 1.2,
                "domain_medium_confidence": 0.8,
                "subject_high": 1.0,
                "subject_medium": 0.6,
                "content_high": 0.7,
                "content_medium": 0.4,
                "exclusion_penalty": -2.0,
                "negative_keyword_penalty": -1.5,
                "priority_bonus": 0.15
            }
        }

    def get_category_names(self) -> List[str]:
        """Get list of all category names."""
        return list(self.categories.keys())

    def get_category_config(self, category_name: str) -> Optional[CategoryConfig]:
        """Get configuration for a specific category."""
        return self.categories.get(category_name)

    def to_dict(self) -> Dict[str, Any]:
        """Convert current configuration to dictionary format."""
        return self._merged_config.copy()

    def save_custom_config(self, custom_config: Dict[str, Any]) -> None:
        """Save custom configuration to file."""
        try:
            custom_path = self.config_dir / self.custom_config_file
            custom_path.parent.mkdir(parents=True, exist_ok=True)

            with open(custom_path, 'w', encoding='utf-8') as f:
                json.dump(custom_config, f, indent=2, ensure_ascii=False)

            logger.info(f"Custom configuration saved to {custom_path}")

            # Reload configurations
            self._load_configurations()
            self._parse_configurations()

        except Exception as e:
            logger.error(f"Error saving custom configuration: {e}")
            raise ConfigurationError(f"Failed to save custom configuration: {e}")

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []

        # Check required categories
        if not self.categories:
            issues.append("No email categories defined")

        # Check category configurations
        for category_name, category_config in self.categories.items():
            if not isinstance(category_config.priority, int):
                issues.append(f"Category '{category_name}': priority must be integer")

            if category_config.priority < 1 or category_config.priority > 10:
                issues.append(f"Category '{category_name}': priority must be 1-10")

        # Check global settings
        if self.global_settings.confidence_threshold <= 0:
            issues.append("confidence_threshold must be positive")

        if self.global_settings.max_categories_per_email < 1:
            issues.append("max_categories_per_email must be >= 1")

        return issues


class ConfigurationError(Exception):
    """Configuration-related error."""
    pass