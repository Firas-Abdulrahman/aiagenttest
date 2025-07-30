import os
import requests
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from whatsapp_workflow import WhatsAppWorkflow

# Load environment variables from .env file (for local development)
# In production (Render), environment variables are set directly
load_dotenv()


class WhatsAppConfig:
    def __init__(self):
        """Initialize configuration from environment variables"""
        # Load credentials from environment variables
        self.whatsapp_token = os.getenv('WHATSAPP_TOKEN')
        self.app_id = os.getenv('APP_ID')
        self.client_secret = os.getenv('CLIENT_SECRET')
        self.waba_id = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
        self.verify_token = os.getenv('VERIFY_TOKEN', 'my_webhook_verify_token_2024')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        # Debug: Print what we loaded (safely)
        self.print_debug_info()

        # Phone number ID - try to get from env first, then auto-fetch
        self.phone_number_id = os.getenv('PHONE_NUMBER_ID')

        # Auto-fetch phone number ID if not provided
        if not self.phone_number_id and self.whatsapp_token and self.waba_id:
            print("🔍 Phone number ID not found in .env, attempting auto-fetch...")
            self.phone_number_id = self.get_phone_number_id()
        elif self.phone_number_id:
            print(f"✅ Using phone number ID from .env: {self.phone_number_id}")

    def print_debug_info(self):
        """Print debug information about loaded credentials"""
        print("\n" + "=" * 50)
        print("🔧 WHATSAPP BOT CONFIGURATION")
        print("=" * 50)
        print(f"WHATSAPP_TOKEN: {'✅ Loaded' if self.whatsapp_token else '❌ Missing'}")
        print(f"APP_ID: {'✅ Loaded' if self.app_id else '❌ Missing'}")
        print(f"CLIENT_SECRET: {'✅ Loaded' if self.client_secret else '❌ Missing'}")
        print(f"WHATSAPP_BUSINESS_ACCOUNT_ID: {'✅ Loaded' if self.waba_id else '❌ Missing'}")
        print(f"VERIFY_TOKEN: {'✅ Loaded' if self.verify_token else '❌ Missing'}")
        print(f"OPENAI_API_KEY: {'✅ Loaded' if self.openai_api_key else 'ℹ️ Missing (Optional)'}")

        if self.whatsapp_token:
            print(f"Token preview: {self.whatsapp_token[:15]}...")
        if self.waba_id:
            print(f"WABA ID: {self.waba_id}")
        print("=" * 50 + "\n")

    def get_phone_number_id(self):
        """Get phone number ID from WhatsApp Business Account"""
        try:
            print(f"🔍 Fetching phone numbers from WABA: {self.waba_id}")

            url = f"https://graph.facebook.com/v18.0/{self.waba_id}/phone_numbers"
            headers = {
                'Authorization': f'Bearer {self.whatsapp_token}'
            }

            print(f"📡 Making request to: {url}")

            response = requests.get(url, headers=headers)

            print(f"📋 Response status: {response.status_code}")

            if response.status_code == 401:
                print("❌ 401 Unauthorized - Possible issues:")
                print("   1. Invalid WhatsApp Token")
                print("   2. Token doesn't have permission for this WABA")
                print("   3. Incorrect WhatsApp Business Account ID")
                print("   4. Token expired")
                print(f"📋 Error response: {response.text}")
                return None

            if response.status_code == 403:
                print("❌ 403 Forbidden - Permission denied")
                print(f"📋 Error response: {response.text}")
                return None

            response.raise_for_status()
            data = response.json()

            print(f"📋 Phone numbers response: {json.dumps(data, indent=2)}")

            phone_numbers = data.get('data', [])

            if phone_numbers:
                phone_number_id = phone_numbers[0]['id']
                phone_number = phone_numbers[0]['display_phone_number']
                status = phone_numbers[0].get('verified_name', 'Unknown')

                print(f"✅ Found phone number: {phone_number}")
                print(f"📱 Phone Number ID: {phone_number_id}")
                print(f"📋 Status: {status}")

                return phone_number_id
            else:
                print("❌ No phone numbers found in this WhatsApp Business Account")
                print("\n📝 To add a phone number:")
                print("   1. Go to https://business.facebook.com/")
                print("   2. Navigate to WhatsApp Manager")
                print("   3. Click 'Add phone number'")
                print("   4. Follow the verification process")
                return None

        except requests.exceptions.RequestException as e:
            print(f"🌐 Request error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"📋 Error response: {e.response.text}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return None

    def get_config_dict(self):
        """Return configuration as dictionary"""
        return {
            'whatsapp_token': self.whatsapp_token,
            'phone_number_id': self.phone_number_id,
            'verify_token': self.verify_token,
            'openai_api_key': self.openai_api_key,
            'app_id': self.app_id,
            'client_secret': self.client_secret,
            'waba_id': self.waba_id
        }

    def validate_config(self):
        """Validate configuration"""
        print("\n🔍 VALIDATING CONFIGURATION...")

        missing_fields = []

        if not self.whatsapp_token:
            missing_fields.append("WHATSAPP_TOKEN")

        if not self.waba_id:
            missing_fields.append("WHATSAPP_BUSINESS_ACCOUNT_ID")

        if not self.phone_number_id:
            missing_fields.append("phone_number_id")

        if missing_fields:
            print(f"❌ Missing required configuration: {', '.join(missing_fields)}")
            return False

        print("✅ Configuration validated successfully")
        return True


def create_flask_app():
    """Create and configure Flask app"""
    app = Flask(__name__)

    # Initialize configuration
    config_manager = WhatsAppConfig()

    # Validate configuration
    if not config_manager.validate_config():
        print("❌ Configuration validation failed.")
        return None

    # Get configuration dictionary
    config = config_manager.get_config_dict()

    # Initialize workflow
    try:
        workflow = WhatsAppWorkflow(config)
        print("✅ WhatsApp workflow initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize workflow: {str(e)}")
        return None

    # Replace the home() function in your app.py with this:

    @app.route('/')
    def home():
        """Home page with useful links"""
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
                .info {{ background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
                a {{ color: #8B4513; text-decoration: none; font-weight: bold; }}
                a:hover {{ text-decoration: underline; }}
                .endpoint {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #8B4513; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>☕ Hef Cafe WhatsApp Bot</h1>

                <div class="status success">
                    ✅ Hef Cafe Ordering Bot is running successfully!
                </div>

                <div class="status info">
                    📱 Phone Number: {config.get('phone_number_id', 'Not configured')}
                </div>

                <h2>🍽️ Bot Features:</h2>
                <div class="endpoint">
                    <strong>☕ Hef Cafe Ordering</strong><br>
                    Step-by-step AI-powered ordering system with bilingual support (Arabic/English)
                </div>

                <div class="endpoint">
                    <strong>🤖 AI-Powered Responses</strong><br>
                    Smart text processing following exact ordering workflow
                </div>

                <div class="endpoint">
                    <strong>📱 Session Management</strong><br>
                    Remembers each customer's ordering progress
                </div>

                <h2>🔧 Available Endpoints:</h2>

                <div class="endpoint">
                    <strong>📊 <a href="/config">Configuration Status</a></strong><br>
                    View current bot configuration (sensitive data hidden)
                </div>

                <div class="endpoint">
                    <strong>🧪 <a href="/test-credentials">Test Credentials</a></strong><br>
                    Test your WhatsApp API credentials
                </div>

                <div class="endpoint">
                    <strong>📱 <a href="/phone-numbers">Phone Numbers</a></strong><br>
                    List available phone numbers
                </div>

                <div class="endpoint">
                    <strong>❤️ <a href="/health">Health Check</a></strong><br>
                    Check if the server is healthy
                </div>

                <div class="endpoint">
                    <strong>🔌 Webhook Endpoint</strong><br>
                    <code>POST /webhook</code> - For WhatsApp webhooks<br>
                    <code>GET /webhook</code> - For webhook verification
                </div>

                <h2>📋 How to Use:</h2>
                <ol>
                    <li><strong>Send any message</strong> to +964 771 111 7646 to start ordering</li>
                    <li><strong>Follow the steps</strong> - the AI will guide you through the process</li>
                    <li><strong>Choose language</strong> - Arabic or English support</li>
                    <li><strong>Select category</strong> - from 13 available menu categories</li>
                    <li><strong>Complete order</strong> - step by step until final confirmation</li>
                </ol>

                <h2>🍽️ Menu Categories:</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                    <div>• Hot Beverages ☕</div>
                    <div>• Cold Beverages 🧊</div>
                    <div>• Cake Slices 🍰</div>
                    <div>• Iced Tea 🧊🍃</div>
                    <div>• Frappuccino ❄️☕</div>
                    <div>• Natural Juices 🍊</div>
                    <div>• Mojito 🌿</div>
                    <div>• Milkshake 🥤</div>
                    <div>• Toast 🍞</div>
                    <div>• Sandwiches 🥪</div>
                    <div>• Croissants 🥐</div>
                    <div>• Savory Pies 🥧</div>
                </div>

                <p><em>Server time: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>

                <p style="text-align: center; color: #8B4513; font-weight: bold;">
                    🎉 Welcome to Hef Cafe Digital Ordering! 🎉
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

        print(f"\n🔐 WEBHOOK VERIFICATION ATTEMPT")
        print(f"Mode: {mode}")
        print(f"Token received: {token}")
        print(f"Expected token: {config['verify_token']}")
        print(f"Challenge: {challenge}")

        if mode == 'subscribe' and token == config['verify_token']:
            print("✅ Webhook verified successfully!")
            return challenge
        else:
            print("❌ Webhook verification failed!")
            return "Verification failed", 403

    @app.route('/webhook', methods=['POST'])
    def handle_webhook():
        """Handle incoming WhatsApp messages"""
        try:
            data = request.get_json()

            if not data:
                print("⚠️ No data received in webhook")
                return jsonify({'status': 'error', 'message': 'No data received'}), 400

            print(f"\n📨 INCOMING WEBHOOK")
            print(f"Data: {json.dumps(data, indent=2)}")

            # Process each entry in the webhook
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        value = change.get('value', {})

                        # Process messages
                        for message in value.get('messages', []):
                            phone_number = message.get('from')
                            message_id = message.get('id')

                            print(f"📱 Processing message {message_id} from {phone_number}")

                            # Process message through workflow
                            response = workflow.handle_whatsapp_message(message)

                            # Send response back to WhatsApp
                            success = workflow.send_whatsapp_message(phone_number, response)

                            if success:
                                print(f"✅ Response sent successfully to {phone_number}")
                            else:
                                print(f"❌ Failed to send response to {phone_number}")

                        # Handle message status updates (delivered, read, etc.)
                        for status in value.get('statuses', []):
                            print(f"📋 Message status update: {status}")

            return jsonify({'status': 'success'}), 200

        except Exception as e:
            print(f"❌ Error processing webhook: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'WhatsApp Bot',
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'version': '1.0.0'
        }), 200

    @app.route('/config', methods=['GET'])
    def show_config():
        """Show current configuration (sensitive data hidden)"""
        safe_config = config.copy()

        # Hide sensitive information
        if safe_config['whatsapp_token']:
            safe_config['whatsapp_token'] = safe_config['whatsapp_token'][:15] + "..."
        if safe_config['openai_api_key']:
            safe_config['openai_api_key'] = safe_config['openai_api_key'][:15] + "..."
        if safe_config['client_secret']:
            safe_config['client_secret'] = safe_config['client_secret'][:10] + "..."

        return jsonify({
            'configuration': safe_config,
            'features': {
                'text_messaging': True,
                'audio_transcription': bool(safe_config['openai_api_key']),
                'image_analysis': bool(safe_config['openai_api_key']),
                'location_processing': True,
                'ai_responses': bool(safe_config['openai_api_key'])
            },
            'status': 'configured'
        }), 200

    @app.route('/test-credentials', methods=['GET'])
    def test_credentials():
        """Test if WhatsApp credentials are working"""
        try:
            url = f"https://graph.facebook.com/v18.0/{config['waba_id']}/phone_numbers"
            headers = {
                'Authorization': f'Bearer {config["whatsapp_token"]}'
            }

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return jsonify({
                    'status': 'success',
                    'message': 'Credentials are working!',
                    'phone_numbers': data.get('data', []),
                    'test_time': __import__('datetime').datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'API test failed with status {response.status_code}',
                    'error_details': response.text,
                    'test_time': __import__('datetime').datetime.now().isoformat()
                }), 500

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
            url = f"https://graph.facebook.com/v18.0/{config['waba_id']}/phone_numbers"
            headers = {
                'Authorization': f'Bearer {config["whatsapp_token"]}'
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            phone_numbers = data.get('data', [])

            formatted_numbers = []
            for phone in phone_numbers:
                formatted_numbers.append({
                    'id': phone.get('id'),
                    'phone_number': phone.get('display_phone_number'),
                    'verified_name': phone.get('verified_name'),
                    'code_verification_status': phone.get('code_verification_status'),
                    'quality_rating': phone.get('quality_rating'),
                    'platform_type': phone.get('platform_type'),
                    'throughput': phone.get('throughput')
                })

            return jsonify({
                'status': 'success',
                'phone_numbers': formatted_numbers,
                'total_count': len(formatted_numbers)
            }), 200

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to fetch phone numbers: {str(e)}'
            }), 500

    @app.route('/test-message', methods=['POST'])
    def test_message():
        """Test endpoint for sending a message (for debugging)"""
        try:
            data = request.get_json()
            phone_number = data.get('phone_number')
            message = data.get('message', 'Hello from WhatsApp Bot! 🤖')

            if not phone_number:
                return jsonify({
                    'status': 'error',
                    'message': 'phone_number is required'
                }), 400

            # Create a test response
            test_response = {
                'type': 'text',
                'content': message,
                'timestamp': __import__('datetime').datetime.now().isoformat()
            }

            # Send the message
            success = workflow.send_whatsapp_message(phone_number, test_response)

            if success:
                return jsonify({
                    'status': 'success',
                    'message': f'Test message sent to {phone_number}'
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to send test message'
                }), 500

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Test message failed: {str(e)}'
            }), 500

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'status': 'error',
            'message': 'Endpoint not found',
            'available_endpoints': [
                '/',
                '/webhook',
                '/health',
                '/config',
                '/test-credentials',
                '/phone-numbers',
                '/test-message'
            ]
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(error)
        }), 500

    return app


