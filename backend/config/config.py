import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///parking_app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # CSRF Protection settings - temporarily disabled to debug payment issues
    WTF_CSRF_ENABLED = False  # Temporarily disable CSRF protection
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'csrf-hard-to-guess-string'
    
    # Server name configuration for URL generation
    SERVER_NAME = os.environ.get('SERVER_NAME') or os.environ.get('DEPLOYMENT_URL') or None
    APPLICATION_ROOT = '/'
    PREFERRED_URL_SCHEME = 'https'
    
    # Database connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,  # Recycle connections after 280 seconds
        'pool_timeout': 20,   # Connection timeout of 20 seconds
        'pool_size': 10,      # Connection pool size
        'max_overflow': 5     # Allow 5 connections beyond pool_size
    }
    
    # APScheduler configuration
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "Asia/Kolkata"  # IST timezone for scheduler
    SCHEDULER_EXECUTORS = {"default": {"type": "threadpool", "max_workers": 20}}
    SCHEDULER_JOB_DEFAULTS = {"coalesce": False, "max_instances": 3}
    
    # Session configuration
    SESSION_COOKIE_SECURE = os.environ.get('PRODUCTION', 'false').lower() == 'true'  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'  # Restrict cookie sending to same-site requests
    
    # Data persistence settings
    PRESERVE_CONTEXT_ON_EXCEPTION = True  # Keep context in case of exceptions
    
    # Google Chat webhook configuration
    GCHAT_WEBHOOK_URL = os.environ.get('GCHAT_WEBHOOK_URL') or None