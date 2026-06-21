# Parking Application Database Management

This document provides instructions for managing the parking application database, including backup, restore, and export operations.

## Database Storage

The parking application uses SQLite as its database, which stores all data in a single file on disk. The database file is located at:

```
parking_app.db
```

This file contains all your application data, including:
- User accounts
- Parking lots
- Parking spots
- Reservations
- Vehicle information

## Database Backup and Restore

### Manual Backup

To manually create a backup at any time:

1. Open a command prompt in the application directory
2. Run:
   ```
   python database_utils.py backup
   ```
3. The backup will be created in the `backups` folder with a timestamp in the filename

### Restoring from Backup

To restore the database from a backup:

1. Open a command prompt in the application directory
2. Run:
   ```
   python database_utils.py restore
   ```
3. Select the backup you want to restore from the list
4. The current database will be backed up before restoration as a safety measure

To restore a specific backup file:

```
python database_utils.py restore path/to/backup.db
```

### Exporting Data to CSV

To export all database tables to CSV files:

1. Open a command prompt in the application directory
2. Run:
   ```
   python database_utils.py export
   ```
3. CSV files for each table will be created in the `exports` folder with a timestamp

## Setting Up Automatic Backups (Windows)

To set up automatic backups using Windows Task Scheduler:

1. Open Task Scheduler (search for it in the Start menu)
2. Click "Create Basic Task..."
3. Enter a name (e.g., "Parking App Database Backup") and description
4. Set the trigger (when you want backups to run, e.g., daily)
5. Choose "Start a program" as the action
6. Browse to select the `scheduled_backup.bat` file in your application directory
7. Complete the wizard and click "Finish"

## Best Practices

1. **Regular Backups**: Set up scheduled backups to run daily
2. **Multiple Backup Locations**: Periodically copy backups to an external drive or cloud storage
3. **Test Restores**: Occasionally test restoring from a backup to ensure it works correctly
4. **Export Before Updates**: Export your data to CSV before major application updates

## Troubleshooting

If you encounter issues with database operations:

1. Ensure the application is not running when performing backups or restores
2. Check that you have write permissions for the application directory
3. Verify that Python and all required modules are installed
4. Look for error messages in the command output for specific issues 