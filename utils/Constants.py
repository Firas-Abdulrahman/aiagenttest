"""Constants and enumerations"""

# Workflow steps
class WorkflowSteps:
    WAITING_FOR_LANGUAGE = 'waiting_for_language'
    WAITING_FOR_CATEGORY = 'waiting_for_category'
    WAITING_FOR_ITEM = 'waiting_for_item'
    WAITING_FOR_QUANTITY = 'waiting_for_quantity'
    WAITING_FOR_ADDITIONAL = 'waiting_for_additional'
    WAITING_FOR_SERVICE = 'waiting_for_service'
    WAITING_FOR_LOCATION = 'waiting_for_location'
    WAITING_FOR_CONFIRMATION = 'waiting_for_confirmation'
    COMPLETED = 'completed'

# Supported languages
class Languages:
    ARABIC = 'arabic'
    ENGLISH = 'english'

# Service types
class ServiceTypes:
    DINE_IN = 'dine-in'
    DELIVERY = 'delivery'

# Message types
class MessageTypes:
    TEXT = 'text'
    IMAGE = 'image'
    AUDIO = 'audio'
    DOCUMENT = 'document'
    LOCATION = 'location'

# AI Actions
class AIActions:
    LANGUAGE_SELECTION = 'language_selection'
    CATEGORY_SELECTION = 'category_selection'
    ITEM_SELECTION = 'item_selection'
    QUANTITY_SELECTION = 'quantity_selection'
    YES_NO = 'yes_no'
    SERVICE_SELECTION = 'service_selection'
    LOCATION_INPUT = 'location_input'
    CONFIRMATION = 'confirmation'
    SHOW_MENU = 'show_menu'
    HELP_REQUEST = 'help_request'
    STAY_CURRENT_STEP = 'stay_current_step'

# Menu categories (IDs)
class MenuCategories:
    HOT_BEVERAGES = 1
    COLD_BEVERAGES = 2
    SWEETS = 3
    ICED_TEA = 4
    FRAPPUCCINO = 5
    NATURAL_JUICES = 6
    MOJITO = 7
    MILKSHAKE = 8
    TOAST = 9
    SANDWICHES = 10
    CAKE_SLICES = 11
    CROISSANTS = 12
    SAVORY_PIES = 13

# API Configuration
class APIConfig:
    WHATSAPP_API_VERSION = 'v18.0'
    WHATSAPP_BASE_URL = 'https://graph.facebook.com'
    MAX_MESSAGE_LENGTH = 4000
    DEFAULT_LANGUAGE = Languages.ARABIC

# Error messages
class ErrorMessages:
    SYSTEM_ERROR_AR = "عذراً، حدث خطأ. الرجاء إعادة المحاولة"
    SYSTEM_ERROR_EN = "Sorry, something went wrong. Please try again"
    INVALID_INPUT_AR = "الرجاء إدخال اختيار صحيح"
    INVALID_INPUT_EN = "Please enter a valid choice"
    SESSION_EXPIRED_AR = "انتهت جلستك. الرجاء البدء من جديد"
    SESSION_EXPIRED_EN = "Your session has expired. Please start over"