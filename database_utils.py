import os
import sqlite3
import shutil
import datetime
import sys
from config import Config

def get_db_path():
    """Get the database path from config."""
    db_uri = Config.SQLALCHEMY_DATABASE_URI
    if db_uri.startswith('sqlite:///'):
        return db_uri[10:]  # Remove 'sqlite:///' prefix
    else:
        print(f"Unsupported database: {db_uri}")
        return None

def create_backup():
    """Create a backup of the database."""
    db_path = get_db_path()
    if not db_path or not os.path.exists(db_path):
        print("Database not found.")
        return
    
    # Create backups directory if it doesn't exist
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create a backup filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{backup_dir}/parking_app_backup_{timestamp}.db"
    
    try:
        # Create a database connection
        conn = sqlite3.connect(db_path)
        
        # Create a backup connection and save to file
        backup_conn = sqlite3.connect(backup_filename)
        conn.backup(backup_conn)
        
        # Close connections
        backup_conn.close()
        conn.close()
        
        print(f"Database backup created successfully: {backup_filename}")
        return backup_filename
    except Exception as e:
        print(f"Error creating backup: {str(e)}")
        return None

def restore_backup(backup_path=None):
    """Restore database from a backup."""
    if not backup_path:
        # List available backups and prompt for selection
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            print("No backups found.")
            return
        
        backups = [f for f in os.listdir(backup_dir) if f.startswith("parking_app_backup_") and f.endswith(".db")]
        if not backups:
            print("No backups found in the backups directory.")
            return
        
        # Sort backups by date (most recent first)
        backups.sort(reverse=True)
        
        print("Available backups:")
        for i, backup in enumerate(backups):
            print(f"{i+1}. {backup}")
        
        choice = input("Select a backup to restore (number) or press Enter to use the most recent: ")
        if choice.strip():
            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    backup_path = os.path.join(backup_dir, backups[index])
                else:
                    print("Invalid selection.")
                    return
            except ValueError:
                print("Invalid input. Please enter a number.")
                return
        else:
            # Use the most recent backup
            backup_path = os.path.join(backup_dir, backups[0])
    
    # Validate backup file exists
    if not os.path.exists(backup_path):
        print(f"Backup file not found: {backup_path}")
        return
    
    db_path = get_db_path()
    if not db_path:
        return
    
    # Create a backup of the current database before restoring
    current_backup = create_backup()
    if not current_backup:
        choice = input("Failed to create a backup of the current database. Continue anyway? (y/n): ")
        if choice.lower() != 'y':
            print("Restore operation cancelled.")
            return
    
    try:
        # Close any open connections
        print("Restoring database...")
        
        # Copy the backup file to replace the current database
        shutil.copy2(backup_path, db_path)
        
        print(f"Database restored successfully from: {backup_path}")
    except Exception as e:
        print(f"Error restoring backup: {str(e)}")
        if current_backup:
            print(f"You can restore the previous state from: {current_backup}")

def export_csv():
    """Export database tables to CSV files."""
    db_path = get_db_path()
    if not db_path or not os.path.exists(db_path):
        print("Database not found.")
        return
    
    # Create exports directory if it doesn't exist
    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)
    
    # Create a timestamp for the export files
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Create a database connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            
            # Skip internal sqlite tables
            if table_name.startswith('sqlite_'):
                continue
                
            # Export table to CSV
            export_file = f"{export_dir}/{table_name}_{timestamp}.csv"
            
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Get table data
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            # Write to CSV
            with open(export_file, 'w') as f:
                # Write header
                f.write(','.join(columns) + '\n')
                
                # Write rows
                for row in rows:
                    # Convert each value to string and escape commas
                    csv_row = ','.join(['"' + str(value).replace('"', '""') + '"' if value is not None else '' for value in row])
                    f.write(csv_row + '\n')
            
            print(f"Exported {table_name} to {export_file}")
        
        conn.close()
        print("CSV export completed successfully.")
    except Exception as e:
        print(f"Error exporting to CSV: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python database_utils.py [backup|restore|export]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "backup":
        create_backup()
    elif command == "restore":
        backup_path = sys.argv[2] if len(sys.argv) > 2 else None
        restore_backup(backup_path)
    elif command == "export":
        export_csv()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: backup, restore, export") 