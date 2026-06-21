import multiprocessing

# Gunicorn configuration for production deployment

# Bind to 0.0.0.0:$PORT (environment variable provided by cloud services)
bind = "0.0.0.0:$PORT"

# Worker configuration - generally 2-4 per CPU
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"

# Timeout settings
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "parking_app"

# Preload app for better performance
preload_app = True 