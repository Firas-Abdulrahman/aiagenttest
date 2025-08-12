# utils/thread_safe_session.py - NEW FILE
"""
Thread-safe session management to prevent user session conflicts
"""
import threading
import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class UserWorkflowState:
    """Isolated workflow state for each user"""
    phone_number: str
    current_step: str = 'waiting_for_language'
    language_preference: Optional[str] = None
    customer_name: Optional[str] = None
    selected_main_category: Optional[int] = None
    selected_sub_category: Optional[int] = None
    selected_item: Optional[int] = None
    order_mode: Optional[str] = None  # 'quick' or 'explore'
    conversation_context: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    processing: bool = False  # Flag to prevent concurrent processing
    last_message_id: Optional[str] = None  # Prevent duplicate processing


class ThreadSafeSessionManager:
    """Thread-safe session manager with user isolation"""

    def __init__(self):
        # Per-user locks to prevent concurrent processing
        self._user_locks: Dict[str, threading.RLock] = {}
        self._locks_lock = threading.Lock()  # Lock for the locks dict itself

        # In-memory session cache with thread safety
        self._session_cache: Dict[str, UserWorkflowState] = {}
        self._cache_lock = threading.RLock()

        # Message deduplication
        self._processed_messages: Dict[str, float] = {}
        self._message_cleanup_lock = threading.Lock()

        # Session timeout in seconds
        self.session_timeout = 1800  # 30 minutes

        logger.info("✅ Thread-safe session manager initialized")

    def get_user_lock(self, phone_number: str) -> threading.RLock:
        """Get or create a lock for specific user - thread safe"""
        with self._locks_lock:
            if phone_number not in self._user_locks:
                self._user_locks[phone_number] = threading.RLock()
            return self._user_locks[phone_number]

    @contextmanager
    def user_session_lock(self, phone_number: str):
        """Context manager for user-specific locking"""
        user_lock = self.get_user_lock(phone_number)
        acquired = False
        try:
            # Try to acquire lock with timeout
            acquired = user_lock.acquire(timeout=10)
            if not acquired:
                raise TimeoutError(f"Could not acquire lock for user {phone_number}")

            logger.debug(f"🔒 Acquired lock for user {phone_number}")
            yield

        finally:
            if acquired:
                user_lock.release()
                logger.debug(f"🔓 Released lock for user {phone_number}")

    def is_message_duplicate(self, phone_number: str, message_id: str) -> bool:
        """Check if message was already processed (thread-safe) - ENHANCED"""
        with self._message_cleanup_lock:
            # Clean old entries first
            current_time = time.time()
            cutoff = current_time - 300  # 5 minutes

            to_remove = [msg_id for msg_id, timestamp in self._processed_messages.items()
                         if timestamp < cutoff]

            for msg_id in to_remove:
                del self._processed_messages[msg_id]

            # Check for duplicate using multiple keys
            keys_to_check = [
                f"{phone_number}:{message_id}",
                f"{phone_number}:{message_id}:{int(current_time)}",  # Add timestamp for extra uniqueness
                f"{phone_number}:{message_id[:20]}"  # Check partial message ID
            ]
            
            for key in keys_to_check:
                if key in self._processed_messages:
                    logger.warning(f"🔄 Duplicate message detected: {key}")
                    return True

            # Mark as processed with multiple keys for better deduplication
            primary_key = f"{phone_number}:{message_id}"
            self._processed_messages[primary_key] = current_time
            
            # Also mark with timestamp for extra protection
            timestamp_key = f"{phone_number}:{message_id}:{int(current_time)}"
            self._processed_messages[timestamp_key] = current_time
            
            return False

    def get_user_state(self, phone_number: str) -> Optional[UserWorkflowState]:
        """Get user state from cache (thread-safe)"""
        with self._cache_lock:
            state = self._session_cache.get(phone_number)

            # Check if session expired
            if state and self._is_session_expired(state):
                logger.info(f"⏰ Session expired for user {phone_number}")
                del self._session_cache[phone_number]
                return None

            return state

    def create_or_update_user_state(self, phone_number: str, **kwargs) -> UserWorkflowState:
        """Create or update user state (thread-safe)"""
        with self._cache_lock:
            state = self._session_cache.get(phone_number)

            if state:
                # Update existing state
                for key, value in kwargs.items():
                    if hasattr(state, key) and value is not None:
                        setattr(state, key, value)
                state.updated_at = datetime.now()
            else:
                # Create new state
                state = UserWorkflowState(phone_number=phone_number, **kwargs)

            self._session_cache[phone_number] = state
            logger.debug(f"💾 Updated state for user {phone_number}: {state.current_step}")
            return state

    def delete_user_state(self, phone_number: str) -> bool:
        """Delete user state (thread-safe)"""
        with self._cache_lock:
            if phone_number in self._session_cache:
                del self._session_cache[phone_number]
                logger.info(f"🗑️ Deleted state for user {phone_number}")
                return True
            return False

    def set_user_processing(self, phone_number: str, processing: bool = True):
        """Mark user as currently being processed"""
        with self._cache_lock:
            state = self._session_cache.get(phone_number)
            if state:
                state.processing = processing

    def is_user_processing(self, phone_number: str) -> bool:
        """Check if user is currently being processed"""
        with self._cache_lock:
            state = self._session_cache.get(phone_number)
            return state.processing if state else False

    def _is_session_expired(self, state: UserWorkflowState) -> bool:
        """Check if session has expired"""
        time_diff = datetime.now() - state.updated_at
        return time_diff.total_seconds() > self.session_timeout

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (thread-safe)"""
        with self._cache_lock:
            expired_users = []

            for phone_number, state in self._session_cache.items():
                if self._is_session_expired(state):
                    expired_users.append(phone_number)

            for phone_number in expired_users:
                del self._session_cache[phone_number]

            logger.info(f"🧹 Cleaned up {len(expired_users)} expired sessions")
            return len(expired_users)

    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        with self._cache_lock:
            active_sessions = len(self._session_cache)
            processing_users = sum(1 for state in self._session_cache.values() if state.processing)

            return {
                'active_sessions': active_sessions,
                'processing_users': processing_users,
                'session_timeout_minutes': self.session_timeout // 60,
                'user_locks_count': len(self._user_locks)
            }

    def force_unlock_user(self, phone_number: str):
        """Force unlock a user (admin function)"""
        try:
            user_lock = self.get_user_lock(phone_number)
            # Try to release any held locks
            try:
                user_lock.release()
            except:
                pass  # Lock might not be held

            # Mark as not processing
            self.set_user_processing(phone_number, False)

            logger.warning(f"🔓 Force unlocked user {phone_number}")
        except Exception as e:
            logger.error(f"❌ Error force unlocking user {phone_number}: {e}")


# Global instance
session_manager = ThreadSafeSessionManager()