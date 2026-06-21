# Routes package for Parking Management System
from . import auth_routes, admin_routes, user_routes

# Create blueprints
auth = auth_routes.auth
admin = admin_routes.admin
user = user_routes.user
