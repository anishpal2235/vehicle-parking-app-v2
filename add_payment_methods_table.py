"""
Migration script to add saved payment methods table to the database.
Run this script after updating the models.py file with the SavedPaymentMethod model.
"""

import sqlite3
import os
from app import create_app

def add_payment_methods_table():
    app = create_app()
    
    # Get database path from SQLAlchemy URI
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    
    if db_uri.startswith('sqlite:///'):
        # For relative path (sqlite:///parking_app.db)
        db_filename = db_uri.replace('sqlite:///', '')
        if not os.path.isabs(db_filename):
            # Check the instance directory
            db_path = os.path.join(app.instance_path, db_filename)
            if not os.path.exists(db_path):
                # Try in the root directory
                db_path = os.path.join(os.getcwd(), db_filename)
        else:
            # Absolute path was specified
            db_path = db_filename
    else:
        print(f"Unsupported database type: {db_uri}")
        return False
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        # Search for any SQLite database file in the instance directory
        instance_dir = app.instance_path
        print(f"Searching for database files in {instance_dir}")
        for file in os.listdir(instance_dir):
            if file.endswith('.db') or file.endswith('.sqlite'):
                print(f"Found potential database file: {file}")
                db_path = os.path.join(instance_dir, file)
                break
        else:
            print("No SQLite database files found.")
            return False
    
    print(f"Adding saved payment methods table to database at {db_path}")
    
    # Connect to SQLite database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create the saved_payment_methods table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            payment_type TEXT NOT NULL,
            card_last_four TEXT,
            card_type TEXT,
            card_holder_name TEXT,
            card_expiry TEXT,
            upi_id TEXT,
            is_default BOOLEAN DEFAULT 0,
            created_at TIMESTAMP,
            last_used TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """)
        
        # Add index for user_id to improve query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_saved_payment_methods_user_id ON saved_payment_methods (user_id)")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print("Migration completed successfully")
        return True
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    add_payment_methods_table() 