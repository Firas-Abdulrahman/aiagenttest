import os
import json
import logging
import time
from flask import Flask, request, jsonify
from config.settings import WhatsAppConfig
from workflow.main import WhatsAppWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to prevent message spam and infinite loops"""

    def __init__(self, max_messages_per_minute: int = 15, max_messages_per_hour: int = 200):
        self.max_per_minute = max_messages_per_minute
        self.max_per_hour = max_messages_per_hour

        # Track messages per user
        from collections import defaultdict, deque
        self.user_messages = defaultdict(lambda: {
            'minute': deque(),
            'hour': deque()
        })

        # Track last message time per user
        self.last_message_time = {}

        # Minimum time between messages (prevent rapid fire)
        self.min_interval = 2  # 2 seconds

    def is_allowed(self, phone_number: str) -> tuple:
        """Check if user is allowed to send a message"""
        current_time = time.time()

        # Check minimum interval between messages
        if phone_number in self.last_message_time:
            time_since_last = current_time - self.last_message_time[phone_number]
            if time_since_last < self.min_interval:
                return False, f"Please wait {self.min_interval - int(time_since_last)} seconds before sending another message"

        # Clean old entries
        self._cleanup_old_entries(phone_number, current_time)

        user_data = self.user_messages[phone_number]

        # Check per-minute limit
        if len(user_data['minute']) >= self.max_per_minute:
            return False, f"Rate limit exceeded: maximum {self.max_per_minute} messages per minute"

        # Check per-hour limit
        if len(user_data['hour']) >= self.max_per_hour:
            return False, f"Rate limit exceeded: maximum {self.max_per_hour} messages per hour"

        # Record this message
        user_data['minute'].append(current_time)
        user_data['hour'].append(current_time)
        self.last_message_time[phone_number] = current_time

        return True, None

    def _cleanup_old_entries(self, phone_number: str, current_time: float):
        """Remove old entries outside the time windows"""
        user_data = self.user_messages[phone_number]

        # Remove entries older than 1 minute
        minute_cutoff = current_time - 60
        while user_data['minute'] and user_data['minute'][0] < minute_cutoff:
            user_data['minute'].popleft()

        # Remove entries older than 1 hour
        hour_cutoff = current_time - 3600
        while user_data['hour'] and user_data['hour'][0] < hour_cutoff:
            user_data['hour'].popleft()

    def get_user_stats(self, phone_number: str) -> dict:
        """Get current rate limit stats for a user"""
        current_time = time.time()
        self._cleanup_old_entries(phone_number, current_time)

        user_data = self.user_messages[phone_number]

        return {
            'messages_this_minute': len(user_data['minute']),
            'messages_this_hour': len(user_data['hour']),
            'max_per_minute': self.max_per_minute,
            'max_per_hour': self.max_per_hour,
            'last_message': self.last_message_time.get(phone_number, 0)
        }

    def reset_user_limits(self, phone_number: str):
        """Reset rate limits for a specific user (admin function)"""
        if phone_number in self.user_messages:
            del self.user_messages[phone_number]
        if phone_number in self.last_message_time:
            del self.last_message_time[phone_number]

        logger.info(f"🔄 Rate limits reset for {phone_number}")

    def cleanup_old_users(self):
        """Clean up data for users who haven't sent messages recently"""
        current_time = time.time()
        cutoff_time = current_time - 86400  # 24 hours

        users_to_remove = []

        for phone_number, last_time in self.last_message_time.items():
            if last_time < cutoff_time:
                users_to_remove.append(phone_number)

        for phone_number in users_to_remove:
            if phone_number in self.user_messages:
                del self.user_messages[phone_number]
            if phone_number in self.last_message_time:
                del self.last_message_time[phone_number]

        if users_to_remove:
            logger.info(f"🧹 Cleaned up rate limit data for {len(users_to_remove)} inactive users")


