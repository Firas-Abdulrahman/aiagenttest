"""Helper utility functions"""

import re
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def format_price(price: int, currency: str = "IQD") -> str:
    """Format price with currency"""
    return f"{price:,} {currency}"


def format_phone_number(phone: str) -> str:
    """Format phone number consistently"""
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', phone)

    # Add + if missing
    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned

    return cleaned


def truncate_message(message: str, max_length: int = 4000) -> str:
    """Truncate message to WhatsApp limits"""
    if len(message) <= max_length:
        return message

    return message[:max_length - 20] + "... (تم اختصار الرسالة)"


def extract_order_id() -> str:
    """Generate unique order ID"""
    import random
    return f"HEF{random.randint(1000, 9999)}"


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()


def clean_text_input(text: str) -> str:
    """Clean and sanitize text input"""
    if not text:
        return ""

    # Remove excessive whitespace
    text = ' '.join(text.split())

    # Limit length
    if len(text) > 1000:
        text = text[:1000]

    return text.strip()


def is_arabic_text(text: str) -> bool:
    """Check if text contains Arabic characters"""
    arabic_pattern = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
    return bool(re.search(arabic_pattern, text))


def format_menu_display(items: list, language: str = 'arabic') -> str:
    """Format menu items for display"""
    if not items:
        return "لا توجد عناصر\nNo items available"

    formatted = ""
    for i, item in enumerate(items, 1):
        if language == 'arabic':
            formatted += f"{i}. {item['item_name_ar']}\n"
            formatted += f"   السعر: {format_price(item['price'])}\n\n"
        else:
            formatted += f"{i}. {item['item_name_en']}\n"
            formatted += f"   Price: {format_price(item['price'])}\n\n"

    return formatted.strip()