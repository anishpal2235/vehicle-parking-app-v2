#!/usr/bin/env python3
"""
Simple startup script for the Parking Management System
"""
import os
import sys

# Add the backend directory to the Python path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_path)

# Import the application components
from app.main import create_app, initialize_database

if __name__ == '__main__':
    app = create_app()
    
    # Initialize database if needed (will not recreate if it exists)
    initialize_database(app, force_reset=False)
    
    print("Starting Parking Management System...")
    print("Access the application at: http://localhost:5000")
    print("Default admin: admin@parking.com / Akpal@123")
    print("Press Ctrl+C to stop the server")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
