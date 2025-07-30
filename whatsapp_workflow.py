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

        # Menu data
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
                    "I only handle text messages. Please send a text message to start ordering!")

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")
            return self.create_response("Sorry, something went wrong. Please try again.")

    def get_message_type(self, message_data: Dict[str, Any]) -> str:
        """Determine the type of incoming message"""
        if 'text' in message_data:
            return 'text'
        return 'unknown'

    def handle_text_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process text messages following EXACT prompt structure"""
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
            current_step = session['step']

            logger.info(f"📊 Current step: {current_step}")

            # Follow EXACT step-by-step process from your prompt
            if current_step == 'waiting_for_language':
                return self.handle_language_selection(session, text, customer_name)

            elif current_step == 'waiting_for_category':
                return self.handle_category_selection(session, text)

            elif current_step == 'waiting_for_item':
                return self.handle_item_selection(session, text)

            elif current_step == 'waiting_for_quantity':
                return self.handle_quantity_selection(session, text)

            elif current_step == 'waiting_for_additional':
                return self.handle_additional_items(session, text)

            elif current_step == 'waiting_for_cart_review':
                return self.handle_cart_review(session, text)

            elif current_step == 'waiting_for_upsell':
                return self.handle_upsell(session, text)

            elif current_step == 'waiting_for_customization':
                return self.handle_customization(session, text)

            elif current_step == 'waiting_for_service_type':
                return self.handle_service_type(session, text)

            elif current_step == 'waiting_for_location':
                return self.handle_location(session, text)

            elif current_step == 'waiting_for_confirmation':
                return self.handle_order_confirmation(session, text)

            elif current_step == 'waiting_for_payment':
                return self.handle_payment(session, text)

            else:
                # Reset to start
                session['step'] = 'waiting_for_language'
                return self.handle_language_selection(session, text, customer_name)

        except Exception as e:
            logger.error(f"❌ Error processing text: {str(e)}")
            return self.create_response("Sorry, I couldn't process your message. Please try again.")

    def handle_language_selection(self, session, text, customer_name):
        """Step 1: Language Selection - EXACTLY as in your prompt"""
        if text in ['1', 'العربية', 'Arabic']:
            session['language'] = 'arabic'
            session['step'] = 'waiting_for_category'
            return self.create_response("""ماذا تريد أن تطلب؟ يرجى اختيار فئة عن طريق الرد برقم:

1: المشروبات الحارة
2: المشروبات الباردة
3: الحلويات
4: ايس تي
5: فرابتشينو
6: العصائر الطبيعية
7: موهيتو
8: ميلك شيك
9: توست
10: السندويشات
11: قطع الكيك
12: كرواسون
13: فطائر مالحة""")

        elif text in ['2', 'English']:
            session['language'] = 'english'
            session['step'] = 'waiting_for_category'
            return self.create_response("""What would you like to order? Please select a category by replying with the number:

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
13: Savory Pies""")

        else:
            # EXACTLY as in your prompt
            return self.create_response(
                f"Welcome to Hef Cafe!\n\nPlease select your preferred language:\n1: العربية (Arabic)\n2: English")

    def handle_category_selection(self, session, text):
        """Step 2: Category Selection"""
        try:
            category_num = int(text)
            if 1 <= category_num <= 13:
                session['current_category'] = category_num
                session['step'] = 'waiting_for_item'

                # Only show items if we have them in menu
                if category_num in self.menu_data:
                    return self.show_category_items(session, category_num)
                else:
                    return self.create_response(
                        "Sorry, this category is not available yet. Please select another category (1-13).")
            else:
                return self.create_response("Please select a valid category number (1-13).")
        except:
            return self.create_response("Please enter a valid number (1-13).")

    def show_category_items(self, session, category_num):
        """Display items from selected category"""
        category = self.menu_data[category_num]
        items = category['items']

        if session['language'] == 'arabic':
            response = f"إليك خيارات {category['name_ar']}:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}: {item['name_ar']} – {item['price']} دينار عراقي\n"
            response += "\nيرجى الرد برقم العنصر لاختياره."
        else:
            response = f"Here are our {category['name_en']} options:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}: {item['name_en']} – {item['price']} IQD\n"
            response += "\nPlease reply with the item number to make your selection."

        return self.create_response(response)

    def handle_item_selection(self, session, text):
        """Step 3: Item Selection"""
        try:
            item_num = int(text)
            category = self.menu_data[session['current_category']]
            items = category['items']

            if 1 <= item_num <= len(items):
                session['current_item'] = items[item_num - 1]
                session['step'] = 'waiting_for_quantity'

                # Ask for quantity with correct unit
                item = session['current_item']
                unit = item['unit']

                if session['language'] == 'arabic':
                    if unit == 'cups':
                        question = "كم عدد الأكواب التي ترغب بطلبها؟"
                    elif unit == 'slices':
                        question = "كم شريحة كيك ترغب بطلبها؟"
                    else:
                        question = "كم قطعة ترغب بطلبها؟"
                else:
                    if unit == 'cups':
                        question = "How many cups would you like to order?"
                    elif unit == 'slices':
                        question = "How many slices would you like to order?"
                    else:
                        question = "How many pieces would you like to order?"

                return self.create_response(question)
            else:
                return self.create_response(f"Please select a valid item number (1-{len(items)}).")
        except:
            return self.create_response("Please enter a valid item number.")

    def handle_quantity_selection(self, session, text):
        """Step 4: Quantity Selection"""
        try:
            quantity = int(text)
            if quantity > 0:
                item = session['current_item']
                cart_item = {
                    'item': item,
                    'quantity': quantity,
                    'subtotal': item['price'] * quantity
                }
                session['cart'].append(cart_item)
                session['step'] = 'waiting_for_additional'

                if session['language'] == 'arabic':
                    return self.create_response("""هل تريد إضافة المزيد من العناصر من فئة أخرى؟
