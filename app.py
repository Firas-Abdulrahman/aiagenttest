import os
import json
import logging
from flask import Flask, request, jsonify
from config.settings import WhatsAppConfig
from workflow.main import WhatsAppWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_flask_app():
    """Create and configure Flask app with organized structure"""
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

    @app.route('/')
    def home():
        """Enhanced home page with comprehensive information"""
        health = workflow.health_check()
        stats = workflow.get_database_stats()

        return f'''
        <html>
        <head>
            <title>Hef Cafe WhatsApp Bot</title>
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
                <h1>☕ Hef Cafe WhatsApp Bot</h1>

                <div class="status {'success' if health['status'] == 'healthy' else 'warning'}">
                    {'✅ System Status: Healthy' if health['status'] == 'healthy' else '⚠️ System Status: ' + health['status'].title()}
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
                    Contextual conversation flow with step validation
                </div>
                <div class="endpoint">
                    <strong>🗄️ Database Integration</strong><br>
                    Complete order history and analytics tracking
                </div>

                <h2>🔧 API Endpoints:</h2>

                <div class="endpoint">
                    <strong>📊 <a href="/health">Health Check</a></strong><br>
                    Comprehensive system health monitoring
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

                <h2>📋 How to Use:</h2>
                <ol>
                    <li><strong>Message the Bot</strong> - Send any message to start ordering</li>
                    <li><strong>Choose Language</strong> - Arabic or English support</li>
                    <li><strong>Browse Menu</strong> - 13 categories with 40+ items</li>
                    <li><strong>Place Order</strong> - AI guides through the process</li>
                    <li><strong>Confirm & Pay</strong> - Receive order confirmation</li>
                </ol>

                <h2>🍽️ Menu Categories:</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                    <div>1. المشروبات الحارة / Hot Beverages ☕</div>
                    <div>2. المشروبات الباردة / Cold Beverages 🧊</div>
                    <div>3. الحلويات / Sweets 🍰</div>
                    <div>4. الشاي المثلج / Iced Tea 🧊🍃</div>
                    <div>5. فرابتشينو / Frappuccino ❄️☕</div>
                    <div>6. العصائر الطبيعية / Natural Juices 🍊</div>
                    <div>7. موهيتو / Mojito 🌿</div>
                    <div>8. ميلك شيك / Milkshake 🥤</div>
                    <div>9. توست / Toast 🍞</div>
                    <div>10. سندويشات / Sandwiches 🥪</div>
                    <div>11. قطع الكيك / Cake Slices 🍰</div>
                    <div>12. كرواسان / Croissants 🥐</div>
                    <div>13. فطائر مالحة / Savory Pies 🥧</div>
                </div>

                <div class="status info" style="margin-top: 30px;">
                    <strong>System Version:</strong> 2.0.0 (Modular Architecture)<br>
                    <strong>Last Updated:</strong> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                    <strong>AI Status:</strong> {'✅ Active' if workflow.is_ai_available() else '❌ Unavailable'}
                </div>

                <p style="text-align: center; color: #8B4513; font-weight: bold; margin-top: 30px;">
                    🎉 Welcome to Hef Cafe Digital Ordering System! 🎉
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
        """Handle incoming WhatsApp messages"""
        try:
            data = request.get_json()

            if not data:
                logger.warning("⚠️ No data received in webhook")
                return jsonify({'status': 'error', 'message': 'No data received'}), 400

            logger.info(f"📨 Incoming webhook: {json.dumps(data, indent=2)}")

            # Validate payload
            if not workflow.validate_webhook_payload(data):
                logger.warning("⚠️ Invalid webhook payload")
                return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400

            # Extract messages
            messages = workflow.extract_messages_from_webhook(data)

            # Process each message
            for message in messages:
                phone_number = message.get('from')
                message_id = message.get('id')

                logger.info(f"📱 Processing message {message_id} from {phone_number}")

                # Process message through workflow
                response = workflow.handle_whatsapp_message(message)

                # Send response back to WhatsApp
                success = workflow.send_whatsapp_message(phone_number, response)

                if success:
                    logger.info(f"✅ Response sent successfully to {phone_number}")
                else:
                    logger.error(f"❌ Failed to send response to {phone_number}")

            return jsonify({'status': 'success'}), 200

        except Exception as e:
            logger.error(f"❌ Error processing webhook: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """Comprehensive health check endpoint"""
        health = workflow.health_check()
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
                'analytics': True
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
        """Clean up old user sessions"""
        try:
            days_old = request.json.get('days_old', 7) if request.json else 7
            deleted_count = workflow.cleanup_old_sessions(days_old)

            return jsonify({
                'status': 'success',
                'message': f'Cleaned up {deleted_count} old sessions',
                'deleted_count': deleted_count
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
                '/test-credentials', '/phone-numbers', '/simulate', '/cleanup'
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
    print("🚀 Starting Hef Cafe WhatsApp Bot Server...")
    print(f"📅 Server time: {__import__('datetime').datetime.now()}")

    # Try to create full app first
    flask_app = create_flask_app()

    if not flask_app:
        print("⚠️ Full app failed to initialize, starting debug app...")
        flask_app = create_simple_test_app()
        print("🔧 Debug app started - visit endpoints to troubleshoot")
    else:
        print("✅ Full WhatsApp bot initialized successfully!")

    # Get port from environment (Render sets this)
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('ENVIRONMENT', 'development') == 'development'

    print(f"\n🌐 Server starting on port {port}")
    print(f"🔗 Webhook URL: https://your-app-name.onrender.com/webhook")
    print(f"🔗 Health Check: https://your-app-name.onrender.com/health")
    print(f"🔗 Analytics: https://your-app-name.onrender.com/analytics")

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