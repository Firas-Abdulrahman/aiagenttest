import requests
import json
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
        return 'unknown'

    def handle_text_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process text messages with AI"""
        try:
            text = message_data.get('text', {}).get('body', '')
            phone_number = message_data.get('from')

            # Get customer name
            customer_name = "Customer"
            if 'contacts' in message_data:
                contacts = message_data.get('contacts', [])
                if contacts and len(contacts) > 0:
                    profile = contacts[0].get('profile', {})
                    customer_name = profile.get('name', 'Customer')

            if not text:
                return self.create_response("Please send a text message.")

            logger.info(f"💬 Processing text: {text} from {phone_number}")

            # Get or create user session
            if phone_number not in self.user_sessions:
                self.user_sessions[phone_number] = {
                    'step': 'new_customer',
                    'language': None,
                    'cart': [],
                    'service_type': None,
                    'location': None,
                    'total': 0,
                    'conversation_history': []
                }

            session = self.user_sessions[phone_number]

            # Add message to conversation history
            session['conversation_history'].append({
                'user': text,
                'timestamp': datetime.datetime.now().isoformat()
            })

            logger.info(f"📊 Current session: {session}")

            # Use AI to understand and respond
            if self.openai_client:
                return self.process_with_smart_ai(session, text, customer_name, phone_number)
            else:
                return self.create_response("AI features are not available. Please contact support.")

        except Exception as e:
            logger.error(f"❌ Error processing text: {str(e)}")
            return self.create_response("Sorry, I couldn't process your message. Please try again.")

    def process_with_smart_ai(self, session, text, customer_name, phone_number):
        """Process with smart AI that understands natural language"""

        # Create comprehensive AI prompt
        ai_prompt = f"""You are a friendly, professional WhatsApp chatbot assistant for Hef Cafe, interacting with {customer_name} via WhatsApp.

You are an intelligent AI that can understand natural language orders and conversations. You don't need to follow rigid steps - you can understand when someone says "اريد واحد اسبريسو واحد لاتيه" (I want one espresso and one latte) and process their order naturally.

CURRENT SITUATION:
- Customer: {customer_name}
- Current message: "{text}"
- Session state: {json.dumps(session, indent=2)}
- Conversation history: {session.get('conversation_history', [])}

YOUR PERSONALITY:
- Friendly and helpful
- Can understand Arabic and English naturally
- Smart enough to process complex orders
- Can handle multiple items in one message
- Don't be rigid about steps - be conversational and natural

MENU (memorize this):
**المشروبات الحارة / Hot Beverages:**
- اسبريسو (Espresso) - 3000 IQD
- قهوة تركية (Turkish Coffee) - 3000 IQD  
- شاي عراقي (Iraqi Tea) - 1000 IQD
- كابتشينو (Cappuccino) - 5000 IQD
- هوت شوكليت (Hot Chocolate) - 5000 IQD
- سبانش لاتيه (Spanish Latte) - 6000 IQD
- لاتيه كراميل (Caramel Latte) - 5000 IQD
- لاتيه فانيلا (Vanilla Latte) - 5000 IQD
- لاتيه بندق (Hazelnut Latte) - 5000 IQD
- امريكانو (Americano) - 4000 IQD
- لاتيه الهيف (Hef Latte) - 6000 IQD

**المشروبات الباردة / Cold Beverages:**
- ايس كوفي (Iced Coffee) - 3000 IQD
- ايس جوكليت (Iced Chocolate) - 3000 IQD
- ايس لاتيه سادة (Plain Iced Latte) - 4000 IQD
- كراميل ايس لاتيه (Caramel Iced Latte) - 5000 IQD
- فانيلا ايس لاتيه (Vanilla Iced Latte) - 5000 IQD
- بندق ايس لاتيه (Hazelnut Iced Latte) - 5000 IQD
- ايس امريكانو (Iced Americano) - 4000 IQD
- ايس موكا (Iced Mocha) - 5000 IQD
- سبانش لاتيه (Spanish Latte) - 6000 IQD
- مكس طاقة (Energy Mix) - 6000 IQD
- ريد بول عادي (Regular Red Bull) - 3000 IQD
- صودا سادة (Plain Soda) - 1000 IQD
- ماء (Water) - 1000 IQD

**قطع الكيك / Cake Slices:**
- فانيلا كيك (Vanilla Cake) - 4000 IQD
- لوتس كيك (Lotus Cake) - 4000 IQD
- بستاشيو كيك (Pistachio Cake) - 4000 IQD
- اوريو كيك (Oreo Cake) - 4000 IQD
- سان سباستيان (San Sebastian) - 4000 IQD
- كيك كراميل (Caramel Cake) - 4000 IQD
- كيك شوكليت (Chocolate Cake) - 4000 IQD

**ايس تي / Iced Tea:**
- خوخ ايس تي (Peach Iced Tea) - 5000 IQD
- باشن فروت ايس تي (Passion Fruit Iced Tea) - 5000 IQD

**فرابتشينو / Frappuccino:**
- فرابتشينو كراميل (Caramel Frappuccino) - 5000 IQD
- فرابتشينو فانيلا (Vanilla Frappuccino) - 5000 IQD
- فرابتشينو بندق (Hazelnut Frappuccino) - 5000 IQD
- فرابتشينو شوكليت (Chocolate Frappuccino) - 5000 IQD