def create_simple_test_app():
    """Create a simple app for testing credentials when full app fails"""
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
        config = config_manager.get_config_dict()

        # Hide sensitive info
        safe_config = config.copy()
        if safe_config.get('whatsapp_token'):
            safe_config['whatsapp_token'] = safe_config['whatsapp_token'][:15] + "..."
        if safe_config.get('openai_api_key'):
            safe_config['openai_api_key'] = safe_config['openai_api_key'][:15] + "..."
        if safe_config.get('client_secret'):
            safe_config['client_secret'] = safe_config['client_secret'][:10] + "..."

        return jsonify(safe_config)

    @app.route('/debug-env')
    def debug_env():
        """Debug environment variables"""
        env_vars = {}
        for key in ['WHATSAPP_TOKEN', 'WHATSAPP_BUSINESS_ACCOUNT_ID', 'APP_ID', 'CLIENT_SECRET', 'VERIFY_TOKEN',
                    'OPENAI_API_KEY', 'PHONE_NUMBER_ID']:
            value = os.getenv(key)
            if value:
                if key in ['WHATSAPP_TOKEN', 'CLIENT_SECRET', 'OPENAI_API_KEY']:
                    env_vars[key] = value[:10] + "..." if len(value) > 10 else value
                else:
                    env_vars[key] = value
            else:
                env_vars[key] = "NOT SET"

        return jsonify({
            'environment_variables': env_vars,
            'dotenv_file_exists': os.path.exists('.env')
        })

    return app


# Create the Flask app instance for WSGI servers (like Gunicorn)
# This is required for Render deployment
def create_app():
    """Create app instance for WSGI"""
    return create_flask_app() or create_simple_test_app()


# For Gunicorn (production)
app = create_app()

if __name__ == '__main__':
    print("🚀 Starting WhatsApp Bot Server...")
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
    if not debug_mode:
        print(f"🔗 Production webhook URL: https://your-app-name.onrender.com/webhook")
    else:
        print("🔗 Local development URLs:")
        print("   • Home: http://localhost:5000")
        print("   • Config: http://localhost:5000/config")
        print("   • Test: http://localhost:5000/test-credentials")
        print("   • Health: http://localhost:5000/health")
        print("   • Webhook: http://localhost:5000/webhook")

    print(f"\n🔗 For Meta Developer Console:")
    print(f"   • Verify Token: {os.getenv('VERIFY_TOKEN', 'my_webhook_verify_token_2024')}")

    print("\n" + "=" * 50)

    # Run the Flask app
    try:
        flask_app.run(
            host='0.0.0.0',
            port=port,
            debug=debug_mode,
            use_reloader=False  # Disable reloader to avoid issues with OpenAI
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {str(e)}")