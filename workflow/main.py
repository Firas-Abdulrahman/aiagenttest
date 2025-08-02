# workflow/main.py - UPDATED WITH MENU AWARENESS
import logging
from typing import Dict, Any
from config.settings import WhatsAppConfig
from database.manager import DatabaseManager
from ai.processor import AIProcessor
from workflow.handlers import MessageHandler
from workflow.actions import ActionExecutor
from whatsapp.client import WhatsAppClient

logger = logging.getLogger(__name__)


class WhatsAppWorkflow:
    """Main workflow orchestrator for WhatsApp bot with Menu Awareness"""

    def __init__(self, config: Dict[str, str]):
        """Initialize the complete workflow system with menu intelligence"""
        self.config = config

        # Initialize core components
        self._init_components()

        logger.info("✅ WhatsApp workflow with menu awareness initialized successfully")

    def _init_components(self):
        """UPDATED: Initialize all workflow components with menu awareness"""
        try:
            # Database manager
            self.db = DatabaseManager(self.config.get('db_path', 'hef_cafe.db'))
            logger.info("✅ Database manager initialized")

            # AI processor with database reference for menu awareness
            ai_config = {
                'ai_quota_cache_duration': self.config.get('ai_quota_cache_duration', 300),
                'ai_disable_on_quota': self.config.get('ai_disable_on_quota', True)
            }
            self.ai = AIProcessor(self.config.get('openai_api_key'), ai_config, self.db)  # UPDATED: Added self.db
            logger.info("✅ AI processor with menu awareness initialized")

            # WhatsApp client
            self.whatsapp = WhatsAppClient(self.config)
            logger.info("✅ WhatsApp client initialized")

            # Action executor
            self.executor = ActionExecutor(self.db)
            logger.info("✅ Action executor initialized")

            # Message handler
            self.handler = MessageHandler(self.db, self.ai, self.executor)
            logger.info("✅ Message handler initialized")

        except Exception as e:
            logger.error(f"❌ Error initializing components: {str(e)}")
            raise

    def handle_whatsapp_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for handling WhatsApp messages with menu intelligence"""
        try:
            logger.info("📨 Processing incoming WhatsApp message with menu awareness")

            # Handle the message through the enhanced workflow
            response = self.handler.handle_message(message_data)

            logger.info("✅ Message processed successfully with menu intelligence")
            return response

        except Exception as e:
            logger.error(f"❌ Error handling WhatsApp message: {str(e)}")
            return {
                'type': 'text',
                'content': 'حدث خطأ. الرجاء إعادة المحاولة\nAn error occurred. Please try again',
                'timestamp': __import__('datetime').datetime.now().isoformat()
            }

    def send_whatsapp_message(self, phone_number: str, response_data: Dict[str, Any]) -> bool:
        """Send response back to WhatsApp"""
        try:
            logger.info(f"📤 Sending response to {phone_number}")
            return self.whatsapp.send_response(phone_number, response_data)

        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp message: {str(e)}")
            return False

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str:
        """Verify webhook for WhatsApp"""
        return self.whatsapp.verify_webhook(mode, token, challenge)

    def validate_webhook_payload(self, payload: Dict) -> bool:
        """Validate incoming webhook payload"""
        return self.whatsapp.validate_webhook_payload(payload)

    def extract_messages_from_webhook(self, payload: Dict) -> list:
        """Extract messages from webhook payload"""
        return self.whatsapp.get_webhook_data(payload)

    # Database operations
    def get_user_session(self, phone_number: str) -> Dict:
        """Get user session information"""
        return self.db.get_user_session(phone_number)

    def get_user_order(self, phone_number: str) -> Dict:
        """Get user's current order"""
        return self.db.get_user_order(phone_number)

    def get_order_history(self, phone_number: str = None, limit: int = 50) -> list:
        """Get order history"""
        return self.db.get_order_history(phone_number, limit)

    def get_popular_items(self, limit: int = 10) -> list:
        """Get most popular menu items"""
        return self.db.get_popular_items(limit)

    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        return self.db.get_database_stats()

    def cleanup_old_sessions(self, days_old: int = 7) -> int:
        """Clean up old user sessions"""
        return self.db.cleanup_old_sessions(days_old)

    # Menu operations
    def get_available_categories(self) -> list:
        """Get all available menu categories"""
        return self.db.get_available_categories()

    def get_main_categories(self) -> list:
        """Get main menu categories"""
        return self.db.get_main_categories()

    def get_sub_categories(self, main_category_id: int) -> list:
        """Get sub-categories for main category"""
        return self.db.get_sub_categories(main_category_id)

    def get_category_items(self, category_id: int) -> list:
        """Get items for specific category"""
        return self.db.get_category_items(category_id)

    def get_sub_category_items(self, sub_category_id: int) -> list:
        """Get items for specific sub-category"""
        return self.db.get_sub_category_items(sub_category_id)

    def get_item_by_id(self, item_id: int) -> Dict:
        """Get specific menu item by ID"""
        return self.db.get_item_by_id(item_id)

    # AI operations with menu awareness
    def is_ai_available(self) -> bool:
        """Check if AI processing is available"""
        return self.ai.is_available()

    def test_ai_connection(self) -> Dict:
        """Test AI connection and capabilities including menu awareness"""
        if not self.ai.is_available():
            return {'status': 'unavailable', 'message': 'AI not configured'}

        try:
            # Test basic AI functionality
            test_result = self.ai.understand_message(
                "Hello",
                "waiting_for_language",
                {'current_step': 'waiting_for_language'}
            )

            # Test menu awareness if available
            menu_aware_test = None
            if hasattr(self.ai, 'understand_message_with_menu_awareness') and self.ai.database_manager:
                menu_aware_test = self.ai.understand_message_with_menu_awareness(
                    "I want something cold and sweet",
                    "waiting_for_category",
                    {'current_step': 'waiting_for_category', 'language': 'english'}
                )

            if test_result or menu_aware_test:
                return {
                    'status': 'available',
                    'message': 'AI working correctly',
                    'menu_awareness': bool(menu_aware_test),
                    'features': {
                        'basic_ai': bool(test_result),
                        'menu_intelligence': bool(menu_aware_test),
                        'natural_language': bool(menu_aware_test)
                    }
                }
            else:
                return {'status': 'error', 'message': 'AI not responding properly'}

        except Exception as e:
            return {'status': 'error', 'message': f'AI test failed: {str(e)}'}

    def test_menu_intelligence(self, test_message: str, language: str = 'arabic') -> Dict:
        """Test menu intelligence with a specific message"""
        try:
            if not hasattr(self.ai, 'understand_message_with_menu_awareness'):
                return {'status': 'unavailable', 'message': 'Menu intelligence not available'}

            context = {
                'current_step': 'waiting_for_category',
                'language': language,
                'available_categories': self.get_main_categories()
            }

            result = self.ai.understand_message_with_menu_awareness(
                test_message, 'waiting_for_category', context
            )

            if result:
                return {
                    'status': 'success',
                    'test_message': test_message,
                    'ai_understanding': result.get('understood_intent', ''),
                    'suggested_category': result.get('extracted_data', {}).get('suggested_main_category'),
                    'suggested_sub_category': result.get('extracted_data', {}).get('suggested_sub_category'),
                    'confidence': result.get('confidence', 'unknown'),
                    'response': result.get('response_message', '')
                }
            else:
                return {'status': 'no_result', 'message': 'No AI result generated'}

        except Exception as e:
            return {'status': 'error', 'message': f'Menu intelligence test failed: {str(e)}'}

    # WhatsApp operations
    def get_phone_numbers(self) -> list:
        """Get all phone numbers associated with the account"""
        return self.whatsapp.get_phone_numbers() or []

    def get_business_profile(self) -> Dict:
        """Get business profile information"""
        return self.whatsapp.get_business_profile() or {}

    def send_template_message(self, to: str, template_name: str, language_code: str = 'en',
                              parameters: list = None) -> bool:
        """Send a template message"""
        return self.whatsapp.send_template_message(to, template_name, language_code, parameters)

    # Health and monitoring
    def health_check(self) -> Dict:
        """Perform comprehensive health check including menu intelligence"""
        health_status = {
            'status': 'healthy',
            'components': {},
            'menu_intelligence': {},
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

        # Database health
        try:
            stats = self.db.get_database_stats()
            health_status['components']['database'] = {
                'status': 'healthy',
                'stats': stats
            }
        except Exception as e:
            health_status['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'

        # AI health with menu intelligence
        ai_test = self.test_ai_connection()
        health_status['components']['ai'] = ai_test
        if ai_test['status'] == 'error':
            health_status['status'] = 'degraded'

        # Menu intelligence specific health
        try:
            if hasattr(self.ai, 'database_manager') and self.ai.database_manager:
                # Test menu intelligence
                menu_test = self.test_menu_intelligence("I want something cold", "english")
                health_status['menu_intelligence'] = {
                    'status': 'active' if menu_test['status'] == 'success' else 'inactive',
                    'test_result': menu_test,
                    'total_main_categories': len(self.get_main_categories()),
                    'total_items': len(self.db.menu_knowledge.get('items', {})) if hasattr(self.db, 'menu_knowledge') else 'unknown'
                }
            else:
                health_status['menu_intelligence'] = {
                    'status': 'not_configured',
                    'message': 'Database not connected to AI processor'
                }
        except Exception as e:
            health_status['menu_intelligence'] = {
                'status': 'error',
                'error': str(e)
            }

        # WhatsApp API health
        try:
            phone_numbers = self.get_phone_numbers()
            health_status['components']['whatsapp'] = {
                'status': 'healthy',
                'phone_numbers_count': len(phone_numbers) if phone_numbers else 0
            }
        except Exception as e:
            health_status['components']['whatsapp'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'

        return health_status

    # Analytics and reporting
    def get_analytics_summary(self, days: int = 7) -> Dict:
        """Get analytics summary for specified days including menu intelligence metrics"""
        try:
            # Get basic stats
            stats = self.db.get_database_stats()

            # Calculate additional metrics
            analytics = {
                'period_days': days,
                'total_users': stats.get('active_users', 0),
                'total_orders': stats.get('completed_orders_count', 0),
                'total_revenue': stats.get('total_revenue', 0),
                'popular_items': self.get_popular_items(5),
                'ai_features': {
                    'ai_availability': self.is_ai_available(),
                    'menu_intelligence': hasattr(self.ai, 'understand_message_with_menu_awareness'),
                    'natural_language_support': bool(self.ai.database_manager)
                },
                'menu_coverage': {
                    'main_categories': len(self.get_main_categories()),
                    'total_sub_categories': sum(len(self.get_sub_categories(cat['id'])) for cat in self.get_main_categories()),
                    'total_items': sum(len(self.get_sub_category_items(sub_cat['id']))
                                     for main_cat in self.get_main_categories()
                                     for sub_cat in self.get_sub_categories(main_cat['id']))
                },
                'generated_at': __import__('datetime').datetime.now().isoformat()
            }

            return analytics

        except Exception as e:
            logger.error(f"❌ Error generating analytics: {str(e)}")
            return {'error': str(e)}

    # Configuration and setup
    def get_configuration_status(self) -> Dict:
        """Get current configuration status including menu intelligence"""
        return {
            'whatsapp_configured': bool(self.config.get('whatsapp_token')),
            'phone_number_configured': bool(self.config.get('phone_number_id')),
            'ai_configured': bool(self.config.get('openai_api_key')),
            'ai_available': self.is_ai_available(),
            'menu_intelligence_enabled': hasattr(self.ai, 'understand_message_with_menu_awareness'),
            'database_connected_to_ai': bool(getattr(self.ai, 'database_manager', None)),
            'database_path': self.config.get('db_path', 'hef_cafe.db'),
            'components_initialized': True,
            'features': {
                'natural_language_understanding': bool(getattr(self.ai, 'database_manager', None)),
                'intelligent_menu_suggestions': hasattr(self.ai, 'understand_message_with_menu_awareness'),
                'multi_language_support': True,
                'session_management': True
            }
        }

    # Utility methods
    def restart_session(self, phone_number: str) -> bool:
        """Restart user session (clear all data)"""
        try:
            return self.db.delete_session(phone_number)
        except Exception as e:
            logger.error(f"❌ Error restarting session: {str(e)}")
            return False

    def export_user_data(self, phone_number: str) -> Dict:
        """Export all user data"""
        try:
            return {
                'session': self.get_user_session(phone_number),
                'current_order': self.get_user_order(phone_number),
                'order_history': self.get_order_history(phone_number),
                'conversation_history': self.db.get_conversation_history(phone_number)
            }
        except Exception as e:
            logger.error(f"❌ Error exporting user data: {str(e)}")
            return {'error': str(e)}

    def simulate_message(self, phone_number: str, message_text: str, customer_name: str = "Test User") -> Dict:
        """Simulate a message for testing purposes including menu intelligence"""
        try:
            # Create mock message data
            mock_message = {
                'from': phone_number,
                'text': {'body': message_text},
                'contacts': [{'profile': {'name': customer_name}}],
                'id': f"test_{__import__('time').time()}"
            }

            # Process through workflow
            return self.handle_whatsapp_message(mock_message)

        except Exception as e:
            logger.error(f"❌ Error simulating message: {str(e)}")
            return {'error': str(e)}

    def test_natural_language_understanding(self, test_cases: list = None) -> Dict:
        """Test natural language understanding with predefined or custom test cases"""
        if not test_cases:
            test_cases = [
                {"message": "I want something cold and sweet", "language": "english"},
                {"message": "اريد شي بارد ومنعش", "language": "arabic"},
                {"message": "I need energy", "language": "english"},
                {"message": "بدي شي حلو اكله", "language": "arabic"},
                {"message": "Something to wake me up", "language": "english"}
            ]

        results = []
        for test_case in test_cases:
            result = self.test_menu_intelligence(test_case["message"], test_case["language"])
            results.append({
                'input': test_case,
                'result': result,
                'success': result.get('status') == 'success'
            })

        success_rate = sum(1 for r in results if r['success']) / len(results) if results else 0

        return {
            'total_tests': len(results),
            'successful': sum(1 for r in results if r['success']),
            'success_rate': round(success_rate * 100, 1),
            'results': results,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }


# For backward compatibility
TrueAIWorkflow = WhatsAppWorkflow