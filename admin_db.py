from flask import Flask
import sqlite3
import os
import sys
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/parking_app.db'
    return app

def inspect_db():
    """Inspect database tables and structure."""
    app = create_app()
    
    # Get database path
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri[10:]  # Remove 'sqlite:///' prefix
    else:
        print(f"Unsupported database: {db_uri}")
        return
        
    print(f"Database path: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found.")
        return
        
    print(f"Database file size: {os.path.getsize(db_path)} bytes")
    
    # Connect to the database
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall()]
            
            print(f"Tables found: {tables}")
            
            # Check for empty tables
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()['count']
                print(f"Table {table}: {count} records")
                
                # Show schema
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print(f"  Columns: {', '.join(col['name'] for col in columns)}")
                
                # Show sample data (up to 5 rows)
                if count > 0:
                    cursor.execute(f"SELECT * FROM {table} LIMIT 5")
                    rows = cursor.fetchall()
                    for i, row in enumerate(rows):
                        print(f"  Row {i+1}: {dict(row)}")
                print()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

def fix_user_ids():
    """Fix user IDs to start from 1."""
    app = create_app()
    
    # Get database path
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri[10:]  # Remove 'sqlite:///' prefix
    else:
        print(f"Unsupported database: {db_uri}")
        return
        
    print(f"Database path: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found.")
        return
        
    # Connect to the database
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get the current user table name (might be Users or users)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='users' OR name='Users')")
            result = cursor.fetchone()
            
            if not result:
                print("Error: User table not found in database.")
                return
                
            user_table = result['name']
            print(f"User table name: {user_table}")
            
            # First, check if there's a gap in user IDs
            cursor.execute(f"SELECT id FROM {user_table} ORDER BY id")
            existing_ids = [row['id'] for row in cursor.fetchall()]
            
            if not existing_ids:
                print("No users found in the database.")
                return
                
            print(f"Current user IDs: {existing_ids}")
            
            # Check if there are any gaps or non-sequential IDs starting from 1
            expected_ids = list(range(1, len(existing_ids) + 1))
            if existing_ids == expected_ids:
                print("User IDs are already correctly sequenced (1 to n).")
                return
                
            print("Found non-sequential user IDs. Fixing...")
            
            # Create a backup of the users table
            backup_table = f"{user_table}_backup_{int(datetime.now().timestamp())}"
            cursor.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM {user_table}")
            print(f"Created backup of users table as {backup_table}")
            
            # Create a mapping of old ID to new ID
            id_map = {old_id: new_id for new_id, old_id in enumerate(existing_ids, 1)}
            print(f"ID mapping: {id_map}")
            
            # Find tables with foreign keys to users
            cursor.execute("""
                SELECT m.name as table_name, p.name as column_name
                FROM sqlite_master m
                JOIN pragma_table_info(m.name) p
                WHERE m.type = 'table'
                AND p.type LIKE '%INT%'
                AND p.name LIKE '%user_id%'
            """)
            fk_tables = cursor.fetchall()
            
            # Update foreign keys in related tables
            for fk_table in fk_tables:
                table_name = fk_table['table_name']
                column_name = fk_table['column_name']
                print(f"Updating foreign keys in {table_name}.{column_name}")
                
                # Create a backup
                backup_name = f"{table_name}_backup_{int(datetime.now().timestamp())}"
                cursor.execute(f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}")
                
                # Update foreign keys using temporary negative IDs
                cursor.execute(f"SELECT id, {column_name} FROM {table_name}")
                for row in cursor.fetchall():
                    row_id = row['id']
                    fk_id = row[column_name]
                    
                    if fk_id in id_map:
                        # Use negative ID temporarily to avoid conflicts
                        temp_id = -id_map[fk_id]
                        cursor.execute(
                            f"UPDATE {table_name} SET {column_name} = ? WHERE id = ?",
                            (temp_id, row_id)
                        )
            
            # Delete and re-insert users with correct IDs
            cursor.execute(f"DELETE FROM {user_table}")
            
            # Get all columns
            cursor.execute(f"PRAGMA table_info({user_table})")
            columns = [col['name'] for col in cursor.fetchall()]
            
            # Get all user data from backup
            cursor.execute(f"SELECT * FROM {backup_table}")
            for user in cursor.fetchall():
                user_dict = dict(user)
                old_id = user_dict['id']
                user_dict['id'] = id_map[old_id]
                
                # Convert dict to SQL
                fields = ', '.join(columns)
                placeholders = ', '.join(['?' for _ in columns])
                values = tuple(user_dict[col] for col in columns)
                
                cursor.execute(f"INSERT INTO {user_table} ({fields}) VALUES ({placeholders})", values)
                print(f"Reinserted user with ID {user_dict['id']} (was {old_id})")
            
            # Fix negative IDs in related tables
            for fk_table in fk_tables:
                table_name = fk_table['table_name']
                column_name = fk_table['column_name']
                
                cursor.execute(f"SELECT id, {column_name} FROM {table_name} WHERE {column_name} < 0")
                for row in cursor.fetchall():
                    row_id = row['id']
                    fk_id = row[column_name]
                    
                    # Convert back to positive
                    cursor.execute(
                        f"UPDATE {table_name} SET {column_name} = ? WHERE id = ?",
                        (-fk_id, row_id)
                    )
            
            # Update sqlite_sequence to ensure new IDs continue from the highest ID
            cursor.execute(f"UPDATE sqlite_sequence SET seq = ? WHERE name = '{user_table}'", (len(existing_ids),))
            
            print("\nVerifying results...")
            cursor.execute(f"SELECT id, username FROM {user_table} ORDER BY id")
            for row in cursor.fetchall():
                print(f"User: {row['username']}, ID: {row['id']}")
            
            # Keep backups for safety
            print("\nBackup tables created during the process:")
            print(f"- {backup_table}")
            for fk_table in fk_tables:
                print(f"- {fk_table['table_name']}_backup_{int(datetime.now().timestamp())}")
                
            print("\nUser ID fix completed successfully!")
            
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

def print_usage():
    print("Usage: python admin_db.py [command]")
    print("Commands:")
    print("  inspect  - Inspect database tables and contents")
    print("  fix_ids  - Fix user IDs to start from 1")
    print("  help     - Show this help message")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "inspect":
        inspect_db()
    elif command == "fix_ids":
        fix_user_ids()
    elif command == "help":
        print_usage()
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1) 