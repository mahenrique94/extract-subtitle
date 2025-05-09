from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os
import logging
from app.babel import configure_babel
from flask_migrate import Migrate
from flask_babel import _, format_datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

def create_app():
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Configure the app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # CSRF Configuration
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
    app.config['WTF_CSRF_SSL_STRICT'] = False
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow both localhost and 127.0.0.1
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # More permissive SameSite policy
    app.config['PREFERRED_URL_SCHEME'] = 'http'  # Explicit URL scheme
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    configure_babel(app)
    migrate.init_app(app, db)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = _('Please log in to access this page.')
    login_manager.login_message_category = 'info'
    
    # Add format_datetime to template context
    @app.context_processor
    def inject_format_datetime():
        return dict(format_datetime=format_datetime)
    
    # Register blueprints
    from app.auth import auth as auth_blueprint
    from app.main import main as main_blueprint
    
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(main_blueprint, url_prefix='')
    
    logger.debug('Auth blueprint registered successfully')
    logger.debug('Main blueprint registered successfully')
    
    # Create database tables and upload folder
    with app.app_context():
        db.create_all()
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Print registered routes for debugging
        logger.debug('Registered routes:')
        for rule in app.url_map.iter_rules():
            logger.debug(f'{rule.endpoint}: {rule.rule}')
    
    # Add CSRF error handler
    @app.errorhandler(403)
    def handle_csrf_error(e):
        logger.error(f"CSRF Error: {str(e)}")
        if request.is_xhr:
            return jsonify({"error": "CSRF validation failed"}), 403
        return render_template('error.html', message="CSRF validation failed. Please try again."), 403
    
    return app 