1: نعم (العودة لاختيار الفئة)
2: لا (متابعة مراجعة السلة)""")
                else:
                    return self.create_response("""Would you like to add more items from another category?
1: Yes (Return to category selection)
2: No (Proceed to cart review)""")
            else:
                return self.create_response("Please enter a valid quantity (greater than 0).")
        except:
            return self.create_response("Please enter a valid number.")

    def handle_additional_items(self, session, text):
        """Step 5: Additional Items"""
        if text == '1':
            session['step'] = 'waiting_for_category'
            if session['language'] == 'arabic':
                return self.create_response("""اختر فئة أخرى:

1: المشروبات الحارة
2: المشروبات الباردة
3: الحلويات
4: ايس تي
5: فرابتشينو
6: العصائر الطبيعية
7: موهيتو
8: ميلك شيك
9: توست
10: السندويشات
11: قطع الكيك
12: كرواسون
13: فطائر مالحة""")
            else:
                return self.create_response("""Select another category:

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
13: Savory Pies""")
        elif text == '2':
            session['step'] = 'waiting_for_cart_review'
            return self.show_cart_review(session)
        else:
            if session['language'] == 'arabic':
                return self.create_response("يرجى اختيار 1 أو 2.")
            else:
                return self.create_response("Please select 1 or 2.")

    def show_cart_review(self, session):
        """Step 6: Cart Review"""
        cart = session['cart']
        total = sum(item['subtotal'] for item in cart)
        session['total'] = total

        if session['language'] == 'arabic':
            response = "ملخص الطلب:\n\n"
            for item in cart:
                response += f"• {item['item']['name_ar']} x{item['quantity']} - {item['subtotal']} دينار\n"
            response += f"\nالمجموع: {total} دينار عراقي\n\n"
            response += "هل تريد مراجعة وتعديل سلتك؟\n1: نعم (السماح بالتعديلات)\n2: لا (متابعة للتخصيص)"
        else:
            response = "Order Summary:\n\n"
            for item in cart:
                response += f"• {item['item']['name_en']} x{item['quantity']} - {item['subtotal']} IQD\n"
            response += f"\nTotal: {total} IQD\n\n"
            response += "Would you like to review and modify your cart?\n1: Yes (Allow modifications)\n2: No (Continue to customization)"

        return self.create_response(response)

    def handle_cart_review(self, session, text):
        """Step 6: Handle Cart Review Response"""
        if text == '1':
            if session['language'] == 'arabic':
                return self.create_response("ميزة التعديل ستكون متاحة قريباً. متابعة للخطوة التالية...")
            else:
                return self.create_response("Modification feature coming soon. Continuing to next step...")
        elif text == '2':
            session['step'] = 'waiting_for_upsell'
            return self.handle_upsell_offer(session)
        else:
            if session['language'] == 'arabic':
                return self.create_response("يرجى اختيار 1 أو 2.")
            else:
                return self.create_response("Please select 1 or 2.")

    def handle_upsell_offer(self, session):
        """Step 7: Upsell Offer"""
        session['step'] = 'waiting_for_customization'
        if session['language'] == 'arabic':
            return self.create_response("لا توجد عروض إضافية متاحة في هذا الوقت.\n\nهل تريد تخصيص طلبك؟\n1: نعم\n2: لا")
        else:
            return self.create_response(
                "No additional offers available at this time.\n\nWould you like to customize your order?\n1: Yes\n2: No")

    def handle_upsell(self, session, text):
        """Handle upsell response - go directly to customization"""
        return self.handle_customization(session, text)

    def handle_customization(self, session, text):
        """Step 8: Customization"""
        if text == '1':
            if session['language'] == 'arabic':
                response = "يرجى تحديد مستوى السكر (إذا كان قابلاً للتطبيق):\n1: بدون سكر\n2: سكر قليل\n3: سكر عادي\n4: سكر زيادة"
            else:
                response = "Please specify sugar level (if applicable):\n1: No sugar\n2: Light sugar\n3: Normal sugar\n4: Extra sugar"

            session['customization'] = text
            session['step'] = 'waiting_for_service_type'
            # For simplicity, go directly to service type
            return self.ask_service_type(session)
        elif text == '2':
            if session['language'] == 'arabic':
                session['customization'] = "لا توجد تخصيصات"
                response = "لا توجد تخصيصات متاحة لهذا العنصر. الانتقال للخطوة التالية."
            else:
                session['customization'] = "No customizations"
                response = "No customization available for this item. Moving to the next step."

            session['step'] = 'waiting_for_service_type'
            return self.create_response(response + "\n\n" + self.ask_service_type(session)['content'])
        else:
            if session['language'] == 'arabic':
                return self.create_response("يرجى اختيار 1 أو 2.")
            else:
                return self.create_response("Please select 1 or 2.")

    def ask_service_type(self, session):
        """Ask for service type"""
        if session['language'] == 'arabic':
            return self.create_response("هل تريد طلبك للتناول في المطعم أم للتوصيل؟\n1: تناول في المطعم\n2: توصيل")
        else:
            return self.create_response("Do you want your order for dine-in or delivery?\n1: Dine-in\n2: Delivery")

    def handle_service_type(self, session, text):
        """Step 9: Service Type"""
        if text == '1':
            session['service_type'] = 'dine-in'
            session['step'] = 'waiting_for_location'
            if session['language'] == 'arabic':
                return self.create_response("يرجى تقديم رقم طاولتك (1-7) لإكمال طلبك.")
            else:
                return self.create_response("Please provide your table number (1-7) to complete your order.")
        elif text == '2':
            session['service_type'] = 'delivery'
            session['step'] = 'waiting_for_location'
            if session['language'] == 'arabic':
                return self.create_response("يرجى مشاركة موقعك عبر واتساب، وأخبرنا إذا كان لديك تعليمات توصيل خاصة.")
            else:
                return self.create_response(
                    "Please share your location via WhatsApp, and let us know if you have special delivery instructions.")
        else:
            if session['language'] == 'arabic':
                return self.create_response("يرجى اختيار 1 أو 2.")
            else:
                return self.create_response("Please select 1 or 2.")

    def handle_location(self, session, text):
        """Step 10: Location Collection"""
        session['location'] = text
        session['step'] = 'waiting_for_confirmation'

        # Show order confirmation
        cart = session['cart']
        total = session['total']
        service = session['service_type']
        location = session['location']

        if session['language'] == 'arabic':
            response = f"""إليك ملخص طلبك:

