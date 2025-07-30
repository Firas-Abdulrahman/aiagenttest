import requests
import json
import base64
import os
from typing import Dict, Any
import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. AI features will be disabled.")


class WhatsAppWorkflow:
    def __init__(self, config: Dict[str, str]):
        """Initialize the WhatsApp workflow with configuration"""
        self.config = config

        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE and config.get('openai_api_key'):
            try:
                self.openai_client = openai.OpenAI(api_key=config.get('openai_api_key'))
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.error(f"⚠️ OpenAI initialization failed: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            logger.info("ℹ️ OpenAI not available or API key not provided.")

        # User sessions for cafe ordering
        self.user_sessions = {}

    def handle_whatsapp_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main handler for incoming WhatsApp messages"""
        try:
            logger.info(f"📨 Processing message: {json.dumps(message_data, indent=2)}")

            message_type = self.get_message_type(message_data)
            logger.info(f"📋 Message type detected: {message_type}")

            if message_type == 'text':
                return self.handle_text_message(message_data)
            else:
                return self.create_response(
                    "I only handle text messages for now. Please send a text message to order from Hef Cafe! 😊")

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")
            return self.create_response("Sorry, something went wrong. Please try again.")

    def get_message_type(self, message_data: Dict[str, Any]) -> str:
        """Determine the type of incoming message"""
        if 'text' in message_data:
            return 'text'
        elif 'location' in message_data:
            return 'location'
        elif 'audio' in message_data:
            return 'audio'
        elif 'image' in message_data:
            return 'image'
        elif 'document' in message_data:
            return 'document'
        return 'unknown'

    def handle_text_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process text messages with AI"""
        try:
            text = message_data.get('text', {}).get('body', '')
            phone_number = message_data.get('from')

            # Get customer name
            customer_name = "Customer"
            if 'contacts' in message_data:
                customer_name = message_data['contacts'][0].get('profile', {}).get('name', 'Customer')

            if not text:
                return self.create_response("Please send a text message.")

            logger.info(f"💬 Processing text: {text} from {phone_number}")

            # Get or create user session
            if phone_number not in self.user_sessions:
                self.user_sessions[phone_number] = {
                    'step': 'waiting_for_language',
                    'language': None,
                    'cart': [],
                    'current_category': None,
                    'current_item': None,
                    'service_type': None,
                    'location': None,
                    'total': 0
                }

            session = self.user_sessions[phone_number]

            logger.info(f"📊 Current session: {session}")

            # UPDATE SESSION FIRST, then generate response
            old_step = session['step']
            self.update_session_step(session, text)
            new_step = session['step']

            logger.info(f"🔄 Step changed from {old_step} to {new_step}")

            # Handle specific steps manually for better control
            if old_step == 'waiting_for_language':
                if text.strip() in ['1', 'العربية']:
                    session['language'] = 'arabic'
                    session['step'] = 'waiting_for_category'
                    return self.create_response("""🍽️ **ماذا تريد أن تطلب؟**

يرجى اختيار فئة عن طريق الرد برقم:

**1**: المشروبات الحارة ☕
**2**: المشروبات الباردة 🧊
**3**: قطع الكيك 🍰
**4**: ايس تي 🧊🍃
**5**: فرابتشينو ❄️☕
**6**: العصائر الطبيعية 🍊
**7**: موهيتو 🌿
**8**: ميلك شيك 🥤
**9**: توست 🍞
**10**: السندويشات 🥪
**11**: قطع الكيك 🍰
**12**: كرواسون 🥐
**13**: فطائر 🥧

رد برقم الفئة (1-13).""")

                elif text.strip() in ['2', 'English']:
                    session['language'] = 'english'
                    session['step'] = 'waiting_for_category'
                    return self.create_response("""🍽️ **What would you like to order?**

Please select a category by replying with the number:

**1**: Hot Beverages ☕
**2**: Cold Beverages 🧊
**3**: Cake Slices 🍰
**4**: Iced Tea 🧊🍃
**5**: Frappuccino ❄️☕
**6**: Natural Juices 🍊
**7**: Mojito 🌿
**8**: Milkshake 🥤
**9**: Toast 🍞
**10**: Sandwiches 🥪
**11**: Cake Slices 🍰
**12**: Croissants 🥐
**13**: Savory Pies 🥧

Reply with the category number (1-13).""")
                else:
                    return self.create_response(
                        "☕ **Welcome to Hef Cafe!**\n\nPlease select your preferred language:\n\n**1**: العربية (Arabic)\n**2**: English\n\nReply with 1 or 2.")

            elif old_step == 'waiting_for_category':
                try:
                    category_num = int(text.strip())
                    if 1 <= category_num <= 13:
                        session['current_category'] = category_num
                        session['step'] = 'waiting_for_item'
                        return self.show_category_items(session, category_num)
                    else:
                        return self.create_response("Please select a valid category number (1-13).")
                except:
                    return self.create_response("Please enter a valid number (1-13).")

            elif old_step == 'waiting_for_item':
                try:
                    item_num = int(text.strip())
                    if item_num > 0:
                        session['current_item'] = item_num
                        session['step'] = 'waiting_for_quantity'
                        return self.ask_quantity(session)
                    else:
                        return self.create_response("Please select a valid item number.")
                except:
                    return self.create_response("Please enter a valid item number.")

            # If we get here, use AI for complex responses
            return self.process_with_ai(session, text, customer_name)

        except Exception as e:
            logger.error(f"❌ Error processing text: {str(e)}")
            return self.create_response("Sorry, I couldn't process your message. Please try again.")

    def show_category_items(self, session, category_num):
        """Show items for selected category"""

        # Menu data
        menu_items = {
            1: [  # Hot Beverages
                ("اسبريسو (Espresso)", 3000),
                ("قهوة تركية (Turkish Coffee)", 3000),
                ("شاي عراقي (Iraqi Tea)", 1000),
                ("كابتشينو (Cappuccino)", 5000),
                ("هوت شوكليت (Hot Chocolate)", 5000),
                ("سبانش لاتيه (Spanish Latte)", 6000),
                ("لاتيه كراميل (Caramel Latte)", 5000),
                ("لاتيه فانيلا (Vanilla Latte)", 5000),
                ("لاتيه بندق (Hazelnut Latte)", 5000),
                ("امريكانو (Americano)", 4000),
                ("لاتيه الهيف (Hef Latte)", 6000)
            ],
            2: [  # Cold Beverages
                ("ايس كوفي (Iced Coffee)", 3000),
                ("ايس جوكليت (Iced Chocolate)", 3000),
                ("ايس لاتيه سادة (Plain Iced Latte)", 4000),
                ("كراميل ايس لاتيه (Caramel Iced Latte)", 5000),
                ("فانيلا ايس لاتيه (Vanilla Iced Latte)", 5000),
                ("بندق ايس لاتيه (Hazelnut Iced Latte)", 5000),
                ("ايس امريكانو (Iced Americano)", 4000),
                ("ايس موكا (Iced Mocha)", 5000),
                ("سبانش لاتيه (Spanish Latte)", 6000),
                ("مكس طاقة (Energy Mix)", 6000),
                ("ريد بول عادي (Regular Red Bull)", 3000),
                ("صودا سادة (Plain Soda)", 1000),
                ("ماء (Water)", 1000)
            ],
            3: [  # Cake Slices
                ("فانيلا كيك (Vanilla Cake)", 4000),
                ("لوتس كيك (Lotus Cake)", 4000),
                ("بستاشيو كيك (Pistachio Cake)", 4000),
                ("اوريو كيك (Oreo Cake)", 4000),
                ("سان سباستيان (San Sebastian)", 4000),
                ("كيك كراميل (Caramel Cake)", 4000),
                ("كيك شوكليت (Chocolate Cake)", 4000)
            ]
            # Add more categories as needed
        }

        category_names = {
            1: "Hot Beverages / المشروبات الحارة",
            2: "Cold Beverages / المشروبات الباردة",
            3: "Cake Slices / قطع الكيك"
        }

        items = menu_items.get(category_num, [])
        category_name = category_names.get(category_num, f"Category {category_num}")

        if not items:
            return self.create_response("Sorry, this category is not available yet. Please select another category.")

        response = f"🍽️ **{category_name} Options:**\n\n"

        for i, (name, price) in enumerate(items, 1):
            response += f"**{i}**: {name} - {price} IQD\n"

        response += f"\nPlease reply with the item number (1-{len(items)}) to make your selection."

        return self.create_response(response)

    def ask_quantity(self, session):
        """Ask for quantity with correct unit"""
        category = session.get('current_category')

        if category in [1, 2, 4, 5, 6, 7, 8]:  # Beverages
            if session.get('language') == 'arabic':
                return self.create_response("كم عدد الأكواب التي ترغب بطلبها؟")
            else:
                return self.create_response("How many cups would you like to order?")
        elif category == 3:  # Cake slices
            if session.get('language') == 'arabic':
                return self.create_response("كم شريحة كيك ترغب بطلبها؟")
            else:
                return self.create_response("How many slices would you like to order?")
        else:  # Food items
            if session.get('language') == 'arabic':
                return self.create_response("كم قطعة ترغب بطلبها؟")
            else:
                return self.create_response("How many pieces would you like to order?")

    def process_with_ai(self, session, text, customer_name):
        """Process with AI for complex responses"""
        if not self.openai_client:
            return self.create_response("AI features are not available. Please restart your order by sending 'hi'.")

        ai_prompt = f"""You are Hef Cafe assistant. Current step: {session['step']}. User said: {text}. 

        Continue the conversation based on the current step. Keep responses short and focused on the current step only."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": ai_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=500,
                temperature=0.3
            )

            return self.create_response(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"AI Error: {e}")
            return self.create_response("Please continue with your order or restart by sending 'hi'.")

    def update_session_step(self, session, message_text):
        """Update session step based on user input"""
        current_step = session['step']
        text = message_text.strip()

        logger.info(f"🔄 Updating step from {current_step} with input: {text}")

        # Don't change step here - let the main handler do it
        # This function is now just for logging
        pass

    def create_response(self, text: str) -> Dict[str, Any]:
        """Create text response"""
        return {
            'type': 'text',
            'content': text,
            'timestamp': datetime.datetime.now().isoformat()
        }

    def send_whatsapp_message(self, phone_number: str, response_data: Dict[str, Any]) -> bool:
        """Send response back to WhatsApp"""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.config.get('phone_number_id')}/messages"
            headers = {
                'Authorization': f'Bearer {self.config.get("whatsapp_token")}',
                'Content-Type': 'application/json'
            }

            payload = {
                'messaging_product': 'whatsapp',
                'to': phone_number,
                'text': {'body': response_data['content']}
            }

            logger.info(f"📤 Sending message to {phone_number}")

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                logger.info(f"✅ Message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send message: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp message: {str(e)}")
            return False