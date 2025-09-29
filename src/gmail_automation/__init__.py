"""Gmail Automation Package - Core Module"""

__version__ = "4.0.0"
__author__ = "Bhargav Achary"
__email__ = "bhargav@example.com"

# Import only standard library components
from .models.email import Email, EmailMetadata, EmailHeaders, EmailContent, ClassificationResult

# Lazy imports for components with external dependencies
def _get_config():
    """Lazy import for Config to avoid dependency issues."""
    try:
        from .core.config import Config
        return Config
    except ImportError as e:
        raise ImportError(
            f"Config requires external dependencies. "
            f"Install with: pip install gmail-automation-suite[all] "
            f"Original error: {e}"
        )

def _get_gmail_client():
    """Lazy import for GmailClient to avoid dependency issues."""
    try:
        from .core.gmail_client import GmailClient
        return GmailClient
    except ImportError as e:
        raise ImportError(
            f"GmailClient requires Google API dependencies. "
            f"Install with: pip install gmail-automation-suite[all] "
            f"Original error: {e}"
        )

def _get_email_classifier():
    """Lazy import for EmailClassifier."""
    try:
        from .core.classifier import EmailClassifier
        return EmailClassifier
    except ImportError as e:
        raise ImportError(
            f"EmailClassifier requires additional dependencies. "
            f"Install with: pip install gmail-automation-suite[all] "
            f"Original error: {e}"
        )

# Expose through __getattr__ for dynamic imports
def __getattr__(name):
    if name == "Config":
        return _get_config()
    elif name == "GmailClient":
        return _get_gmail_client()
    elif name == "EmailClassifier":
        return _get_email_classifier()
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["Config", "Email", "EmailMetadata", "EmailHeaders", "EmailContent", "ClassificationResult", "GmailClient", "EmailClassifier"]