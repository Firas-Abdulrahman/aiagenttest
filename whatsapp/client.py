import requests
import json
import logging
import time
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """WhatsApp Business API Client with enhanced reliability"""

    def __init__(self, config: Dict[str, str]):
        self.whatsapp_token = config.get('whatsapp_token')
        self.phone_number_id = config.get('phone_number_id')
        self.waba_id = config.get('waba_id')
        self.verify_token = config.get('verify_token')

        # API configuration
        self.api_version = 'v18.0'
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.whatsapp_token}',
            'Content-Type': 'application/json'
        }

        # Configure retry strategy
        self.session = self._create_retry_session()

        logger.info(f"✅ WhatsApp client initialized with phone ID: {self.phone_number_id}")

    def _create_retry_session(self) -> requests.Session:
        """Create session with retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # Maximum number of retries
            backoff_factor=1,  # Exponential backoff: 1, 2, 4 seconds
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def _make_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and proper error handling"""
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Log request details
            logger.debug(f"📡 {method} {url} - Status: {response.status_code}")
            
            # Handle specific error cases
            if response.status_code == 401:
                logger.error("❌ Authentication failed - check WhatsApp token")
                return None
            elif response.status_code == 403:
                logger.error("❌ Permission denied - check API permissions")
                return None
            elif response.status_code == 429:
                logger.warning("⚠️ Rate limit exceeded - request will be retried")
                return None
            elif response.status_code >= 500:
                logger.warning(f"⚠️ Server error {response.status_code} - request will be retried")
                return None
            
            return response
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Connection error: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"❌ Request timeout: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return None

    def send_text_message(self, to: str, message: str) -> bool:
        """Send a text message to WhatsApp user with enhanced reliability"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"

            payload = {
                'messaging_product': 'whatsapp',
                'to': to,
                'text': {'body': message}
            }

            logger.info(f"📤 Sending text message to {to}")

            response = self._make_request('POST', url, headers=self.headers, json=payload)

            if response and response.status_code == 200:
                logger.info("✅ Message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send message: {response.status_code if response else 'No response'}")
                if response:
                    logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending text message: {str(e)}")
            return False

    def upload_media(self, media_bytes: bytes, mime_type: str) -> Optional[str]:
        """Upload media to WhatsApp and return media_id."""
        try:
            import requests
            url = f"{self.base_url}/{self.phone_number_id}/media"
            # Pick a filename by mime type
            filename = 'voice.ogg'
            if 'mpeg' in mime_type or 'mp3' in mime_type:
                filename = 'audio.mp3'
            elif 'wav' in mime_type:
                filename = 'audio.wav'

            files = {
                'file': (filename, media_bytes, mime_type),
            }
            data = {
                'messaging_product': 'whatsapp'
            }
            headers = {
                'Authorization': f'Bearer {self.whatsapp_token}'
            }
            response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
            if response.status_code == 200:
                media_id = response.json().get('id')
                return media_id
            logger.error(f"❌ Media upload failed: {response.status_code} {response.text}")
            return None
        except Exception as e:
            logger.error(f"❌ Error uploading media: {e}")
            return None

    def send_voice_message(self, to: str, media_id: str, voice: bool = True) -> bool:
        """Send a WhatsApp audio message (voice note when voice=True)."""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            payload = {
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'audio',
                'audio': {
                    'id': media_id,
                    'voice': bool(voice)
                }
            }
            response = self._make_request('POST', url, headers=self.headers, json=payload)
            if response and response.status_code == 200:
                logger.info("✅ Voice message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send voice message: {response.status_code if response else 'No response'}")
                if response:
                    logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error sending voice message: {e}")
            return False

    def send_template_message(self, to: str, template_name: str, language_code: str = 'en',
                              parameters: List[str] = None) -> bool:
        """Send a template message to WhatsApp user with enhanced reliability"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"

            # Build template payload
            template_payload = {
                'name': template_name,
                'language': {'code': language_code}
            }

            # Add parameters if provided
            if parameters:
                template_payload['components'] = [{
                    'type': 'body',
                    'parameters': [{'type': 'text', 'text': param} for param in parameters]
                }]

            payload = {
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'template',
                'template': template_payload
            }

            logger.info(f"📤 Sending template message '{template_name}' to {to}")

            response = self._make_request('POST', url, headers=self.headers, json=payload)

            if response and response.status_code == 200:
                logger.info("✅ Template message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send template message: {response.status_code if response else 'No response'}")
                if response:
                    logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending template message: {str(e)}")
            return False

    def send_interactive_message(self, to: str, header_text: str, body_text: str,
                                 footer_text: str, buttons: List[Dict]) -> bool:
        """Send an interactive message with buttons with enhanced reliability"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"

            # Build interactive payload
            interactive_payload = {
                'type': 'button',
                'header': {'type': 'text', 'text': header_text},
                'body': {'text': body_text},
                'footer': {'text': footer_text},
                'action': {'buttons': buttons}
            }

            payload = {
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'interactive',
                'interactive': interactive_payload
            }

            logger.info(f"📤 Sending interactive message to {to}")

            response = self._make_request('POST', url, headers=self.headers, json=payload)

            if response and response.status_code == 200:
                logger.info("✅ Interactive message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send interactive message: {response.status_code if response else 'No response'}")
                if response:
                    logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending interactive message: {str(e)}")
            return False

    def send_list_message(self, to: str, header_text: str, body_text: str,
                          footer_text: str, button_text: str, sections: List[Dict]) -> bool:
        """Send a list message with multiple options with enhanced reliability"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"

            # Build interactive list payload
            interactive_payload = {
                'type': 'list',
                'header': {'type': 'text', 'text': header_text},
                'body': {'text': body_text},
                'footer': {'text': footer_text},
                'action': {
                    'button': button_text,
                    'sections': sections
                }
            }

            payload = {
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'interactive',
                'interactive': interactive_payload
            }

            logger.info(f"📤 Sending list message to {to}")

            response = self._make_request('POST', url, headers=self.headers, json=payload)

            if response and response.status_code == 200:
                logger.info("✅ List message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send list message: {response.status_code if response else 'No response'}")
                if response:
                    logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending list message: {str(e)}")
            return False

    def mark_message_as_read(self, message_id: str) -> bool:
        """Mark a message as read with enhanced reliability"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"

            payload = {
                'messaging_product': 'whatsapp',
                'status': 'read',
                'message_id': message_id
            }

            response = self._make_request('POST', url, headers=self.headers, json=payload)

            if response and response.status_code == 200:
                logger.info(f"✅ Message {message_id} marked as read")
                return True
            else:
                logger.error(f"❌ Failed to mark message as read: {response.status_code if response else 'No response'}")
                return False

        except Exception as e:
            logger.error(f"❌ Error marking message as read: {str(e)}")
            return False

    def get_media(self, media_id: str) -> Optional[Dict]:
        """Get media information by ID with enhanced reliability"""
        try:
            url = f"{self.base_url}/{media_id}"

            response = self._make_request('GET', url, headers=self.headers)

            if response and response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get media: {response.status_code if response else 'No response'}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting media: {str(e)}")
            return None

    def download_media(self, media_url: str) -> Optional[bytes]:
        """Download media content with enhanced reliability"""
        try:
            response = self._make_request('GET', media_url, headers=self.headers)

            if response and response.status_code == 200:
                return response.content
            else:
                logger.error(f"❌ Failed to download media: {response.status_code if response else 'No response'}")
                return None

        except Exception as e:
            logger.error(f"❌ Error downloading media: {str(e)}")
            return None

    def get_business_profile(self) -> Optional[Dict]:
        """Get business profile information with enhanced reliability"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/whatsapp_business_profile"

            response = self._make_request('GET', url, headers=self.headers)

            if response and response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get business profile: {response.status_code if response else 'No response'}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting business profile: {str(e)}")
            return None

    def update_business_profile(self, profile_data: Dict) -> bool:
        """Update business profile with enhanced reliability"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/whatsapp_business_profile"

            response = self._make_request('POST', url, headers=self.headers, json=profile_data)

            if response and response.status_code == 200:
                logger.info("✅ Business profile updated successfully")
                return True
            else:
                logger.error(f"❌ Failed to update business profile: {response.status_code if response else 'No response'}")
                return False

        except Exception as e:
            logger.error(f"❌ Error updating business profile: {str(e)}")
            return False

    def get_phone_numbers(self) -> Optional[List[Dict]]:
        """Get all phone numbers associated with the WhatsApp Business Account with enhanced reliability"""
        try:
            url = f"{self.base_url}/{self.waba_id}/phone_numbers"

            response = self._make_request('GET', url, headers=self.headers)

            if response and response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            else:
                logger.error(f"❌ Failed to get phone numbers: {response.status_code if response else 'No response'}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting phone numbers: {str(e)}")
            return None

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verify webhook for WhatsApp subscription"""
        logger.info("🔐 Webhook verification attempt")
        logger.info(f"Mode: {mode}")

        if mode == 'subscribe' and token == self.verify_token:
            logger.info("✅ Webhook verified successfully!")
            return challenge
        else:
            logger.warning("❌ Webhook verification failed!")
            return None

    def send_response(self, phone_number: str, response_data: Dict[str, Any]) -> bool:
        """Send response back to WhatsApp user with enhanced reliability"""
        try:
            message_type = response_data.get('type', 'text')

            if message_type == 'text':
                content = response_data.get('content', '')
                return self.send_text_message(phone_number, content)
            elif message_type == 'interactive_buttons':
                header_text = response_data.get('header_text', '')
                body_text = response_data.get('body_text', '')
                footer_text = response_data.get('footer_text', '')
                buttons = response_data.get('buttons', [])
                return self.send_interactive_message(phone_number, header_text, body_text, footer_text, buttons)
            else:
                logger.warning(f"Unsupported message type: {message_type}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending response: {str(e)}")
            return False

    def validate_webhook_payload(self, payload: Dict) -> bool:
        """Validate incoming webhook payload"""
        try:
            # Check required fields
            if 'entry' not in payload:
                return False

            for entry in payload['entry']:
                if 'changes' not in entry:
                    continue

                for change in entry['changes']:
                    if change.get('field') != 'messages':
                        continue

                    value = change.get('value', {})
                    if 'messages' in value or 'statuses' in value:
                        return True

            return False

        except Exception as e:
            logger.error(f"❌ Error validating webhook payload: {str(e)}")
            return False

    def get_webhook_data(self, payload: Dict) -> List[Dict]:
        """Extract message data from webhook payload"""
        messages = []

        try:
            for entry in payload.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        value = change.get('value', {})

                        # If webhook payload includes metadata with phone number id,
                        # ensure it matches the configured phone number id.
                        metadata = value.get('metadata', {})
                        incoming_phone_id = metadata.get('phone_number_id')
                        if (
                            self.phone_number_id
                            and incoming_phone_id
                            and incoming_phone_id != self.phone_number_id
                        ):
                            logger.info(
                                f"Ignoring webhook for phone_number_id {incoming_phone_id} (configured {self.phone_number_id})"
                            )
                            continue

                        # Extract messages
                        for message in value.get('messages', []):
                            # Handle interactive button responses
                            if message.get('type') == 'interactive':
                                interactive = message.get('interactive', {})
                                if interactive.get('type') == 'button_reply':
                                    button_reply = interactive.get('button_reply', {})
                                    # Convert button click to text message format
                                    message['text'] = {
                                        'body': button_reply.get('id', '')
                                    }
                                    message['type'] = 'text'
                            messages.append(message)

            return messages

        except Exception as e:
            logger.error(f"❌ Error extracting webhook data: {str(e)}")
            return []