**العصائر الطبيعية / Natural Juices:**
- برتقال (Orange) - 4000 IQD
- ليمون (Lemon) - 4000 IQD
- ليمون ونعناع (Lemon & Mint) - 5000 IQD
- بطيخ (Watermelon) - 5000 IQD
- كيوي (Kiwi) - 5000 IQD
- اناناس (Pineapple) - 5000 IQD
- موز وحليب (Banana & Milk) - 5000 IQD
- موز وفراولة (Banana & Strawberry) - 6000 IQD
- موز وشوكليت (Banana & Chocolate) - 6000 IQD
- فراولة (Strawberry) - 5000 IQD

**موهيتو / Mojito:**
- بلو موهيتو (Blue Mojito) - 5000 IQD
- باشن فروت (Passion Fruit) - 5000 IQD
- بلو بيري (Blueberry) - 5000 IQD
- روز بيري (Raspberry) - 5000 IQD
- موهيتو فراولة (Strawberry Mojito) - 5000 IQD
- موهيتو بيتا كولادا (Pina Colada Mojito) - 5000 IQD
- موهيتو علك (Gum Mojito) - 5000 IQD
- موهيتو دراجون (Dragon Mojito) - 5000 IQD
- موهيتو الهيف (Hef Mojito) - 5000 IQD
- موهيتو رمان (Pomegranate Mojito) - 5000 IQD
- خوخ موهيتو (Peach Mojito) - 5000 IQD

**ميلك شيك / Milkshake:**
- فانيلا (Vanilla) - 6000 IQD
- جوكليت (Chocolate) - 6000 IQD
- اوريو (Oreo) - 6000 IQD
- فراولة (Strawberry) - 6000 IQD

**توست / Toast:**
- مارتديلا لحم بالجبن (Beef Mortadella with Cheese) - 2000 IQD
- مارتديلا دجاج بالجبن (Chicken Mortadella with Cheese) - 2000 IQD
- جبن بالزعتر (Cheese with Zaatar) - 2000 IQD

**السندويشات / Sandwiches:**
- سندويش روست لحم (Roast Beef Sandwich) - 3000 IQD
- مارتديلا دجاج (Chicken Mortadella) - 3000 IQD
- جبنة حلوم (Halloumi Cheese) - 3000 IQD
- دجاج بالخضار دايت (Diet Chicken with Vegetables) - 3000 IQD
- ديك رومي (Turkey) - 3000 IQD
- فاهيتا دجاج (Chicken Fajita) - 3000 IQD

**كرواسون / Croissants:**
- كرواسون سادة (Plain Croissant) - 2000 IQD
- كرواسون جبن (Cheese Croissant) - 2000 IQD
- كرواسون شوكليت (Chocolate Croissant) - 2000 IQD

**فطائر / Savory Pies:**
- فطيرة دجاج (Chicken Pie) - 2000 IQD
- فطيرة جبن (Cheese Pie) - 2000 IQD
- فطيرة زعتر (Zaatar Pie) - 2000 IQD

HOW TO RESPOND:
1. If this is their first message or they're greeting you, welcome them warmly to Hef Cafe and ask what they'd like to order
2. If they're making an order (like "اريد واحد اسبريسو واحد لاتيه"), process it naturally:
   - Recognize the items they want
   - Calculate quantities and prices
   - Add to their cart
   - Ask if they want anything else
3. Be conversational and natural - don't be robotic
4. If they ask for the menu, show categories or specific items
5. When they're ready, ask about dine-in/delivery and location
6. Complete the order naturally

IMPORTANT:
- Understand natural language - don't force rigid steps
- Be smart about quantities ("واحد" = 1, "اثنين" = 2, etc.)
- Mix Arabic and English naturally
- Calculate totals automatically
- Be helpful and friendly

Generate a natural, intelligent response that shows you understand what they want."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": ai_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=1000,
                temperature=0.3
            )

            ai_response = response.choices[0].message.content

            # Add AI response to conversation history
            session['conversation_history'].append({
                'bot': ai_response,
                'timestamp': datetime.datetime.now().isoformat()
            })

            # Update session based on AI understanding
            self.update_session_from_ai_response(session, text, ai_response)

            return self.create_response(ai_response)

        except Exception as e:
            logger.error(f"AI Error: {e}")
            return self.create_response(
                "Sorry, I'm having trouble right now. Please try again or say 'menu' to see our options.")

    def update_session_from_ai_response(self, session, user_text, ai_response):
        """Update session based on AI understanding"""

        # Detect language from user input
        if any(arabic_word in user_text for arabic_word in ['اريد', 'منيو', 'طلب', 'مرحبا', 'السلام']):
            session['language'] = 'arabic'
        elif any(english_word in user_text.lower() for english_word in ['want', 'order', 'menu', 'hello', 'hi']):
            session['language'] = 'english'

        # Update step based on conversation progress
        if any(greeting in user_text.lower() for greeting in ['hi', 'hello', 'مرحبا', 'السلام']):
            session['step'] = 'greeting'
        elif any(order_word in user_text for order_word in ['اريد', 'want', 'order', 'طلب']):
            session['step'] = 'ordering'
        elif 'menu' in user_text.lower() or 'منيو' in user_text:
            session['step'] = 'viewing_menu'

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