"""
Migration script to add payment fields to the parking_reservations table.
Run this script after updating the models.py file with payment fields.
"""

import sqlite3
import os
from app import create_app

def add_payment_fields():
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
    
    print(f"Adding payment fields to database at {db_path}")
    
    # Connect to SQLite database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the parking_reservations table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='parking_reservations'")
        if not cursor.fetchone():
            print("Table 'parking_reservations' does not exist in the database.")
            conn.close()
            return False
        
        # Check if the columns already exist
        cursor.execute("PRAGMA table_info(parking_reservations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add columns if they don't exist
        columns_to_add = {
            'payment_status': 'TEXT DEFAULT "PENDING"',
            'payment_date': 'TIMESTAMP',
            'payment_method': 'TEXT',
            'transaction_id': 'TEXT'
        }
        
        for column_name, column_type in columns_to_add.items():
            if column_name not in columns:
                print(f"Adding {column_name} column to parking_reservations table")
                try:
                    cursor.execute(f"ALTER TABLE parking_reservations ADD COLUMN {column_name} {column_type}")
                    print(f"Successfully added {column_name} column")
                except sqlite3.OperationalError as e:
                    print(f"Error adding {column_name}: {str(e)}")
            else:
                print(f"Column {column_name} already exists")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print("Migration completed successfully")
        return True
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    add_payment_fields() 