العناصر:
"""
            for item in cart:
                response += f"• {item['item']['name_ar']} x{item['quantity']}\n"

            response += f"""
التخصيصات: {session.get('customization', 'لا توجد')}
الخدمة: {service}
الموقع: {location}
السعر الإجمالي: {total} دينار عراقي

هل تريد تأكيد هذا الطلب؟
1: نعم
2: لا (إعادة البدء)"""
        else:
            response = f"""Here is your order summary:

Items:
"""
            for item in cart:
                response += f"• {item['item']['name_en']} x{item['quantity']}\n"

            response += f"""
Customizations: {session.get('customization', 'None')}
Service: {service}
Location: {location}
Total Price: {total} IQD

Would you like to confirm this order?
1: Yes
2: No (Restart)"""

        return self.create_response(response)

    def handle_order_confirmation(self, session, text):
        """Step 11: Order Confirmation"""
        if text == '1':
            session['step'] = 'waiting_for_payment'
            total = session['total']

            if session['language'] == 'arabic':
                return self.create_response(f"إجماليك هو {total} دينار عراقي. يرجى دفع هذا المبلغ للكاشير في المنضدة.")
            else:
                return self.create_response(
                    f"Your total is {total} IQD. Please pay this amount to the cashier at the counter.")
        elif text == '2':
            # Restart
            session.clear()
            session['step'] = 'waiting_for_language'
            return self.create_response(
                "Welcome to Hef Cafe!\n\nPlease select your preferred language:\n1: العربية (Arabic)\n2: English")
        else:
            if session['language'] == 'arabic':
                return self.create_response("يرجى اختيار 1 أو 2.")
            else:
                return self.create_response("Please select 1 or 2.")

    def handle_payment(self, session, text):
        """Step 12: Final Confirmation"""
        import random
        order_id = f"HEF{random.randint(1000, 9999)}"
        cart = session['cart']
        total = session['total']
        location = session['location']

        if session['language'] == 'arabic':
            response = f"""شكراً لك! تم تقديم طلبك بنجاح. سنقوم بإشعارك عندما يكون جاهزاً.

تفاصيل الطلب:
رقم الطلب: {order_id}
الموقع: {location}
السعر الإجمالي: {total} دينار عراقي

العناصر:
"""
            for item in cart:
                response += f"• {item['item']['name_ar']} x{item['quantity']}\n"
        else:
            response = f"""Thank you! Your order has been placed successfully. We'll notify you once it's ready.

Order Details:
Order ID: {order_id}
Location: {location}
Total Price: {total} IQD

Items:
"""
            for item in cart:
                response += f"• {item['item']['name_en']} x{item['quantity']}\n"

        # Reset session
        session.clear()
        session['step'] = 'waiting_for_language'

        return self.create_response(response)

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