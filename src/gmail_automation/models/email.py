"""
Email data models for Gmail Automation Suite.

Provides structured representation of email data with validation,
serialization, and utility methods.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class EmailMetadata:
    """Email metadata structure."""
    message_id: str
    thread_id: str
    label_ids: List[str] = field(default_factory=list)
    snippet: str = ""
    size_estimate: int = 0
    history_id: str = ""
    internal_date: Optional[datetime] = None


@dataclass
class EmailHeaders:
    """Email headers structure."""
    from_address: str = ""
    to_addresses: List[str] = field(default_factory=list)
    subject: str = ""
    date: Optional[datetime] = None
    cc_addresses: List[str] = field(default_factory=list)
    bcc_addresses: List[str] = field(default_factory=list)
    reply_to: str = ""
    message_id: str = ""

    @classmethod
    def from_gmail_headers(cls, headers: List[Dict[str, str]]) -> 'EmailHeaders':
        """Create EmailHeaders from Gmail API headers format."""
        header_dict = {h.get('name', '').lower(): h.get('value', '') for h in headers}

        return cls(
            from_address=header_dict.get('from', ''),
            to_addresses=cls._parse_address_list(header_dict.get('to', '')),
            subject=header_dict.get('subject', ''),
            cc_addresses=cls._parse_address_list(header_dict.get('cc', '')),
            bcc_addresses=cls._parse_address_list(header_dict.get('bcc', '')),
            reply_to=header_dict.get('reply-to', ''),
            message_id=header_dict.get('message-id', '')
        )

    @staticmethod
    def _parse_address_list(address_string: str) -> List[str]:
        """Parse comma-separated email addresses."""
        if not address_string:
            return []
        return [addr.strip() for addr in address_string.split(',') if addr.strip()]


@dataclass
class EmailContent:
    """Email content structure."""
    text_plain: str = ""
    text_html: str = ""
    attachments: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def combined_text(self) -> str:
        """Get combined plain text content for analysis."""
        return self.text_plain or self.text_html or ""


@dataclass
class ClassificationResult:
    """Email classification result."""
    category: str
    confidence: float
    method: str = "unknown"
    scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'category': self.category,
            'confidence': self.confidence,
            'method': self.method,
            'scores': self.scores,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class Email:
    """
    Complete email representation for Gmail Automation Suite.

    Combines metadata, headers, content, and classification results
    into a single, comprehensive data structure.
    """
    metadata: EmailMetadata
    headers: EmailHeaders
    content: EmailContent
    classification: Optional[ClassificationResult] = None

    @property
    def sender_domain(self) -> str:
        """Extract domain from sender email address."""
        sender = self.headers.from_address
        if '@' in sender:
            return sender.split('@')[-1].lower()
        return ""

    @property
    def is_classified(self) -> bool:
        """Check if email has been classified."""
        return self.classification is not None

    def get_classification_data(self) -> Dict[str, Any]:
        """Get data structure for classification algorithms."""
        return {
            'subject': self.headers.subject,
            'sender': self.headers.from_address,
            'content': self.content.combined_text,
            'snippet': self.metadata.snippet,
            'sender_domain': self.sender_domain
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            'metadata': {
                'message_id': self.metadata.message_id,
                'thread_id': self.metadata.thread_id,
                'label_ids': self.metadata.label_ids,
                'snippet': self.metadata.snippet,
                'size_estimate': self.metadata.size_estimate,
                'history_id': self.metadata.history_id
            },
            'headers': {
                'from': self.headers.from_address,
                'to': self.headers.to_addresses,
                'subject': self.headers.subject,
                'cc': self.headers.cc_addresses,
                'bcc': self.headers.bcc_addresses,
                'reply_to': self.headers.reply_to,
                'message_id': self.headers.message_id
            },
            'content': {
                'text_plain': self.content.text_plain,
                'text_html': self.content.text_html,
                'attachments': self.content.attachments
            }
        }

        if self.classification:
            result['classification'] = self.classification.to_dict()

        return result

    @classmethod
    def from_gmail_message(cls, message: Dict[str, Any]) -> 'Email':
        """Create Email instance from Gmail API message format."""
        # Extract metadata
        metadata = EmailMetadata(
            message_id=message.get('id', ''),
            thread_id=message.get('threadId', ''),
            label_ids=message.get('labelIds', []),
            snippet=message.get('snippet', ''),
            size_estimate=message.get('sizeEstimate', 0),
            history_id=message.get('historyId', '')
        )

        # Extract headers
        payload = message.get('payload', {})
        gmail_headers = payload.get('headers', [])
        headers = EmailHeaders.from_gmail_headers(gmail_headers)

        # Extract content (simplified - you may want to expand this)
        content = EmailContent()
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        import base64
                        content.text_plain = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                elif part.get('mimeType') == 'text/html':
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        import base64
                        content.text_html = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
        else:
            # Single part message
            body = payload.get('body', {})
            body_data = body.get('data', '')
            if body_data and payload.get('mimeType') == 'text/plain':
                import base64
                content.text_plain = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')

        return cls(metadata=metadata, headers=headers, content=content)