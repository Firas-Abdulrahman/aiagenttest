import requests
import json
import os
from typing import Dict, Any
import datetime
import logging
import random

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
                    'language': 'auto',
                    'cart': [],
                    'service_type': None,
                    'location': None,
                    'total': 0,
                    'order_complete': False
                }

            session = self.user_sessions[phone_number]

            logger.info(f"📊 Current session: {session}")

            # Detect and maintain language consistency
            if any(arabic_word in text for arabic_word in
                   ['مرحبا', 'اريد', 'منيو', 'قائمة', 'توست', 'نعم', 'لا', 'طلب']):
                session['language'] = 'arabic'
            elif any(english_word in text.lower() for english_word in
                     ['hello', 'hi', 'menu', 'want', 'order', 'yes', 'no', 'proceed']):
                session['language'] = 'english'

            # Use AI to understand and respond
            if self.openai_client:
                return self.process_with_smart_ai(session, text, customer_name, phone_number)
            else:
                return self.create_response("AI features are not available. Please contact support.")

        except Exception as e:
            logger.error(f"❌ Error processing text: {str(e)}")
            return self.create_response("Sorry, I couldn't process your message. Please try again.")

    def process_with_smart_ai(self, session, text, customer_name, phone_number):
        """Process with smart AI that maintains conversation flow"""

        # Determine conversation state
        conversation_context = self.get_conversation_context(session, text)

        # Create AI prompt with better flow control
        ai_prompt = f"""You are a professional Hef Cafe assistant talking to {customer_name}.

CRITICAL RULES:
1. ALWAYS respond in {session['language']} (Arabic or English) - NEVER switch languages mid-conversation
2. COMPLETE the order process - don't get stuck in loops
3. When customer says "proceed" or "yes" after order confirmation, FINALIZE the order
4. Generate order ID and complete the transaction
5. Be decisive and move the conversation forward

CURRENT SITUATION:
- Customer language: {session['language']}
- Customer message: "{text}"
- Current step: {session['step']}
- Cart: {session['cart']}
- Service type: {session['service_type']}
- Location: {session['location']}
- Order complete: {session['order_complete']}

CONVERSATION CONTEXT: {conversation_context}

MENU (Hef Cafe):
**توست / Toast (2000 IQD each):**
- مارتديلا لحم بالجبن / Beef Mortadella with Cheese
- مارتديلا دجاج بالجبن / Chicken Mortadella with Cheese  
- جبن بالزعتر / Cheese with Zaatar

**المشروبات الحارة / Hot Beverages:**
- اسبريسو / Espresso - 3000 IQD
- كابتشينو / Cappuccino - 5000 IQD
- لاتيه / Latte - 5000 IQD

**المشروبات الباردة / Cold Beverages:**
- ايس كوفي / Iced Coffee - 3000 IQD
- ايس لاتيه / Iced Latte - 4000 IQD

RESPONSE GUIDELINES:
- If showing menu: Show categories clearly
- If taking order: Add to cart and ask for more items or proceed
- If customer wants to proceed: Ask dine-in or delivery
- If dine-in: Ask for table number (1-7)
- If they confirm final order: COMPLETE with order ID and payment info
- NEVER get stuck repeating the same question

IMPORTANT: If customer has confirmed their order and said "proceed" or "yes", COMPLETE THE ORDER with:
1. Final order summary
2. Generate order ID (like HEF1234 or HEF5678 - use any 4 digit number)
3. Payment instructions (pay at cashier)
4. Thank them and mark order as complete

Be natural, helpful, and COMPLETE the transaction properly."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": ai_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=800,
                temperature=0.2  # Lower temperature for more consistent responses
            )

            ai_response = response.choices[0].message.content

            # Update session based on the interaction
            self.update_session_intelligently(session, text, ai_response)

            # If order should be complete, mark it
            if any(completion_word in text.lower() for completion_word in
                   ['proceed', 'yes', 'نعم', 'موافق']) and session.get('service_type') and session.get('location'):
                if 'order id' in ai_response.lower() or 'HEF' in ai_response:
                    session['order_complete'] = True
                    session['step'] = 'completed'

            return self.create_response(ai_response)

        except Exception as e:
            logger.error(f"AI Error: {e}")
            return self.create_response("Sorry, I'm having trouble right now. Please try again.")

    def get_conversation_context(self, session, text):
        """Get context about where we are in the conversation"""

        if session['order_complete']:
            return "Order is already complete"

        if not session['cart']:
            return "Customer hasn't ordered anything yet"

        if session['cart'] and not session['service_type']:
            return "Customer has items in cart, need to ask dine-in or delivery"

        if session['service_type'] and not session['location']:
            return "Need to get table number or delivery address"

        if session['cart'] and session['service_type'] and session['location']:
            if any(proceed_word in text.lower() for proceed_word in ['proceed', 'yes', 'نعم', 'موافق']):
                return "Customer wants to complete order - FINALIZE IT NOW"
            return "Ready to finalize order"

        return "Normal conversation flow"

    def update_session_intelligently(self, session, user_text, ai_response):
        """Update session based on conversation progress"""

        # Detect if items were added to cart
        if any(item_word in user_text.lower() for item_word in
               ['توست', 'toast', 'اسبريسو', 'espresso', 'قهوة', 'coffee']):
            if not session['cart']:  # First item
                session['cart'] = [{'item': 'toast', 'price': 2000}]  # Simplified
                session['total'] = 2000
                session['step'] = 'has_items'

        # Detect service type
        if 'dine' in user_text.lower() or 'في المقهى' in user_text:
            session['service_type'] = 'dine-in'
            session['step'] = 'need_location'
        elif 'delivery' in user_text.lower() or 'توصيل' in user_text:
            session['service_type'] = 'delivery'
            session['step'] = 'need_location'

        # Detect location/table
        if 'table' in user_text.lower() or 'طاولة' in user_text or any(str(i) in user_text for i in range(1, 8)):
            session['location'] = user_text
            session['step'] = 'ready_to_complete'

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