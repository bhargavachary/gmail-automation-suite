"""
Gmail Automation Suite

A comprehensive Gmail automation solution with AI/ML capabilities for intelligent
email categorization, label management, and semi-supervised learning.
"""

__version__ = "3.0.0"
__author__ = "Gmail Automation Suite"
__description__ = "Advanced Gmail automation with AI-powered email categorization"

from .gmail_automation import GmailAutomationUnified
from .email_ml_categorizer import EmailMLCategorizer
from .email_clustering_reviewer import EmailClusteringReviewer

__all__ = [
    "GmailAutomationUnified",
    "EmailMLCategorizer",
    "EmailClusteringReviewer"
]