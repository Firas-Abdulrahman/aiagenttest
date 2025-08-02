import requests
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """WhatsApp Business API Client"""

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

        logger.info(f"✅ WhatsApp client initialized with phone ID: {self.phone_number_id}")

    def send_text_message(self, to: str, message: str) -> bool:
        """Send a text message to WhatsApp user"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"

            payload = {
                'messaging_product': 'whatsapp',
                'to': to,
                'text': {'body': message}
            }

            logger.info(f"📤 Sending text message to {to}")

            response = requests.post(url, headers=self.headers, json=payload)

            if response.status_code == 200:
                logger.info("✅ Message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send message: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending text message: {str(e)}")
            return False

    def send_template_message(self, to: str, template_name: str, language_code: str = 'en',
                              parameters: List[str] = None) -> bool:
        """Send a template message to WhatsApp user"""
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

            response = requests.post(url, headers=self.headers, json=payload)

            if response.status_code == 200:
                logger.info("✅ Template message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send template message: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending template message: {str(e)}")
            return False

    def send_interactive_message(self, to: str, header_text: str, body_text: str,
                                 footer_text: str, buttons: List[Dict]) -> bool:
        """Send an interactive message with buttons"""
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

            response = requests.post(url, headers=self.headers, json=payload)

            if response.status_code == 200:
                logger.info("✅ Interactive message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send interactive message: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending interactive message: {str(e)}")
            return False

    def send_list_message(self, to: str, header_text: str, body_text: str,
                          footer_text: str, button_text: str, sections: List[Dict]) -> bool:
        """Send a list message with multiple options"""
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

            response = requests.post(url, headers=self.headers, json=payload)

            if response.status_code == 200:
                logger.info("✅ List message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send list message: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending list message: {str(e)}")
            return False

    def mark_message_as_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"

            payload = {
                'messaging_product': 'whatsapp',
                'status': 'read',
                'message_id': message_id
            }

            response = requests.post(url, headers=self.headers, json=payload)

            if response.status_code == 200:
                logger.info(f"✅ Message {message_id} marked as read")
                return True
            else:
                logger.error(f"❌ Failed to mark message as read: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Error marking message as read: {str(e)}")
            return False

    def get_media(self, media_id: str) -> Optional[Dict]:
        """Get media information by ID"""
        try:
            url = f"{self.base_url}/{media_id}"

            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get media: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting media: {str(e)}")
            return None

    def download_media(self, media_url: str) -> Optional[bytes]:
        """Download media content"""
        try:
            response = requests.get(media_url, headers=self.headers)

            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"❌ Failed to download media: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Error downloading media: {str(e)}")
            return None

    def get_business_profile(self) -> Optional[Dict]:
        """Get business profile information"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/whatsapp_business_profile"

            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get business profile: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting business profile: {str(e)}")
            return None

    def update_business_profile(self, profile_data: Dict) -> bool:
        """Update business profile"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/whatsapp_business_profile"

            response = requests.post(url, headers=self.headers, json=profile_data)

            if response.status_code == 200:
                logger.info("✅ Business profile updated successfully")
                return True
            else:
                logger.error(f"❌ Failed to update business profile: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Error updating business profile: {str(e)}")
            return False

    def get_phone_numbers(self) -> Optional[List[Dict]]:
        """Get all phone numbers associated with the WhatsApp Business Account"""
        try:
            url = f"{self.base_url}/{self.waba_id}/phone_numbers"

            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            else:
                logger.error(f"❌ Failed to get phone numbers: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting phone numbers: {str(e)}")
            return None

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verify webhook for WhatsApp subscription"""
        logger.info(f"🔐 Webhook verification attempt")
        logger.info(f"Mode: {mode}, Token: {token}, Challenge: {challenge}")

        if mode == 'subscribe' and token == self.verify_token:
            logger.info("✅ Webhook verified successfully!")
            return challenge
        else:
            logger.warning("❌ Webhook verification failed!")
            return None

    def send_response(self, phone_number: str, response_data: Dict[str, Any]) -> bool:
        """Send response back to WhatsApp user"""
        try:
            content = response_data.get('content', '')
            message_type = response_data.get('type', 'text')

            if message_type == 'text':
                return self.send_text_message(phone_number, content)
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

                        # Extract messages
                        for message in value.get('messages', []):
                            messages.append(message)

            return messages

        except Exception as e:
            logger.error(f"❌ Error extracting webhook data: {str(e)}")
            return []