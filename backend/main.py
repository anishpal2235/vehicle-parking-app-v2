#!/usr/bin/env python3
"""
Main entry point for the Parking Management System backend
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import create_app, initialize_database

if __name__ == '__main__':
    app = create_app()
    
    # Initialize database if needed (will not recreate if it exists)
    initialize_database(app, force_reset=False)
    
    app.run(debug=False, host='0.0.0.0', port=5000)
