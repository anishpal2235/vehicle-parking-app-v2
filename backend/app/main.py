from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from config.config import Config
from models.models import db, User
from routes import auth, admin, user
from utils.helpers import format_datetime, get_time_difference
from datetime import timedelta
import os
import sqlite3
import logging
from flask_wtf.csrf import CSRFProtect

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import scheduler with error handling
try:
    from jobs import init_scheduler
    from services.cache_service import cache
    SCHEDULER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import scheduler or cache: {str(e)}")
    SCHEDULER_AVAILABLE = False

def create_app():
    # Get absolute paths for templates and static files
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_folder = os.path.join(base_dir, 'frontend', 'templates')
    static_folder = os.path.join(base_dir, 'frontend', 'static')
    
    app = Flask(__name__, 
                template_folder=template_folder,
                static_folder=static_folder)
    app.config.from_object(Config)
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Create a list of routes exempted from CSRF
    csrf.exempt("user.payment")  # Exempt the payment form page
    csrf.exempt("user.process_payment")  # Exempt the payment processing endpoint
    
    # Initialize logging for production
    if not app.debug:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Parking app startup')
    
    # Enhanced session configuration
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # Session lasts for 30 days
    app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in the filesystem
    app.config['SESSION_PERMANENT'] = True  # Make sessions permanent
    app.config['SESSION_USE_SIGNER'] = True  # Add a cryptographic signer
    
    # Override SERVER_NAME with environment variable for cloud deployment
    if os.environ.get('RENDER') or os.environ.get('DEPLOYMENT_URL'):
        app.config['SERVER_NAME'] = os.environ.get('DEPLOYMENT_URL')
    
    # Ensure the instance directory exists
    os.makedirs(app.instance_path, exist_ok=True)
    
    # Initialize database
    db.init_app(app)
    
    # Initialize login manager with enhanced settings
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    login_manager.session_protection = "strong"  # Enhanced security
    login_manager.refresh_view = 'auth.login'
    login_manager.needs_refresh_message = 'Please log in again to confirm your identity'
    login_manager.needs_refresh_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        # Try to load the user from the database
        user = User.query.get(int(user_id))
        return user
    
    # Register blueprints
    app.register_blueprint(auth)
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(user, url_prefix='/user')
    
    # Add a template context processor to provide CSRF token to all templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=lambda: csrf._get_csrf_token())
    
    # Add template filters
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['get_time_difference'] = get_time_difference
    
    # Initialize services and jobs if available
    if SCHEDULER_AVAILABLE:
        # Set app instance for cache
        cache.app = app
        
        # Initialize scheduler with retry
        try:
            app.logger.info("Initializing scheduler...")
            init_scheduler(app)
            app.logger.info("Scheduler initialized successfully")
        except Exception as e:
            app.logger.error(f"Failed to initialize scheduler: {str(e)}")
    else:
        app.logger.warning("Scheduler not available. Daily reminders and other scheduled jobs will not run.")
    
    # Create a home route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.dashboard'))
        return render_template('index.html')
    
    # Add cache cleanup to app context if available
    if SCHEDULER_AVAILABLE:
        @app.before_request
        def cleanup_cache():
            cache.clean_expired()
    
    @app.route('/offline.html')
    def offline():
        """Serve the offline page."""
        return render_template('offline.html')
    
    return app

# Initialize the database and create admin user if it doesn't exist
def initialize_database(app, force_reset=False):
    with app.app_context():
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not db_path.startswith('/'):
            db_path = os.path.join(os.getcwd(), db_path)
        db_exists = os.path.exists(db_path)
        
        # Force recreation if there are schema issues
        if force_reset or not db_exists:
            # Remove existing database if force_reset is True
            if force_reset and db_exists:
                print("Force reset requested. Removing existing database...")
                os.remove(db_path)
                print("Existing database removed.")
            
            print("Creating database tables...")
            db.create_all()
            
            # Create admin user if it doesn't exist
            try:
                admin_exists = User.query.filter_by(is_admin=True).first() is not None
                if not admin_exists:
                    admin_email = 'admin@parking.com'
                    admin_fullname = 'System Administrator'
                    admin = User(
                        username=admin_fullname,
                        email=admin_email,
                        password='Akpal@123',  # This will be hashed in the User.__init__ method
                        is_admin=True,
                        full_name=admin_fullname,
                        address='Parking Administration Office',
                        pin_code='000000'
                    )
                    db.session.add(admin)
                    db.session.commit()
                    print('New admin user created.')
            except Exception as e:
                print(f"Warning: Could not check/create admin user: {str(e)}")
                print("Database tables created, but admin user creation failed.")
            
            print("Database initialization complete.")
        else:
            # Check if schema is compatible
            try:
                # Try a simple query to test schema compatibility
                test_user = User.query.first()
                print("Database already exists and schema is compatible. Using existing database.")
            except Exception as e:
                print(f"Database schema mismatch detected: {str(e)}")
                print("Recreating database with correct schema...")
                
                # Remove the problematic database
                if os.path.exists(db_path):
                    os.remove(db_path)
                    print("Removed incompatible database")
                
                # Recreate tables
                db.create_all()
                print("Database recreated with correct schema")
                
                # Create admin user
                try:
                    admin_email = 'admin@parking.com'
                    admin_fullname = 'System Administrator'
                    admin = User(
                        username=admin_fullname,
                        email=admin_email,
                        password='Akpal@123',
                        is_admin=True,
                        full_name=admin_fullname,
                        address='Parking Administration Office',
                        pin_code='000000'
                    )
                    db.session.add(admin)
                    db.session.commit()
                    print('New admin user created.')
                except Exception as e:
                    print(f"Warning: Could not create admin user: {str(e)}")
                
                print("Database initialization complete.")

if __name__ == '__main__':
    app = create_app()
    
    # Initialize database if needed (will not recreate if it exists)
    initialize_database(app, force_reset=False)
    
    app.run(debug=False)  # Disable debug mode to prevent duplicate scheduler initialization