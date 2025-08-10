import os
import requests
import json
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class WhatsAppConfig:
    """Centralized configuration management for WhatsApp Bot with enhanced validation"""

    def __init__(self):
        """Initialize configuration from environment variables with validation"""
        # Validate configuration before initialization
        if not self._validate_required_environment():
            raise ValueError("Missing required environment variables. Check configuration.")

        # Core credentials
        self.whatsapp_token = os.getenv('WHATSAPP_TOKEN')
        self.app_id = os.getenv('APP_ID')
        self.client_secret = os.getenv('CLIENT_SECRET')
        self.waba_id = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
        self.verify_token = os.getenv('VERIFY_TOKEN', 'my_webhook_verify_token_2024')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        # AI configuration
        self.ai_enabled = bool(self.openai_api_key)
        self.ai_fallback_enabled = os.getenv('AI_FALLBACK_ENABLED', 'true').lower() == 'true'
        self.ai_quota_cache_duration = int(os.getenv('AI_QUOTA_CACHE_DURATION', '300'))  # 5 minutes default
        self.ai_disable_on_quota = os.getenv('AI_DISABLE_ON_QUOTA', 'true').lower() == 'true'

        # Server configuration
        self.port = int(os.environ.get('PORT', 5000))
        self.debug_mode = os.environ.get('ENVIRONMENT', 'development') == 'development'
        self.host = '0.0.0.0'

        # Database configuration
        self.db_path = os.getenv('DATABASE_PATH', 'hef_cafe.db')

        # Auto-fetch phone number ID
        self.phone_number_id = os.getenv('PHONE_NUMBER_ID')
        if self.phone_number_id:
            # Clean the phone number ID (remove + prefix if present)
            self.phone_number_id = self.phone_number_id.lstrip('+')
            logger.info(f"✅ Using phone number ID from env: {self.phone_number_id}")
        elif not self.phone_number_id and self.whatsapp_token and self.waba_id:
            logger.info("🔍 Phone number ID not found, attempting auto-fetch...")
            self.phone_number_id = self.get_phone_number_id()

        # Final validation
        if not self.validate_config():
            raise ValueError("Configuration validation failed. Check required fields.")

        # Print safe debug info (no credentials)
        self.print_safe_debug_info()

    def _validate_required_environment(self) -> bool:
        """Validate required environment variables before initialization"""
        required_vars = [
            'WHATSAPP_TOKEN',
            'WHATSAPP_BUSINESS_ACCOUNT_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            logger.error("Please set the required environment variables before starting the application.")
            return False
        
        return True

    def print_safe_debug_info(self):
        """Print safe debug information without exposing credentials"""
        logger.info("\n" + "=" * 50)
        logger.info("🔧 WHATSAPP BOT CONFIGURATION")
        logger.info("=" * 50)
        logger.info(f"WHATSAPP_TOKEN: {'✅ Loaded' if self.whatsapp_token else '❌ Missing'}")
        logger.info(f"APP_ID: {'✅ Loaded' if self.app_id else '❌ Missing'}")
        logger.info(f"CLIENT_SECRET: {'✅ Loaded' if self.client_secret else '❌ Missing'}")
        logger.info(f"WHATSAPP_BUSINESS_ACCOUNT_ID: {'✅ Loaded' if self.waba_id else '❌ Missing'}")
        logger.info(f"VERIFY_TOKEN: {'✅ Loaded' if self.verify_token else '❌ Missing'}")
        logger.info(f"OPENAI_API_KEY: {'✅ Loaded' if self.openai_api_key else 'ℹ️ Missing (Optional)'}")
        logger.info(f"AI_ENABLED: {'✅ Yes' if self.ai_enabled else '❌ No'}")
        logger.info(f"AI_FALLBACK_ENABLED: {'✅ Yes' if self.ai_fallback_enabled else '❌ No'}")
        logger.info(f"AI_QUOTA_CACHE_DURATION: {self.ai_quota_cache_duration}s")
        logger.info(f"AI_DISABLE_ON_QUOTA: {'✅ Yes' if self.ai_disable_on_quota else '❌ No'}")
        logger.info(f"ENVIRONMENT: {'development' if self.debug_mode else 'production'}")
        logger.info(f"PORT: {self.port}")
        logger.info(f"DATABASE_PATH: {self.db_path}")

        if self.waba_id:
            logger.info(f"WABA ID: {self.waba_id}")
        logger.info("=" * 50 + "\n")

    def get_phone_number_id(self) -> Optional[str]:
        """Get phone number ID from WhatsApp Business Account with enhanced error handling"""
        try:
            logger.info(f"🔍 Fetching phone numbers from WABA: {self.waba_id}")

            url = f"https://graph.facebook.com/v18.0/{self.waba_id}/phone_numbers"
            headers = {'Authorization': f'Bearer {self.whatsapp_token}'}

            # Add timeout and retry logic
            response = requests.get(url, headers=headers, timeout=30)

            logger.info(f"📋 Response status: {response.status_code}")

            if response.status_code == 401:
                logger.error("❌ 401 Unauthorized - Check token and permissions")
                return None

            if response.status_code == 403:
                logger.error("❌ 403 Forbidden - Permission denied")
                return None

            if response.status_code == 404:
                logger.error("❌ 404 Not Found - Check WABA ID")
                return None

            response.raise_for_status()
            data = response.json()

            phone_numbers = data.get('data', [])
            if phone_numbers:
                phone_number_id = phone_numbers[0]['id']
                phone_number = phone_numbers[0]['display_phone_number']

                logger.info(f"✅ Found phone number: {phone_number}")
                logger.info(f"📱 Phone Number ID: {phone_number_id}")

                return phone_number_id
            else:
                logger.error("❌ No phone numbers found in WhatsApp Business Account")
                return None

        except requests.exceptions.Timeout:
            logger.error("❌ Timeout while fetching phone number ID")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("❌ Connection error while fetching phone number ID")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request error while fetching phone number ID: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching phone number ID: {str(e)}")
            return None

    def get_config_dict(self) -> Dict:
        """Return configuration as dictionary"""
        return {
            'whatsapp_token': self.whatsapp_token,
            'phone_number_id': self.phone_number_id,
            'verify_token': self.verify_token,
            'openai_api_key': self.openai_api_key,
            'app_id': self.app_id,
            'client_secret': self.client_secret,
            'waba_id': self.waba_id,
            'db_path': self.db_path,
            'ai_enabled': self.ai_enabled,
            'ai_fallback_enabled': self.ai_fallback_enabled,
            'ai_quota_cache_duration': self.ai_quota_cache_duration,
            'ai_disable_on_quota': self.ai_disable_on_quota,
            'port': self.port,
            'debug_mode': self.debug_mode,
            'host': self.host
        }

    def validate_config(self) -> bool:
        """Validate required configuration with enhanced checks"""
        logger.info("\n🔍 VALIDATING CONFIGURATION...")

        missing_fields = []
        validation_errors = []

        # Check required fields
        if not self.whatsapp_token:
            missing_fields.append("WHATSAPP_TOKEN")
        if not self.waba_id:
            missing_fields.append("WHATSAPP_BUSINESS_ACCOUNT_ID")
        if not self.phone_number_id:
            missing_fields.append("phone_number_id")

        # Validate token format (basic check)
        if self.whatsapp_token and len(self.whatsapp_token) < 50:
            validation_errors.append("WHATSAPP_TOKEN appears to be invalid (too short)")

        # Validate WABA ID format
        if self.waba_id and not self.waba_id.isdigit():
            validation_errors.append("WHATSAPP_BUSINESS_ACCOUNT_ID should be numeric")

        # Validate phone number ID format (allow + prefix)
        if self.phone_number_id:
            # Remove + prefix if present, then check if remaining is numeric
            phone_id_clean = self.phone_number_id.lstrip('+')
            if not phone_id_clean.isdigit():
                validation_errors.append("PHONE_NUMBER_ID should be numeric (with optional + prefix)")

        # Validate AI configuration
        if self.ai_enabled and not self.openai_api_key:
            validation_errors.append("AI enabled but no OpenAI API key provided")

        # Validate port number
        if self.port < 1 or self.port > 65535:
            validation_errors.append(f"Invalid port number: {self.port}")

        # Report errors
        if missing_fields:
            logger.error(f"❌ Missing required configuration: {', '.join(missing_fields)}")
            return False

        if validation_errors:
            for error in validation_errors:
                logger.error(f"❌ Configuration error: {error}")
            return False

        logger.info("✅ Configuration validated successfully")
        return True

    def get_safe_config(self) -> Dict:
        """Get configuration with sensitive data hidden"""
        safe_config = self.get_config_dict().copy()

        # Hide sensitive information
        if safe_config['whatsapp_token']:
            safe_config['whatsapp_token'] = safe_config['whatsapp_token'][:15] + "..."
        if safe_config['openai_api_key']:
            safe_config['openai_api_key'] = safe_config['openai_api_key'][:15] + "..."
        if safe_config['client_secret']:
            safe_config['client_secret'] = safe_config['client_secret'][:10] + "..."

        return safe_config

    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.debug_mode

    def get_ai_config(self) -> Dict:
        """Get AI-specific configuration"""
        return {
            'ai_quota_cache_duration': self.ai_quota_cache_duration,
            'ai_disable_on_quota': self.ai_disable_on_quota,
            'ai_fallback_enabled': self.ai_fallback_enabled
        }