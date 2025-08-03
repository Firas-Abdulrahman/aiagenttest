# utils/rate_limiter.py - NEW FILE

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to prevent message spam and infinite loops"""

    def __init__(self, max_messages_per_minute: int = 10, max_messages_per_hour: int = 100):
        self.max_per_minute = max_messages_per_minute
        self.max_per_hour = max_messages_per_hour

        # Track messages per user
        self.user_messages = defaultdict(lambda: {
            'minute': deque(),
            'hour': deque()
        })

        # Track last message time per user
        self.last_message_time = {}

        # Minimum time between messages (prevent rapid fire)
        self.min_interval = 2  # 2 seconds

    def is_allowed(self, phone_number: str) -> tuple[bool, Optional[str]]:
        """Check if user is allowed to send a message"""
        current_time = time.time()

        # Check minimum interval between messages
        if phone_number in self.last_message_time:
            time_since_last = current_time - self.last_message_time[phone_number]
            if time_since_last < self.min_interval:
                return False, f"Please wait {self.min_interval - int(time_since_last)} seconds before sending another message"

        # Clean old entries
        self._cleanup_old_entries(phone_number, current_time)

        user_data = self.user_messages[phone_number]

        # Check per-minute limit
        if len(user_data['minute']) >= self.max_per_minute:
            return False, f"Rate limit exceeded: maximum {self.max_per_minute} messages per minute"

        # Check per-hour limit
        if len(user_data['hour']) >= self.max_per_hour:
            return False, f"Rate limit exceeded: maximum {self.max_per_hour} messages per hour"

        # Record this message
        user_data['minute'].append(current_time)
        user_data['hour'].append(current_time)
        self.last_message_time[phone_number] = current_time

        return True, None

    def _cleanup_old_entries(self, phone_number: str, current_time: float):
        """Remove old entries outside the time windows"""
        user_data = self.user_messages[phone_number]

        # Remove entries older than 1 minute
        minute_cutoff = current_time - 60
        while user_data['minute'] and user_data['minute'][0] < minute_cutoff:
            user_data['minute'].popleft()

        # Remove entries older than 1 hour
        hour_cutoff = current_time - 3600
        while user_data['hour'] and user_data['hour'][0] < hour_cutoff:
            user_data['hour'].popleft()

    def get_user_stats(self, phone_number: str) -> Dict:
        """Get current rate limit stats for a user"""
        current_time = time.time()
        self._cleanup_old_entries(phone_number, current_time)

        user_data = self.user_messages[phone_number]

        return {
            'messages_this_minute': len(user_data['minute']),
            'messages_this_hour': len(user_data['hour']),
            'max_per_minute': self.max_per_minute,
            'max_per_hour': self.max_per_hour,
            'last_message': self.last_message_time.get(phone_number, 0)
        }

    def reset_user_limits(self, phone_number: str):
        """Reset rate limits for a specific user (admin function)"""
        if phone_number in self.user_messages:
            del self.user_messages[phone_number]
        if phone_number in self.last_message_time:
            del self.last_message_time[phone_number]

        logger.info(f"🔄 Rate limits reset for {phone_number}")

    def cleanup_old_users(self):
        """Clean up data for users who haven't sent messages recently"""
        current_time = time.time()
        cutoff_time = current_time - 86400  # 24 hours

        users_to_remove = []

        for phone_number, last_time in self.last_message_time.items():
            if last_time < cutoff_time:
                users_to_remove.append(phone_number)

        for phone_number in users_to_remove:
            if phone_number in self.user_messages:
                del self.user_messages[phone_number]
            if phone_number in self.last_message_time:
                del self.last_message_time[phone_number]

        if users_to_remove:
            logger.info(f"🧹 Cleaned up rate limit data for {len(users_to_remove)} inactive users")