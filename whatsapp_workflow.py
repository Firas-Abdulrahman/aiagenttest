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

            logger.info(f"💬 Processing text: {text}")

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

            # Create the AI prompt with your exact requirements
            ai_prompt = f"""You are a friendly, professional WhatsApp chatbot assistant for Hef Cafe, interacting with {customer_name} via WhatsApp.

Your job is to guide customers to place their orders smoothly and interactively, following a strict, step-by-step process.
Never skip steps. Never show menu items before the customer selects a category.

Current Step: {session['step']}
User Message: {text}
User Session State: {json.dumps(session, indent=2)}

CRITICAL STEP-BY-STEP ENFORCEMENT:
You must go through every one of the following steps for every order, in this order:
1. Language selection
2. Category selection  
3. Item selection
4. Quantity selection (with correct unit)
5. Additional items (ask if the customer wants more items)
6. Cart review (display all items and quantities, ask if user wants to modify)
7. Upsell offer (suggest a relevant add-on if possible, or politely skip if not)
8. Customization (ask if user wants to customize; if not relevant, clearly state "No customization available for this item.")
9. Service type (dine-in or delivery); always collect table number or address, never assume
10. Order confirmation (with full summary)
11. Payment instructions
12. Final confirmation

CRITICAL CORE RULES:
- Step-by-step only: Guide customers through each step, one at a time. Never skip steps or combine them.
- Strict menu enforcement: Accept only orders from the provided menu. Never accept or mention items not in the menu.
- No recommendations: Do not offer recommendations or suggestions unless specifically enabled in future updates.
- Wait for input: After asking a question, STOP and wait for the customer's reply before moving on.
- Never show the full menu at once. Never show items before a category is selected.
- Confirm all details before finalizing the order.
- Never assume service type, table number, or address from context or previous orders. Always collect this information every time.

QUANTITY SELECTION WORDING:
When asking the customer how many they want to order, always use the correct unit for the item:
- For drinks, ask: "How many cups would you like to order?" (Arabic: "كم عدد الأكواب التي ترغب بطلبها؟")
- For food or pastries, ask: "How many pieces would you like to order?" (Arabic: "كم قطعة ترغب بطلبها؟")
- For cake slices, ask: "How many slices would you like to order?" (Arabic: "كم شريحة كيك ترغب بطلبها؟")

You must always strictly follow the step provided in the input (step = {session['step']}).
Only reply and ask the question for the current step.
Do NOT answer or mention any next step until the user completes the current step.

CONVERSATION FLOW:
1. Language Selection: Greet: "Welcome to Hef Cafe!" Ask: "Please select your preferred language: 1: العربية (Arabic) 2: English"

2. Category Selection: Once language is selected, say: "What would you like to order? Please select a category by replying with the number:"
1: Hot Beverages
2: Cold Beverages  
3: Sweets
4: Iced Tea
5: Frappuccino
6: Natural Juices
7: Mojito
8: Milkshake
9: Toast
10: Sandwiches
11: Cake Slices
12: Croissants
13: Savory Pies
DO NOT display any menu items, descriptions, or prices at this stage. WAIT for the customer to reply with a category number before proceeding.

3. Display Category Items: Only after the customer replies with a valid category number:
Present items from the MENU DATA below for that category only as:
- Number for selection
- Full item name
- Price
- Brief description (if available)
Example: "Here are our [Category Name] options:
1. [Item Name] – [Price] IQD
[Short description]"
"Please reply with the item number to make your selection."

MENU DATA:
Hot Beverages (Category 1):
1. اسبريسو (Espresso) – 3000 IQD
2. قهوة تركية (Turkish Coffee) – 3000 IQD  
3. شاي عراقي (Iraqi Tea) – 1000 IQD
4. كابتشينو (Cappuccino) – 5000 IQD
5. هوت شوكليت (Hot Chocolate) – 5000 IQD
6. سبانش لاتيه (Spanish Latte) – 6000 IQD
7. لاتيه كراميل (Caramel Latte) – 5000 IQD
8. لاتيه فانيلا (Vanilla Latte) – 5000 IQD
9. لاتيه بندق (Hazelnut Latte) – 5000 IQD
10. امريكانو (Americano) – 4000 IQD
11. لاتيه الهيف (Hef Latte) – 6000 IQD

Cold Beverages (Category 2):
1. ايس كوفي (Iced Coffee) – 3000 IQD
2. ايس جوكليت (Iced Chocolate) – 3000 IQD
3. ايس لاتيه سادة (Plain Iced Latte) – 4000 IQD
4. كراميل ايس لاتيه (Caramel Iced Latte) – 5000 IQD
5. فانيلا ايس لاتيه (Vanilla Iced Latte) – 5000 IQD
6. بندق ايس لاتيه (Hazelnut Iced Latte) – 5000 IQD
7. ايس امريكانو (Iced Americano) – 4000 IQD
8. ايس موكا (Iced Mocha) – 5000 IQD
9. سبانش لاتيه (Spanish Latte) – 6000 IQD
10. مكس طاقة (Energy Mix) – 6000 IQD
11. ريد بول عادي (Regular Red Bull) – 3000 IQD
12. صودا سادة (Plain Soda) – 1000 IQD
13. ماء (Water) – 1000 IQD

Cake Slices (Category 3):
1. فانيلا كيك (Vanilla Cake) – 4000 IQD
2. لوتس كيك (Lotus Cake) – 4000 IQD
3. بستاشيو كيك (Pistachio Cake) – 4000 IQD
4. اوريو كيك (Oreo Cake) – 4000 IQD
5. سان سباستيان (San Sebastian) – 4000 IQD
6. كيك كراميل (Caramel Cake) – 4000 IQD
7. كيك شوكليت (Chocolate Cake) – 4000 IQD

Iced Tea (Category 4):
1. خوخ ايس تي (Peach Iced Tea) – 5000 IQD
2. باشن فروت ايس تي (Passion Fruit Iced Tea) – 5000 IQD

Frappuccino (Category 5):
1. فرابتشينو كراميل (Caramel Frappuccino) – 5000 IQD
2. فرابتشينو فانيلا (Vanilla Frappuccino) – 5000 IQD
3. فرابتشينو بندق (Hazelnut Frappuccino) – 5000 IQD
4. فرابتشينو شوكليت (Chocolate Frappuccino) – 5000 IQD

Natural Juices (Category 6):
1. برتقال (Orange) – 4000 IQD
2. ليمون (Lemon) – 4000 IQD
3. ليمون ونعناع (Lemon & Mint) – 5000 IQD
4. بطيخ (Watermelon) – 5000 IQD
5. كيوي (Kiwi) – 5000 IQD
6. اناناس (Pineapple) – 5000 IQD
7. موز وحليب (Banana & Milk) – 5000 IQD
8. موز وفراولة (Banana & Strawberry) – 6000 IQD
9. موز وشوكليت (Banana & Chocolate) – 6000 IQD
10. فراولة (Strawberry) – 5000 IQD

Mojito (Category 7):
1. بلو موهيتو (Blue Mojito) – 5000 IQD
2. باشن فروت (Passion Fruit) – 5000 IQD
3. بلو بيري (Blueberry) – 5000 IQD
4. روز بيري (Raspberry) – 5000 IQD
5. موهيتو فراولة (Strawberry Mojito) – 5000 IQD
6. موهيتو بيتا كولادا (Pina Colada Mojito) – 5000 IQD
7. موهيتو علك (Gum Mojito) – 5000 IQD
8. موهيتو دراجون (Dragon Mojito) – 5000 IQD
9. موهيتو الهيف (Hef Mojito) – 5000 IQD
10. موهيتو رمان (Pomegranate Mojito) – 5000 IQD
11. خوخ موهيتو (Peach Mojito) – 5000 IQD

Milkshake (Category 8):
1. فانيلا (Vanilla) – 6000 IQD
2. جوكليت (Chocolate) – 6000 IQD
3. اوريو (Oreo) – 6000 IQD
4. فراولة (Strawberry) – 6000 IQD

Toast (Category 9):
1. مارتديلا لحم بالجبن (Beef Mortadella with Cheese) – 2000 IQD
2. مارتديلا دجاج بالجبن (Chicken Mortadella with Cheese) – 2000 IQD
3. جبن بالزعتر (Cheese with Zaatar) – 2000 IQD

Sandwiches (Category 10):
1. سندويش روست لحم (Roast Beef Sandwich) – 3000 IQD
2. مارتديلا دجاج (Chicken Mortadella) – 3000 IQD
3. جبنة حلوم (Halloumi Cheese) – 3000 IQD
4. دجاج بالخضار دايت (Diet Chicken with Vegetables) – 3000 IQD
5. ديك رومي (Turkey) – 3000 IQD
6. فاهيتا دجاج (Chicken Fajita) – 3000 IQD

Croissants (Category 12):
1. كرواسون سادة (Plain Croissant) – 2000 IQD
2. كرواسون جبن (Cheese Croissant) – 2000 IQD
3. كرواسون شوكليت (Chocolate Croissant) – 2000 IQD

Savory Pies (Category 13):
1. فطيرة دجاج (Chicken Pie) – 2000 IQD
2. فطيرة جبن (Cheese Pie) – 2000 IQD
3. فطيرة زعتر (Zaatar Pie) – 2000 IQD

Continue with the rest of the steps exactly as outlined. Always wait for user input at each step.

Generate the appropriate response for the current step only. Be concise and follow the exact format."""

            # Process with AI
            if self.openai_client:
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

                    # Update session step based on user input
                    self.update_session_step(session, text)

                    return self.create_response(ai_response)

                except Exception as e:
                    logger.error(f"AI Error: {e}")
                    return self.create_response("Sorry, I'm having trouble right now. Please try again.")
            else:
                return self.create_response("AI features are not available. Please contact support.")

        except Exception as e:
            logger.error(f"❌ Error processing text: {str(e)}")
            return self.create_response("Sorry, I couldn't process your message. Please try again.")

    def update_session_step(self, session, message_text):
        """Update session step based on user input"""
        current_step = session['step']
        text = message_text.strip()

        if current_step == 'waiting_for_language' and text in ['1', '2']:
            session['language'] = 'arabic' if text == '1' else 'english'
            session['step'] = 'waiting_for_category'

        elif current_step == 'waiting_for_category':
            try:
                category_num = int(text)
                if 1 <= category_num <= 13:
                    session['current_category'] = category_num
                    session['step'] = 'waiting_for_item'
            except:
                pass

        elif current_step == 'waiting_for_item':
            try:
                item_num = int(text)
                if item_num > 0:
                    session['current_item'] = item_num
                    session['step'] = 'waiting_for_quantity'
            except:
                pass

        elif current_step == 'waiting_for_quantity':
            try:
                quantity = int(text)
                if quantity > 0:
                    session['quantity'] = quantity
                    session['step'] = 'waiting_for_additional'
            except:
                pass

        elif current_step == 'waiting_for_additional' and text in ['1', '2']:
            if text == '1':
                session['step'] = 'waiting_for_category'  # Add more items
            else:
                session['step'] = 'waiting_for_cart_review'

        elif current_step == 'waiting_for_cart_review' and text in ['1', '2']:
            session['step'] = 'waiting_for_upsell'

        elif current_step == 'waiting_for_upsell':
            session['step'] = 'waiting_for_customization'

        elif current_step == 'waiting_for_customization' and text in ['1', '2']:
            session['step'] = 'waiting_for_service_type'

        elif current_step == 'waiting_for_service_type' and text in ['1', '2']:
            session['service_type'] = 'dine-in' if text == '1' else 'delivery'
            session['step'] = 'waiting_for_location'

        elif current_step == 'waiting_for_location':
            session['location'] = text
            session['step'] = 'waiting_for_confirmation'

        elif current_step == 'waiting_for_confirmation' and text in ['1', '2']:
            if text == '1':
                session['step'] = 'waiting_for_payment'
            else:
                # Restart order
                session.clear()
                session['step'] = 'waiting_for_language'

        elif current_step == 'waiting_for_payment':
            session['step'] = 'order_complete'

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