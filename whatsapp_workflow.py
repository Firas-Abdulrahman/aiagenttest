import requests
import json
import base64
import os
from typing import Dict, Any, Optional
import io
import datetime

# Try to import OpenAI, but make it optional
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not installed. AI features will be disabled.")

# Try to import PIL, but make it optional
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not installed. Image processing will be limited.")


class WhatsAppWorkflow:
    def __init__(self, config: Dict[str, str]):
        """
        Initialize the WhatsApp workflow with configuration

        Args:
            config: Dictionary containing API keys and endpoints
                   - whatsapp_token: WhatsApp Business API token
                   - openai_api_key: OpenAI API key (optional)
                   - phone_number_id: WhatsApp phone number ID
        """
        self.config = config

        # Initialize OpenAI client if available and configured
        if OPENAI_AVAILABLE and config.get('openai_api_key'):
            try:
                self.openai_client = openai.OpenAI(api_key=config.get('openai_api_key'))
                print("✅ OpenAI client initialized")
            except Exception as e:
                print(f"⚠️ OpenAI initialization failed: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            if not OPENAI_AVAILABLE:
                print("ℹ️ OpenAI not available. Install with: pip install openai")
            else:
                print("ℹ️ OpenAI API key not provided. AI features disabled.")

    def handle_whatsapp_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main handler for incoming WhatsApp messages

        Args:
            message_data: WhatsApp webhook payload

        Returns:
            Response data with appropriate action
        """
        try:
            print(f"📨 Processing message: {json.dumps(message_data, indent=2)}")

            message_type = self.get_message_type(message_data)
            print(f"📋 Message type detected: {message_type}")

            if message_type == 'location':
                return self.handle_location_message(message_data)
            elif message_type == 'audio':
                return self.handle_audio_message(message_data)
            elif message_type == 'image':
                return self.handle_image_message(message_data)
            elif message_type == 'text':
                return self.handle_text_message(message_data)
            elif message_type == 'document':
                return self.handle_document_message(message_data)
            else:
                return self.create_response(
                    f"Sorry, I don't support '{message_type}' message type yet. I can handle text, images, audio, location, and documents.")

        except Exception as e:
            print(f"❌ Error handling message: {str(e)}")
            return self.create_response("Sorry, something went wrong processing your message. Please try again.")

    def get_message_type(self, message_data: Dict[str, Any]) -> str:
        """Determine the type of incoming message"""
        if 'location' in message_data:
            return 'location'
        elif 'audio' in message_data:
            return 'audio'
        elif 'image' in message_data:
            return 'image'
        elif 'document' in message_data:
            return 'document'
        elif 'video' in message_data:
            return 'video'
        elif 'text' in message_data:
            return 'text'
        elif 'button' in message_data:
            return 'button'
        elif 'interactive' in message_data:
            return 'interactive'
        return 'unknown'

    def handle_location_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process location messages and generate code location"""
        try:
            location = message_data.get('location', {})
            latitude = location.get('latitude')
            longitude = location.get('longitude')
            name = location.get('name', 'Unknown location')
            address = location.get('address', 'No address provided')

            if not latitude or not longitude:
                return self.create_response("❌ Invalid location data received.")

            # Generate a location code
            location_code = f"LOC_{abs(hash(f'{latitude}{longitude}'))}"[:10]

            # Create detailed response
            response_text = f"""📍 **Location Received!**

**Details:**
• Name: {name}
• Address: {address}
• Coordinates: {latitude}, {longitude}
• Location Code: `{location_code}`

**Google Maps:** https://maps.google.com/?q={latitude},{longitude}

Thank you for sharing your location! 🗺️"""

            return self.create_response(response_text)

        except Exception as e:
            print(f"❌ Error processing location: {str(e)}")
            return self.create_response("Sorry, I couldn't process your location. Please try again.")

    def handle_audio_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process audio messages - transcribe and respond"""
        try:
            if not self.openai_client:
                return self.create_response(
                    "🎵 I received your voice message! However, audio transcription is not available right now. Please send a text message instead.")

            # Get audio info
            audio_info = message_data.get('audio', {})
            audio_id = audio_info.get('id')

            if not audio_id:
                return self.create_response("❌ No audio ID found in message.")

            print(f"🎵 Processing audio with ID: {audio_id}")

            # Download audio file
            audio_data = self.download_media(audio_id)

            if not audio_data:
                return self.create_response("❌ Could not download audio file.")

            # Transcribe audio
            transcription = self.transcribe_audio(audio_data)

            if not transcription:
                return self.create_response(
                    "🎵 I received your voice message but couldn't understand the audio. Could you please send it as text instead?")

            print(f"📝 Transcription: {transcription}")

            # Process transcription with AI
            ai_response = self.process_with_ai(
                f"User sent a voice message that says: '{transcription}'. Please respond appropriately.")

            # Create response with transcription
            response_text = f"🎵 **Voice Message Received**\n\n📝 **I heard:** {transcription}\n\n💬 **My response:** {ai_response}"

            return self.create_response(response_text)

        except Exception as e:
            print(f"❌ Error processing audio: {str(e)}")
            return self.create_response(
                "🎵 I received your voice message but couldn't process it. Please try sending a text message instead.")

    def handle_image_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process image messages - analyze and respond"""
        try:
            # Get image info
            image_info = message_data.get('image', {})
            image_id = image_info.get('id')
            caption = image_info.get('caption', '')

            if not image_id:
                return self.create_response("❌ No image ID found in message.")

            print(f"🖼️ Processing image with ID: {image_id}")

            # Download image
            image_data = self.download_media(image_id)

            if not image_data:
                return self.create_response("❌ Could not download image.")

            # Analyze image if OpenAI is available
            if self.openai_client:
                analysis = self.analyze_image(image_data)
                response_text = f"🖼️ **Image Received!**\n\n🔍 **Analysis:** {analysis}"

                if caption:
                    response_text += f"\n\n💬 **Your caption:** {caption}"
                    # Also process the caption with AI
                    caption_response = self.process_with_ai(
                        f"User sent an image with caption: '{caption}'. The image shows: {analysis}. Please respond appropriately.")
                    response_text += f"\n\n🤖 **My thoughts:** {caption_response}"
            else:
                response_text = f"🖼️ **Image Received!**\n\nI can see you sent me an image"
                if caption:
                    response_text += f" with the caption: '{caption}'"
                response_text += ". However, image analysis is not available right now. Please describe what you'd like me to help you with!"

            return self.create_response(response_text)

        except Exception as e:
            print(f"❌ Error processing image: {str(e)}")
            return self.create_response(
                "🖼️ I received your image but couldn't process it. Please try describing what you need help with!")

    def handle_document_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process document messages"""
        try:
            doc_info = message_data.get('document', {})
            filename = doc_info.get('filename', 'Unknown file')
            mime_type = doc_info.get('mime_type', 'Unknown type')

            response_text = f"📄 **Document Received!**\n\n📁 **Filename:** {filename}\n📋 **Type:** {mime_type}\n\n💡 I received your document but cannot process file contents yet. Please let me know how I can help you with it!"

            return self.create_response(response_text)

        except Exception as e:
            print(f"❌ Error processing document: {str(e)}")
            return self.create_response(
                "📄 I received your document but couldn't process it. Please let me know how I can help!")

    def handle_text_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process text messages"""
        try:
            text = message_data.get('text', {}).get('body', '')

            if not text:
                return self.create_response("❌ Empty message received.")

            print(f"💬 Processing text: {text}")

            # Check for special commands
            text_lower = text.lower().strip()

            if text_lower in ['hello', 'hi', 'hey', 'hola', 'سلام', 'مرحبا']:
                return self.create_response(
                    "👋 Hello! How can I help you today?\n\n💡 I can help with:\n• Answering questions\n• Processing voice messages\n• Analyzing images\n• Location sharing\n• Coffee orders (/coffee)")

            elif text_lower in ['help', '/help', 'مساعدة']:
                return self.create_response("""🆘 **Help Menu**

**What I can do:**
• 💬 Answer questions and chat
• 🎵 Transcribe voice messages
• 🖼️ Analyze images
• 📍 Process location sharing
• ☕ Take coffee orders (/coffee)
• 📄 Receive documents

**Commands:**
• `/help` - Show this menu
• `/coffee [order]` - Place coffee order
• `hello` - Greet me

**Tips:**
• Send me voice messages and I'll transcribe them
• Share images and I'll describe what I see
• Ask me anything!""")

            elif text_lower.startswith('/coffee'):
                return self.handle_coffee_order(text)

            elif text_lower in ['status', '/status']:
                return self.get_bot_status()

            # Process with AI if available
            if self.openai_client:
                ai_response = self.process_with_ai(text)
                return self.create_response(ai_response)
            else:
                # Simple responses without AI
                return self.create_simple_response(text)

        except Exception as e:
            print(f"❌ Error processing text: {str(e)}")
            return self.create_response("Sorry, I couldn't process your message. Please try again.")

    def create_simple_response(self, text: str) -> Dict[str, Any]:
        """Create simple responses without AI"""
        text_lower = text.lower()

        if any(word in text_lower for word in ['how are you', 'how r u', 'كيف حالك']):
            return self.create_response("I'm doing great, thank you for asking! 😊 How can I help you today?")

        elif any(word in text_lower for word in ['thank', 'thanks', 'شكرا']):
            return self.create_response("You're very welcome! 😊 Is there anything else I can help you with?")

        elif any(word in text_lower for word in ['bye', 'goodbye', 'see you', 'مع السلامة']):
            return self.create_response("Goodbye! 👋 Feel free to message me anytime you need help!")

        else:
            return self.create_response(
                f"📝 You said: \"{text}\"\n\n🤖 I received your message! AI features are currently disabled, but I'm here and ready to help. Try sending /help to see what I can do!")

    def download_media(self, media_id: str) -> Optional[bytes]:
        """Download media file from WhatsApp"""
        try:
            # First, get the media URL
            url = f"https://graph.facebook.com/v18.0/{media_id}"
            headers = {
                'Authorization': f'Bearer {self.config.get("whatsapp_token")}'
            }

            print(f"📡 Getting media URL for ID: {media_id}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            media_info = response.json()
            media_url = media_info.get('url')

            if not media_url:
                print("❌ No media URL found")
                return None

            print(f"📡 Downloading media from: {media_url}")

            # Download the actual media file
            media_response = requests.get(media_url, headers=headers)
            media_response.raise_for_status()

            print(f"✅ Media downloaded successfully, size: {len(media_response.content)} bytes")
            return media_response.content

        except Exception as e:
            print(f"❌ Error downloading media: {str(e)}")
            return None

    def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using OpenAI Whisper"""
        try:
            if not self.openai_client:
                return ""

            print("🎵 Transcribing audio with Whisper...")

            # Create audio file object
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.ogg"  # WhatsApp usually sends OGG files

            transcript = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="auto"  # Auto-detect language
            )

            print(f"✅ Transcription successful: {transcript.text}")
            return transcript.text

        except Exception as e:
            print(f"❌ Transcription error: {str(e)}")
            return ""

    def analyze_image(self, image_data: bytes) -> str:
        """Analyze image content using OpenAI Vision"""
        try:
            if not self.openai_client:
                return "Image analysis not available"

            print("🖼️ Analyzing image with GPT-4 Vision...")

            # Convert image to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')

            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text",
                             "text": "Please describe what you see in this image in detail. Be helpful and conversational."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=500
            )

            analysis = response.choices[0].message.content
            print(f"✅ Image analysis successful")
            return analysis

        except Exception as e:
            print(f"❌ Image analysis error: {str(e)}")
            return "I can see the image but couldn't analyze it properly. Please describe what you'd like me to help you with!"

    def process_with_ai(self, text: str) -> str:
        """Process text with AI (OpenAI GPT)"""
        try:
            if not self.openai_client:
                return f"You said: {text}"

            print("🤖 Processing with GPT...")

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",
                     "content": "You are a helpful WhatsApp assistant. Keep responses concise, friendly, and helpful. Use emojis appropriately. Support both English and Arabic users."},
                    {"role": "user", "content": text}
                ],
                max_tokens=800,
                temperature=0.7
            )

            ai_response = response.choices[0].message.content
            print(f"✅ AI response generated")
            return ai_response

        except Exception as e:
            print(f"❌ AI processing error: {str(e)}")
            return "I'm having trouble processing your request right now. Please try again in a moment!"

    def handle_coffee_order(self, text: str) -> Dict[str, Any]:
        """Handle coffee ordering command"""
        try:
            order_details = text.replace('/coffee', '').strip()

            if not order_details:
                response = """☕ **Coffee Order System**

Welcome to our coffee shop! 🏪

**How to order:**
Type `/coffee` followed by your order

**Example:**
`/coffee Large Latte with extra shot`

**Popular options:**
• Espresso ☕
• Latte 🥛
• Cappuccino ☕
• Americano ☕
• Mocha 🍫

What would you like to order? 😊"""
            else:
                order_id = f"ORD_{abs(hash(order_details + str(datetime.datetime.now())))}"[:8]
                response = f"""☕ **Coffee Order Confirmed!**

**Order Details:**
• Item: {order_details}
• Order ID: `{order_id}`
• Status: ✅ Confirmed
• Estimated time: 10-15 minutes

Thank you for your order! We'll prepare it right away! 🚀

*Reply with `/coffee status {order_id}` to check your order status*"""

            return self.create_response(response)

        except Exception as e:
            print(f"❌ Error processing coffee order: {str(e)}")
            return self.create_response("☕ Sorry, there was an issue with your coffee order. Please try again!")

    def get_bot_status(self) -> Dict[str, Any]:
        """Get bot status information"""
        try:
            status_text = f"""🤖 **Bot Status Report**

**System Status:** ✅ Online
**Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Available Features:**
• 💬 Text messaging: ✅ Active
• 🎵 Audio transcription: {'✅ Active' if self.openai_client else '❌ Disabled'}
• 🖼️ Image analysis: {'✅ Active' if self.openai_client else '❌ Disabled'}
• 📍 Location processing: ✅ Active
• 📄 Document handling: ✅ Basic
• 🤖 AI responses: {'✅ Active' if self.openai_client else '❌ Disabled'}

**Commands Available:**
• `/help` - Show help menu
• `/coffee` - Coffee ordering
• `/status` - This status report

**Ready to help!** 😊"""

            return self.create_response(status_text)

        except Exception as e:
            print(f"❌ Error getting status: {str(e)}")
            return self.create_response("❌ Could not get status information.")

    def create_response(self, text: str) -> Dict[str, Any]:
        """Create text response"""
        return {
            'type': 'text',
            'content': text,
            'timestamp': self.get_timestamp()
        }

    def create_audio_response(self, audio_data: bytes) -> Dict[str, Any]:
        """Create audio response"""
        return {
            'type': 'audio',
            'content': base64.b64encode(audio_data).decode('utf-8'),
            'timestamp': self.get_timestamp()
        }

    def get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.datetime.now().isoformat()

    def send_whatsapp_message(self, phone_number: str, response_data: Dict[str, Any]) -> bool:
        """Send response back to WhatsApp"""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.config.get('phone_number_id')}/messages"
            headers = {
                'Authorization': f'Bearer {self.config.get("whatsapp_token")}',
                'Content-Type': 'application/json'
            }

            if response_data['type'] == 'text':
                payload = {
                    'messaging_product': 'whatsapp',
                    'to': phone_number,
                    'text': {'body': response_data['content']}
                }
            elif response_data['type'] == 'audio':
                # For audio responses, you'd need to upload the audio first
                # This is a simplified version
                payload = {
                    'messaging_product': 'whatsapp',
                    'to': phone_number,
                    'type': 'text',
                    'text': {'body': 'Audio response (upload feature not implemented yet)'}
                }

            print(f"📤 Sending message to {phone_number}")
            print(f"📋 Payload: {json.dumps(payload, indent=2)}")

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                print(f"✅ Message sent successfully")
                print(f"📋 Response: {response.json()}")
                return True
            else:
                print(f"❌ Failed to send message: {response.status_code}")
                print(f"📋 Error response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error sending WhatsApp message: {str(e)}")
            return False