import os
import requests
import json
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class WhatsAppConfig:
    """Centralized configuration management for WhatsApp Bot"""

    def __init__(self):
        """Initialize configuration from environment variables"""
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

        # Print debug info
        self.print_debug_info()

        # Auto-fetch phone number ID
        self.phone_number_id = os.getenv('PHONE_NUMBER_ID')
        if not self.phone_number_id and self.whatsapp_token and self.waba_id:
            print("🔍 Phone number ID not found, attempting auto-fetch...")
            self.phone_number_id = self.get_phone_number_id()
        elif self.phone_number_id:
            print(f"✅ Using phone number ID from env: {self.phone_number_id}")

    def print_debug_info(self):
        """Print debug information about loaded credentials"""
        print("\n" + "=" * 50)
        print("🔧 WHATSAPP BOT CONFIGURATION")
        print("=" * 50)
        print(f"WHATSAPP_TOKEN: {'✅ Loaded' if self.whatsapp_token else '❌ Missing'}")
        print(f"APP_ID: {'Loaded' if self.app_id else '❌ Missing'}")
        print(f"CLIENT_SECRET: {'✅ Loaded' if self.client_secret else '❌ Missing'}")
        print(f"WHATSAPP_BUSINESS_ACCOUNT_ID: {'✅ Loaded' if self.waba_id else '❌ Missing'}")
        print(f"VERIFY_TOKEN: {'✅ Loaded' if self.verify_token else '❌ Missing'}")
        print(f"OPENAI_API_KEY: {'✅ Loaded' if self.openai_api_key else 'ℹ️ Missing (Optional)'}")
        print(f"AI_ENABLED: {'✅ Yes' if self.ai_enabled else '❌ No'}")
        print(f"AI_FALLBACK_ENABLED: {'✅ Yes' if self.ai_fallback_enabled else '❌ No'}")
        print(f"AI_QUOTA_CACHE_DURATION: {self.ai_quota_cache_duration}s")
        print(f"AI_DISABLE_ON_QUOTA: {'✅ Yes' if self.ai_disable_on_quota else '❌ No'}")

        if self.whatsapp_token:
            print(f"Token preview: {self.whatsapp_token[:15]}...")
        if self.waba_id:
            print(f"WABA ID: {self.waba_id}")
        print("=" * 50 + "\n")

    def get_phone_number_id(self) -> Optional[str]:
        """Get phone number ID from WhatsApp Business Account"""
        try:
            print(f"🔍 Fetching phone numbers from WABA: {self.waba_id}")

            url = f"https://graph.facebook.com/v18.0/{self.waba_id}/phone_numbers"
            headers = {'Authorization': f'Bearer {self.whatsapp_token}'}

            response = requests.get(url, headers=headers)
            print(f"📋 Response status: {response.status_code}")

            if response.status_code == 401:
                print("❌ 401 Unauthorized - Check token and permissions")
                return None

            if response.status_code == 403:
                print("❌ 403 Forbidden - Permission denied")
                return None

            response.raise_for_status()
            data = response.json()

            phone_numbers = data.get('data', [])
            if phone_numbers:
                phone_number_id = phone_numbers[0]['id']
                phone_number = phone_numbers[0]['display_phone_number']

                print(f"✅ Found phone number: {phone_number}")
                print(f"📱 Phone Number ID: {phone_number_id}")

                return phone_number_id
            else:
                print("❌ No phone numbers found in WhatsApp Business Account")
                return None

        except Exception as e:
            print(f"❌ Error fetching phone number ID: {str(e)}")
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
            'db_path': self.db_path
        }

    def validate_config(self) -> bool:
        """Validate required configuration"""
        print("\n🔍 VALIDATING CONFIGURATION...")

        missing_fields = []

        if not self.whatsapp_token:
            missing_fields.append("WHATSAPP_TOKEN")
        if not self.waba_id:
            missing_fields.append("WHATSAPP_BUSINESS_ACCOUNT_ID")
        if not self.phone_number_id:
            missing_fields.append("phone_number_id")

        if missing_fields:
            print(f"❌ Missing required configuration: {', '.join(missing_fields)}")
            return False

        print("✅ Configuration validated successfully")
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