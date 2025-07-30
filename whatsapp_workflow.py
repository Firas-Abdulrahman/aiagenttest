import requests
import json
import os
from typing import Dict, Any
import datetime
import logging
import re

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


class AIWhatsAppWorkflow:
    def __init__(self, config: Dict[str, str]):
        """Initialize the AI-powered WhatsApp workflow"""
        self.config = config

        # Initialize OpenAI client
        if OPENAI_AVAILABLE and config.get('openai_api_key'):
            try:
                self.openai_client = openai.OpenAI(api_key=config.get('openai_api_key'))
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.error(f"⚠️ OpenAI initialization failed: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            logger.info("ℹ️ OpenAI not available - falling back to rule-based responses")

        # User sessions for AI conversation and ordering
        self.user_sessions = {}

        # Menu data - Complete menu
        self.menu_data = {
            1: {  # Hot Beverages
                "name_ar": "المشروبات الحارة",
                "name_en": "Hot Beverages",
                "items": [
                    {"name_ar": "اسبريسو", "name_en": "Espresso", "price": 3000, "unit": "cups"},
                    {"name_ar": "قهوة تركية", "name_en": "Turkish Coffee", "price": 3000, "unit": "cups"},
                    {"name_ar": "شاي عراقي", "name_en": "Iraqi Tea", "price": 1000, "unit": "cups"},
                    {"name_ar": "كابتشينو", "name_en": "Cappuccino", "price": 5000, "unit": "cups"},
                    {"name_ar": "هوت شوكليت", "name_en": "Hot Chocolate", "price": 5000, "unit": "cups"},
                    {"name_ar": "لاتيه كراميل", "name_en": "Caramel Latte", "price": 5000, "unit": "cups"},
                    {"name_ar": "لاتيه فانيلا", "name_en": "Vanilla Latte", "price": 5000, "unit": "cups"},
                    {"name_ar": "امريكانو", "name_en": "Americano", "price": 4000, "unit": "cups"}
                ]
            },
            2: {  # Cold Beverages
                "name_ar": "المشروبات الباردة",
                "name_en": "Cold Beverages",
                "items": [
                    {"name_ar": "ايس كوفي", "name_en": "Iced Coffee", "price": 3000, "unit": "cups"},
                    {"name_ar": "ايس لاتيه", "name_en": "Iced Latte", "price": 4000, "unit": "cups"},
                    {"name_ar": "كراميل ايس لاتيه", "name_en": "Caramel Iced Latte", "price": 5000, "unit": "cups"},
                    {"name_ar": "ايس امريكانو", "name_en": "Iced Americano", "price": 4000, "unit": "cups"}
                ]
            },
            3: {  # Sweets
                "name_ar": "الحلويات",
                "name_en": "Sweets",
                "items": [
                    {"name_ar": "كيك شوكليت", "name_en": "Chocolate Cake", "price": 4000, "unit": "pieces"},
                    {"name_ar": "كيك فانيلا", "name_en": "Vanilla Cake", "price": 4000, "unit": "pieces"}
                ]
            },
            4: {  # Iced Tea
                "name_ar": "ايس تي",
                "name_en": "Iced Tea",
                "items": [
                    {"name_ar": "ايس تي ليمون", "name_en": "Lemon Iced Tea", "price": 3500, "unit": "cups"},
                    {"name_ar": "ايس تي خوخ", "name_en": "Peach Iced Tea", "price": 3500, "unit": "cups"}
                ]
            },
            5: {  # Frappuccino
                "name_ar": "فرابتشينو",
                "name_en": "Frappuccino",
                "items": [
                    {"name_ar": "فرابتشينو كراميل", "name_en": "Caramel Frappuccino", "price": 6000, "unit": "cups"},
                    {"name_ar": "فرابتشينو موكا", "name_en": "Mocha Frappuccino", "price": 6000, "unit": "cups"}
                ]
            },
            9: {  # Toast
                "name_ar": "توست",
                "name_en": "Toast",
                "items": [
                    {"name_ar": "مارتديلا لحم بالجبن", "name_en": "Beef Mortadella with Cheese", "price": 2000,
                     "unit": "pieces"},
                    {"name_ar": "مارتديلا دجاج بالجبن", "name_en": "Chicken Mortadella with Cheese", "price": 2000,
                     "unit": "pieces"},
                    {"name_ar": "جبن بالزعتر", "name_en": "Cheese with Zaatar", "price": 2000, "unit": "pieces"}
                ]
            },
            11: {  # Cake Slices
                "name_ar": "قطع الكيك",
                "name_en": "Cake Slices",
                "items": [
                    {"name_ar": "فانيلا كيك", "name_en": "Vanilla Cake", "price": 4000, "unit": "slices"},
                    {"name_ar": "لوتس كيك", "name_en": "Lotus Cake", "price": 4000, "unit": "slices"},
                    {"name_ar": "شوكليت كيك", "name_en": "Chocolate Cake", "price": 4000, "unit": "slices"}
                ]
            }
        }

        # AI System Prompt
        self.system_prompt = """You are an AI assistant for Hef Cafe, a cozy Iraqi cafe. You help customers place orders through WhatsApp in a friendly, conversational way.

PERSONALITY:
- Warm, friendly, and helpful
- Understand different Arabic dialects (Iraqi, Gulf, Levantine, Egyptian, etc.)
- Can communicate in Arabic and English naturally
- Use appropriate emojis and casual language
- Be patient and understanding with customers

MENU KNOWLEDGE:
You have access to the complete menu with categories:
1. Hot Beverages (المشروبات الحارة) - Espresso, Turkish Coffee, Iraqi Tea, Cappuccino, Hot Chocolate, Caramel Latte, Vanilla Latte, Americano
2. Cold Beverages (المشروبات الباردة) - Iced Coffee, Iced Latte, Caramel Iced Latte, Iced Americano  
3. Sweets (الحلويات) - Chocolate Cake, Vanilla Cake
4. Iced Tea (ايس تي) - Lemon Iced Tea, Peach Iced Tea
5. Frappuccino (فرابتشينو) - Caramel Frappuccino, Mocha Frappuccino
9. Toast (توست) - Beef Mortadella with Cheese, Chicken Mortadella with Cheese, Cheese with Zaatar
11. Cake Slices (قطع الكيك) - Vanilla Cake, Lotus Cake, Chocolate Cake

ORDERING PROCESS:
1. Greet customers warmly and ask how you can help
2. Help them browse the menu naturally through conversation
3. When they mention items, confirm details (quantity, customizations)
4. Keep track of their order in a conversational way
5. Ask about service type (dine-in or delivery)
6. Collect location/table number
7. Confirm the final order with total price
8. Generate order ID and thank them

CONVERSATION RULES:
- Always respond naturally, not with rigid menu lists unless requested
- Understand various ways customers might ask for items (slang, dialects, abbreviations)
- If they ask about unavailable items, suggest similar alternatives
- Handle pricing questions naturally
- Be flexible with how they want to order (one item at a time vs. multiple items)
- If they seem confused, offer to show the full menu
- Handle small talk and questions about the cafe

IMPORTANT:
- Always extract and track: items ordered, quantities, special requests, service type, location
- Calculate totals accurately
- Generate realistic order IDs (HEF + 4 digits)
- Handle both Arabic and English seamlessly
- Understand context from previous messages in the conversation"""

    def get_menu_context(self) -> str:
        """Generate menu context for AI"""
        menu_text = "CURRENT MENU WITH PRICES:\n\n"

        for category_id, category in self.menu_data.items():
            menu_text += f"{category_id}. {category['name_en']} ({category['name_ar']}):\n"
            for item in category['items']:
                menu_text += f"   - {item['name_en']} ({item['name_ar']}) - {item['price']} IQD\n"
            menu_text += "\n"

        return menu_text

    def handle_whatsapp_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main handler for incoming WhatsApp messages"""
        try:
            logger.info(f"📨 Processing message: {json.dumps(message_data, indent=2)}")

            message_type = self.get_message_type(message_data)
            logger.info(f"📋 Message type detected: {message_type}")

            if message_type == 'text':
                return self.handle_text_message(message_data)
            else:
                return self.create_ai_response(
                    "I can help you with text messages. Please send me a message to start ordering! 😊",
                    message_data.get('from', ''), {}
                )

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")
            return self.create_ai_response(
                "Sorry, something went wrong. Please try again! 🙏",
                message_data.get('from', ''), {}
            )

    def get_message_type(self, message_data: Dict[str, Any]) -> str:
        """Determine the type of incoming message"""
        if 'text' in message_data:
            return 'text'
        return 'unknown'

    def handle_text_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process text messages using AI"""
        try:
            text = message_data.get('text', {}).get('body', '').strip()
            phone_number = message_data.get('from')

            # Get customer name
            customer_name = "Customer"
            if 'contacts' in message_data:
                contacts = message_data.get('contacts', [])
                if contacts and len(contacts) > 0:
                    profile = contacts[0].get('profile', {})
                    customer_name = profile.get('name', 'Customer')

            if not text:
                return self.create_ai_response(
                    "Please send me a message! 😊",
                    phone_number, {}
                )

            logger.info(f"💬 Processing text: {text} from {phone_number}")

            # Get or create user session
            if phone_number not in self.user_sessions:
                self.user_sessions[phone_number] = {
                    'conversation_history': [],
                    'current_order': {
                        'items': [],
                        'total': 0,
                        'service_type': None,
                        'location': None,
                        'customer_name': customer_name
                    },
                    'language_preference': 'auto'  # Auto-detect from conversation
                }

            session = self.user_sessions[phone_number]

            # Add user message to conversation history
            session['conversation_history'].append({
                'role': 'user',
                'content': text,
                'timestamp': datetime.datetime.now().isoformat()
            })

            # Generate AI response
            ai_response = self.generate_ai_response(session, text, customer_name)

            # Add AI response to conversation history
            session['conversation_history'].append({
                'role': 'assistant',
                'content': ai_response,
                'timestamp': datetime.datetime.now().isoformat()
            })

            # Keep conversation history manageable (last 20 messages)
            if len(session['conversation_history']) > 20:
                session['conversation_history'] = session['conversation_history'][-20:]

            return self.create_ai_response(ai_response, phone_number, session)

        except Exception as e:
            logger.error(f"❌ Error processing text: {str(e)}")
            return self.create_ai_response(
                "Sorry, I couldn't understand that. Can you try again? 🤔",
                phone_number, {}
            )

    def generate_ai_response(self, session: Dict, user_message: str, customer_name: str) -> str:
        """Generate AI response using OpenAI"""
        if not self.openai_client:
            return self.fallback_response(user_message, session)

        try:
            # Build conversation context
            messages = [
                {"role": "system", "content": self.system_prompt + "\n\n" + self.get_menu_context()}
            ]

            # Add recent conversation history (last 10 messages)
            recent_history = session['conversation_history'][-10:] if session['conversation_history'] else []

            for msg in recent_history:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })

            # Add current order context if exists
            current_order = session['current_order']
            if current_order['items']:
                order_context = f"\nCURRENT ORDER STATE:\n"
                order_context += f"Customer: {customer_name}\n"
                order_context += f"Items: {json.dumps(current_order['items'], ensure_ascii=False)}\n"
                order_context += f"Total: {current_order['total']} IQD\n"
                order_context += f"Service: {current_order['service_type']}\n"
                order_context += f"Location: {current_order['location']}\n"

                messages[0]["content"] += order_context

            # Add user's current message
            messages.append({"role": "user", "content": user_message})

            # Generate response
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )

            ai_response = response.choices[0].message.content.strip()

            # Extract order information from the AI response if present
            self.extract_order_info(ai_response, session, user_message)

            return ai_response

        except Exception as e:
            logger.error(f"❌ OpenAI API error: {str(e)}")
            return self.fallback_response(user_message, session)

    def extract_order_info(self, ai_response: str, session: Dict, user_message: str):
        """Extract order information from AI response and user message"""
        try:
            current_order = session['current_order']

            # Simple extraction logic - you can make this more sophisticated
            # Look for mentions of menu items in user message
            user_lower = user_message.lower()

            for category_id, category in self.menu_data.items():
                for item in category['items']:
                    # Check if item is mentioned in Arabic or English
                    if (item['name_ar'].lower() in user_lower or
                            item['name_en'].lower() in user_lower):

                        # Extract quantity (look for numbers)
                        quantity = 1  # default
                        numbers = re.findall(r'\d+', user_message)
                        if numbers:
                            quantity = int(numbers[0])

                        # Check if item already in order
                        existing_item = None
                        for order_item in current_order['items']:
                            if order_item['name_ar'] == item['name_ar']:
                                existing_item = order_item
                                break

                        if existing_item:
                            existing_item['quantity'] += quantity
                            existing_item['subtotal'] = existing_item['quantity'] * item['price']
                        else:
                            current_order['items'].append({
                                'name_ar': item['name_ar'],
                                'name_en': item['name_en'],
                                'price': item['price'],
                                'quantity': quantity,
                                'subtotal': item['price'] * quantity
                            })

                        # Recalculate total
                        current_order['total'] = sum(item['subtotal'] for item in current_order['items'])

                        logger.info(f"📝 Added to order: {item['name_ar']} x{quantity}")
                        break

            # Extract service type
            if any(word in user_lower for word in ['توصيل', 'delivery', 'deliver']):
                current_order['service_type'] = 'delivery'
            elif any(word in user_lower for word in ['تناول', 'dine', 'table']):
                current_order['service_type'] = 'dine-in'

            # Extract location/table number
            table_numbers = re.findall(r'(?:table|طاولة|رقم)\s*(\d+)', user_lower)
            if table_numbers:
                current_order['location'] = f"Table {table_numbers[0]}"

        except Exception as e:
            logger.error(f"❌ Error extracting order info: {str(e)}")

    def fallback_response(self, user_message: str, session: Dict) -> str:
        """Fallback response when OpenAI is not available"""
        user_lower = user_message.lower()

        # Simple rule-based responses
        if any(word in user_lower for word in ['مرحبا', 'hello', 'hi', 'hey', 'سلام']):
            return "مرحباً بك في مقهى هيف! 😊 كيف يمكنني مساعدتك اليوم؟\n\nWelcome to Hef Cafe! How can I help you today?"

        elif any(word in user_lower for word in ['menu', 'قائمة', 'منيو']):
            return self.show_full_menu()

        elif any(word in user_lower for word in ['price', 'سعر', 'كم']):
            return "يمكنني مساعدتك في الأسعار! ما هو المشروب أو الطعام الذي تريد معرفة سعره؟\n\nI can help you with prices! What drink or food would you like to know the price of?"

        else:
            return "أعتذر، أحتاج لفهمك بشكل أفضل. هل يمكنك إعادة صياغة طلبك؟ 🤔\n\nSorry, I need to understand you better. Can you rephrase your request?"

    def show_full_menu(self) -> str:
        """Show the complete menu"""
        menu_text = "🍽️ قائمة مقهى هيف / Hef Cafe Menu\n\n"

        for category_id, category in self.menu_data.items():
            menu_text += f"📂 {category['name_ar']} / {category['name_en']}\n"
            for item in category['items']:
                menu_text += f"   • {item['name_ar']} / {item['name_en']} - {item['price']} IQD\n"
            menu_text += "\n"

        menu_text += "💬 احكيلي شنو تريد تطلب! / Tell me what you'd like to order!"
        return menu_text

    def create_ai_response(self, text: str, phone_number: str, session: Dict) -> Dict[str, Any]:
        """Create AI response with metadata"""
        return {
            'type': 'text',
            'content': text,
            'timestamp': datetime.datetime.now().isoformat(),
            'session_data': session.get('current_order', {}) if session else {}
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

            logger.info(f"📤 Sending AI message to {phone_number}")

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                logger.info(f"✅ AI message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send AI message: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp message: {str(e)}")
            return False


# For backward compatibility - create alias
WhatsAppWorkflow = AIWhatsAppWorkflow