def create_flask_app():
    """Create and configure Flask app with enhanced protection"""
    app = Flask(__name__)

    # Initialize configuration
    config_manager = WhatsAppConfig()

    # Validate configuration
    if not config_manager.validate_config():
        logger.error("❌ Configuration validation failed.")
        return None

    # Get configuration dictionary
    config = config_manager.get_config_dict()

    # Initialize workflow
    try:
        workflow = WhatsAppWorkflow(config)
        logger.info("✅ WhatsApp workflow initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize workflow: {str(e)}")
        return None

    # Initialize rate limiter
    rate_limiter = RateLimiter(
        max_messages_per_minute=15,  # Increased slightly for normal usage
        max_messages_per_hour=200  # Reasonable daily limit
    )

    @app.route('/')
    def home():
        """Enhanced home page with comprehensive information"""
        health = workflow.health_check()
        stats = workflow.get_database_stats()

        return f'''
        <html>
        <head>
            <title>Hef Cafe WhatsApp Bot - Enhanced</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #8B4513; }}
                .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
                .warning {{ background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }}
                .info {{ background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
                a {{ color: #8B4513; text-decoration: none; font-weight: bold; }}
                a:hover {{ text-decoration: underline; }}
                .endpoint {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #8B4513; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
                .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #8B4513; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>☕ Hef Cafe WhatsApp Bot - Enhanced</h1>

                <div class="status {'success' if health['status'] == 'healthy' else 'warning'}">
                    {'✅ System Status: Healthy' if health['status'] == 'healthy' else '⚠️ System Status: ' + health['status'].title()}
                </div>

                <div class="status success">
                    🛡️ Enhanced Protection: Rate Limiting, Session Isolation, Message Deduplication
                </div>

                <div class="status info">
                    📱 Phone Number: {config.get('phone_number_id', 'Not configured')}
                </div>

                <h2>📊 System Statistics:</h2>
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{stats.get('active_users', 0)}</div>
                        <div>Active Users</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{stats.get('completed_orders_count', 0)}</div>
                        <div>Total Orders</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{stats.get('total_revenue', 0):,}</div>
                        <div>Revenue (IQD)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{stats.get('menu_items_count', 0)}</div>
                        <div>Menu Items</div>
                    </div>
                </div>

                <h2>🛡️ Enhanced Security Features:</h2>
                <div class="status success">
                    ✅ Message Deduplication - Prevents duplicate processing<br>
                    ✅ Rate Limiting - 15 messages/minute, 200/hour per user<br>
                    ✅ Session Isolation - Thread-safe user sessions<br>
                    ✅ AI Loop Prevention - Max 1 AI attempt per message<br>
                    ✅ Processing Locks - Prevents concurrent message processing
                </div>

                <h2>🔧 API Endpoints:</h2>

                <div class="endpoint">
                    <strong>📊 <a href="/health">Health Check</a></strong><br>
                    Comprehensive system health monitoring with rate limiter stats
                </div>

                <div class="endpoint">
                    <strong>📈 <a href="/analytics">Analytics Dashboard</a></strong><br>
                    Business intelligence and reporting
                </div>

                <div class="endpoint">
                    <strong>🧪 <a href="/test-credentials">Test Credentials</a></strong><br>
                    Validate WhatsApp API connectivity
                </div>

                <div class="endpoint">
                    <strong>📱 <a href="/phone-numbers">Phone Numbers</a></strong><br>
                    Manage WhatsApp Business numbers
                </div>

                <div class="endpoint">
                    <strong>⚙️ <a href="/config">Configuration</a></strong><br>
                    System configuration overview
                </div>

                <div class="endpoint">
                    <strong>🔌 Webhook Endpoints</strong><br>
                    <code>POST /webhook</code> - Message processing<br>
                    <code>GET /webhook</code> - Webhook verification
                </div>

                <h2>🍽️ Bot Features:</h2>
                <div class="endpoint">
                    <strong>☕ AI-Powered Ordering</strong><br>
                    Advanced natural language understanding with GPT-4 integration
                </div>
                <div class="endpoint">
                    <strong>🌐 Bilingual Support</strong><br>
                    Seamless Arabic and English conversation handling
                </div>
                <div class="endpoint">
                    <strong>📱 Smart Session Management</strong><br>
                    Thread-safe contextual conversation flow with step validation
                </div>
                <div class="endpoint">
                    <strong>🗄️ Database Integration</strong><br>
                    Complete order history and analytics tracking
                </div>

                <h2>🍽️ Menu Categories:</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                    <div>1. المشروبات الباردة / Cold Drinks 🧊</div>
                    <div>2. المشروبات الحارة / Hot Drinks ☕</div>
                    <div>3. الحلويات والمعجنات / Pastries & Sweets 🍰</div>
                </div>

                <div class="status info" style="margin-top: 30px;">
                    <strong>System Version:</strong> 2.1.0 (Enhanced Security)<br>
                    <strong>Last Updated:</strong> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                    <strong>AI Status:</strong> {'✅ Active' if workflow.is_ai_available() else '❌ Unavailable'}<br>
                    <strong>Rate Limiter:</strong> ✅ Active (15/min, 200/hour)
                </div>

                <p style="text-align: center; color: #8B4513; font-weight: bold; margin-top: 30px;">
                    🎉 Enhanced Hef Cafe Digital Ordering System! 🎉
                </p>
            </div>
        </body>
        </html>
        '''

    @app.route('/webhook', methods=['GET'])
    def verify_webhook():
        """Verify webhook for WhatsApp (required by Meta)"""
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        logger.info(f"🔐 Webhook verification attempt: mode={mode}, token={token}")

        result = workflow.verify_webhook(mode, token, challenge)
        if result:
            return result
        else:
            return "Verification failed", 403

    @app.route('/webhook', methods=['POST'])
    def handle_webhook():
        """Handle incoming WhatsApp messages with enhanced protection"""
        try:
            data = request.get_json()

            if not data:
                logger.warning("⚠️ No data received in webhook")
                return jsonify({'status': 'error', 'message': 'No data received'}), 400

            logger.info(f"📨 Incoming webhook data received")

            # Validate payload
            if not workflow.validate_webhook_payload(data):
                logger.warning("⚠️ Invalid webhook payload")
                return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400

            # Extract messages
            messages = workflow.extract_messages_from_webhook(data)

            if not messages:
                logger.info("ℹ️ No messages to process (status update only)")
                return jsonify({'status': 'success', 'message': 'No messages to process'}), 200

            # Process each message with enhanced protection
            for message in messages:
                phone_number = message.get('from')
                message_id = message.get('id')

                if not phone_number or not message_id:
                    logger.warning("⚠️ Message missing phone number or ID")
                    continue

                logger.info(f"📱 Processing message {message_id} from {phone_number}")

                # Check rate limits
                allowed, rate_limit_message = rate_limiter.is_allowed(phone_number)
                if not allowed:
                    logger.warning(f"🚫 Rate limit exceeded for {phone_number}: {rate_limit_message}")

                    # Send rate limit message to user
                    rate_limit_response = {
                        'type': 'text',
                        'content': f"⚠️ {rate_limit_message}\n\nتم تجاوز الحد المسموح للرسائل. الرجاء الانتظار",
                        'timestamp': time.time()
                    }
                    workflow.send_whatsapp_message(phone_number, rate_limit_response)
                    continue

                try:
                    # Process message through workflow
                    response = workflow.handle_whatsapp_message(message)

                    # Send response back to WhatsApp
                    success = workflow.send_whatsapp_message(phone_number, response)

                    if success:
                        logger.info(f"✅ Response sent successfully to {phone_number}")
                    else:
                        logger.error(f"❌ Failed to send response to {phone_number}")

                except Exception as message_error:
                    logger.error(f"❌ Error processing message {message_id}: {message_error}")

                    # Send error message to user
                    error_response = {
                        'type': 'text',
                        'content': 'حدث خطأ مؤقت. الرجاء إعادة المحاولة\nTemporary error occurred. Please try again',
                        'timestamp': time.time()
                    }
                    try:
                        workflow.send_whatsapp_message(phone_number, error_response)
                    except:
                        pass  # Don't let error handling errors crash the system

            return jsonify({'status': 'success'}), 200

        except Exception as e:
            logger.error(f"❌ Error processing webhook: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """Comprehensive health check endpoint"""
        health = workflow.health_check()

        # Add rate limiter stats
        health['rate_limiter'] = {
            'status': 'active',
            'total_users_tracked': len(rate_limiter.user_messages),
            'limits': {
                'per_minute': rate_limiter.max_per_minute,
                'per_hour': rate_limiter.max_per_hour
            }
        }

        status_code = 200 if health['status'] == 'healthy' else 503
        return jsonify(health), status_code

    @app.route('/analytics', methods=['GET'])
    def analytics():
        """Analytics dashboard"""
        days = request.args.get('days', 7, type=int)
        analytics = workflow.get_analytics_summary(days)
        return jsonify(analytics), 200

    @app.route('/config', methods=['GET'])
    def show_config():
        """Show current configuration (sensitive data hidden)"""
        safe_config = config_manager.get_safe_config()
        config_status = workflow.get_configuration_status()

        return jsonify({
            'configuration': safe_config,
            'status': config_status,
            'features': {
                'text_messaging': True,
                'ai_processing': workflow.is_ai_available(),
                'database_storage': True,
                'webhook_handling': True,
                'analytics': True,
                'rate_limiting': True,
                'session_isolation': True,
                'message_deduplication': True
            }
        }), 200

    @app.route('/test-credentials', methods=['GET'])
    def test_credentials():
        """Test WhatsApp credentials and AI connection"""
        try:
            # Test WhatsApp API
            phone_numbers = workflow.get_phone_numbers()

            # Test AI
            ai_test = workflow.test_ai_connection()

            return jsonify({
                'status': 'success',
                'whatsapp': {
                    'status': 'working' if phone_numbers else 'error',
                    'phone_numbers': phone_numbers or []
                },
                'ai': ai_test,
                'test_time': __import__('datetime').datetime.now().isoformat()
            }), 200

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Credentials test failed: {str(e)}',
                'test_time': __import__('datetime').datetime.now().isoformat()
            }), 500

    @app.route('/phone-numbers', methods=['GET'])
    def list_phone_numbers():
        """List all phone numbers in the WhatsApp Business Account"""
        try:
            phone_numbers = workflow.get_phone_numbers()

            return jsonify({
                'status': 'success',
                'phone_numbers': phone_numbers,
                'total_count': len(phone_numbers) if phone_numbers else 0
            }), 200

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to fetch phone numbers: {str(e)}'
            }), 500

    @app.route('/rate-limit-stats/<phone_number>', methods=['GET'])
    def get_rate_limit_stats(phone_number):
        """Get rate limit statistics for a user"""
        try:
            stats = rate_limiter.get_user_stats(phone_number)
            return jsonify({
                'status': 'success',
                'phone_number': phone_number,
                'rate_limit_stats': stats
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/reset-rate-limit/<phone_number>', methods=['POST'])
    def reset_rate_limit(phone_number):
        """Reset rate limits for a user (admin function)"""
        try:
            rate_limiter.reset_user_limits(phone_number)
            return jsonify({
                'status': 'success',
                'message': f'Rate limits reset for {phone_number}'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/simulate', methods=['POST'])
    def simulate_message():
        """Simulate a message for testing purposes"""
        try:
            data = request.get_json()
            phone_number = data.get('phone_number', '1234567890')
            message = data.get('message', 'Hello')
            customer_name = data.get('customer_name', 'Test User')

            if not message:
                return jsonify({
                    'status': 'error',
                    'message': 'message is required'
                }), 400

            # Simulate the message
            response = workflow.simulate_message(phone_number, message, customer_name)

            return jsonify({
                'status': 'success',
                'simulation': {
                    'input': {'phone_number': phone_number, 'message': message},
                    'response': response
                }
            }), 200

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Simulation failed: {str(e)}'
            }), 500

    @app.route('/cleanup', methods=['POST'])
    def cleanup_sessions():
        """Clean up old user sessions and rate limit data"""
        try:
            days_old = request.json.get('days_old', 7) if request.json else 7

            # Clean up old sessions
            deleted_sessions = workflow.cleanup_old_sessions(days_old)

            # Clean up rate limiter data
            rate_limiter.cleanup_old_users()

            return jsonify({
                'status': 'success',
                'message': f'Cleaned up {deleted_sessions} old sessions and rate limit data',
                'deleted_sessions': deleted_sessions
            }), 200

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Cleanup failed: {str(e)}'
            }), 500

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'status': 'error',
            'message': 'Endpoint not found',
            'available_endpoints': [
                '/', '/webhook', '/health', '/analytics', '/config',
                '/test-credentials', '/phone-numbers', '/simulate', '/cleanup',
                '/rate-limit-stats/<phone_number>', '/reset-rate-limit/<phone_number>'
            ]
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(error)
        }), 500

    return app


def create_simple_test_app():
    """Create a simple app for testing when full app fails"""
    app = Flask(__name__)

    @app.route('/')
    def home():
        return '''
        <h1>WhatsApp Bot Debug Mode</h1>
        <p>Full app failed to initialize. Use these endpoints to debug:</p>
        <ul>
            <li><a href="/test-credentials">Test Credentials</a></li>
            <li><a href="/config">View Config</a></li>
            <li><a href="/debug-env">Debug Environment</a></li>
        </ul>
        '''

    @app.route('/test-credentials')
    def test_credentials():
        """Test credentials without starting full workflow"""
        config_manager = WhatsAppConfig()
        return jsonify({
            'credentials_loaded': {
                'whatsapp_token': bool(config_manager.whatsapp_token),
                'waba_id': bool(config_manager.waba_id),
                'app_id': bool(config_manager.app_id),
                'client_secret': bool(config_manager.client_secret),
            },
            'phone_number_id': config_manager.phone_number_id,
            'validation_passed': config_manager.validate_config()
        })

    @app.route('/config')
    def show_config():
        """Show current configuration"""
        config_manager = WhatsAppConfig()
        return jsonify(config_manager.get_safe_config())

    @app.route('/debug-env')
    def debug_env():
        """Debug environment variables"""
        env_vars = {}
        for key in ['WHATSAPP_TOKEN', 'WHATSAPP_BUSINESS_ACCOUNT_ID', 'APP_ID',
                    'CLIENT_SECRET', 'VERIFY_TOKEN', 'OPENAI_API_KEY', 'PHONE_NUMBER_ID']:
            value = os.getenv(key)
            if value and key in ['WHATSAPP_TOKEN', 'CLIENT_SECRET', 'OPENAI_API_KEY']:
                env_vars[key] = value[:10] + "..." if len(value) > 10 else value
            else:
                env_vars[key] = value or "NOT SET"

        return jsonify({
            'environment_variables': env_vars,
            'dotenv_file_exists': os.path.exists('.env')
        })

    return app


# Create the Flask app instance for WSGI servers
def create_app():
    """Create app instance for WSGI"""
    return create_flask_app() or create_simple_test_app()


# For Gunicorn (production)
app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Enhanced Hef Cafe WhatsApp Bot Server...")
    print(f"📅 Server time: {__import__('datetime').datetime.now()}")
    print("🛡️ Enhanced with: Rate Limiting, Session Isolation, Message Deduplication")

    # Try to create full app first
    flask_app = create_flask_app()

    if not flask_app:
        print("⚠️ Full app failed to initialize, starting debug app...")
        flask_app = create_simple_test_app()
        print("🔧 Debug app started - visit endpoints to troubleshoot")
    else:
        print("✅ Enhanced WhatsApp bot initialized successfully!")

    # Get port from environment (Render sets this)
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('ENVIRONMENT', 'development') == 'development'

    print(f"\n🌐 Server starting on port {port}")
    print(f"🔗 Webhook URL: https://your-app-name.onrender.com/webhook")
    print(f"🔗 Health Check: https://your-app-name.onrender.com/health")

    print("\n" + "=" * 50)

    # Run the Flask app
    try:
        flask_app.run(
            host='0.0.0.0',
            port=port,
            debug=debug_mode,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {str(e)}")