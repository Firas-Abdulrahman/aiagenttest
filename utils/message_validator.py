import re
from typing import Dict, List, Optional


class MessageValidator:
    """Enhanced message validation and sanitization"""

    # Spam detection patterns
    SPAM_PATTERNS = [
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        r'www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        r'(?:buy now|click here|limited time|free money|guarantee|win|prize)',
        r'(?:call|text|whatsapp)\s*[+]?[0-9\s\-()]{10,}',
    ]

    @staticmethod
    def is_valid_message(message_data: Dict) -> bool:
        """Validate incoming WhatsApp message format"""
        if not message_data:
            return False

        # Must have sender
        if 'from' not in message_data:
            return False

        # Must have text content or be a supported media type
        has_text = 'text' in message_data and 'body' in message_data.get('text', {})
        has_media = any(media_type in message_data for media_type in ['image', 'audio', 'document', 'location'])

        return has_text or has_media

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize and clean user text input"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = ' '.join(text.split())

        # Limit length to prevent abuse
        if len(text) > 1000:
            text = text[:1000]

        # Remove potentially harmful characters
        text = re.sub(r'[<>{}]', '', text)

        return text.strip()

    @staticmethod
    def is_spam(text: str) -> bool:
        """Simple spam detection"""
        if not text:
            return False

        text_lower = text.lower()

        # Check against spam patterns
        for pattern in MessageValidator.SPAM_PATTERNS:
            if re.search(pattern, text_lower):
                return True

        # Check for excessive repetition
        words = text_lower.split()
        if len(words) > 3:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:  # Less than 30% unique words
                return True

        return False

    @staticmethod
    def extract_phone_number(message_data: Dict) -> Optional[str]:
        """Extract and validate phone number from message"""
        phone = message_data.get('from', '')

        if not phone:
            return None

        # Clean phone number
        phone_cleaned = re.sub(r'[^\d+]', '', phone)

        # Validate length (should be at least 10 digits)
        if len(phone_cleaned.replace('+', '')) < 10:
            return None

        return phone_cleaned

    @staticmethod
    def extract_customer_name(message_data: Dict) -> str:
        """Extract customer name with fallback"""
        if 'contacts' in message_data:
            contacts = message_data.get('contacts', [])
            if contacts and len(contacts) > 0:
                profile = contacts[0].get('profile', {})
                name = profile.get('name', '').strip()
                if name and len(name) <= 50:  # Reasonable name length
                    return name

        # Fallback to phone number or generic name
        phone = MessageValidator.extract_phone_number(message_data)
        if phone:
            return f"Customer {phone[-4:]}"  # Last 4 digits

        return "Valued Customer"