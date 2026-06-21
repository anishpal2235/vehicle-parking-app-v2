from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
import logging
import os
from models import db, User, ParkingReservation, IST
from services.notification_service import NotificationService
from services.report_service import ReportService
from services.email_service import EmailService

# Create a logger for the module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize the scheduler
scheduler = APScheduler()

def init_scheduler(app):
    """Initialize the scheduler with the Flask app"""
    # Check if scheduler is already running to prevent duplicate initialization
    if scheduler.running:
        app.logger.warning("Scheduler is already running, skipping initialization")
        return
    
    # Check if scheduler has already been initialized with this app
    if hasattr(scheduler, '_app') and scheduler._app == app:
        app.logger.warning("Scheduler already initialized with this app, skipping initialization")
        return
    
    # Make sure scheduler is properly configured with timezone
    if not app.config.get('SCHEDULER_TIMEZONE'):
        app.config['SCHEDULER_TIMEZONE'] = "Asia/Kolkata"  # IST timezone for scheduler
    
    scheduler.init_app(app)
    scheduler.start()
    
    # Register jobs
    with app.app_context():
        # Remove all existing jobs before adding new ones to avoid duplicates
        scheduler.remove_all_jobs()
        
        app.logger.info('Setting up daily reminder scheduler...')
        
        # Add daily reminder job - runs every minute to check for users who need reminders
        # This allows for precise timing based on user preferences (e.g., 11:14 AM)
        scheduler.add_job(
            id='daily_reminders',
            func=send_daily_reminders,
            trigger='cron',
            minute='*',  # Run every minute
            second=0,
            args=[app]
        )
        
        # Add monthly report job - runs on the 1st of every month at 1 AM
        scheduler.add_job(
            id='monthly_reports',
            func=generate_monthly_reports,
            trigger='cron',
            day=1,
            hour=1,
            minute=0,
            second=0,
            args=[app]
        )
        
        # Add cleanup job for old exports - runs every day at 2 AM
        scheduler.add_job(
            id='cleanup_old_files',
            func=cleanup_old_files,
            trigger='cron',
            hour=2,
            minute=0,
            second=0,
            args=[app]
        )
        
        # Add a job to verify scheduler is running - runs every 5 minutes
        scheduler.add_job(
            id='scheduler_heartbeat',
            func=scheduler_heartbeat,
            trigger='interval',
            minutes=5,
            args=[app]
        )
        
        app.logger.info('Scheduler initialized with all jobs')
        
        # Log all registered jobs
        jobs = scheduler.get_jobs()
        for job in jobs:
            app.logger.info(f'Registered job: {job.id}, next run: {job.next_run_time}')

def scheduler_heartbeat(app):
    """Simple heartbeat to verify scheduler is running"""
    with app.app_context():
        current_time = datetime.now(IST)
        app.logger.info(f"Scheduler heartbeat at {current_time}")

def send_daily_reminders(app):
    """Send daily parking reminders to users based on their preferred reminder time"""
    with app.app_context():
        notification_service = NotificationService(app)
        
        # Get current time
        current_time = datetime.now(IST)
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_date = current_time.date()
        
        app.logger.info(f"Running daily reminder check at {current_hour:02d}:{current_minute:02d}")
        
        # Get all users who don't have an active reservation
        active_user_ids = db.session.query(ParkingReservation.user_id).filter_by(active=True).distinct().all()
        active_user_ids = [u[0] for u in active_user_ids]
        
        users_without_reservation = User.query.filter(User.id.notin_(active_user_ids) if active_user_ids else True).all()
        
        app.logger.info(f"Found {len(users_without_reservation)} users without active reservations to check for reminders.")
        
        # Count users with specific reminder times for this minute
        users_with_exact_time = 0
        for user in users_without_reservation:
            if user.is_admin:
                continue
            reminder_time_str = getattr(user, 'reminder_time', '18:00')
            if reminder_time_str and ':' in reminder_time_str:
                try:
                    reminder_parts = reminder_time_str.split(':')
                    if len(reminder_parts) == 2:
                        reminder_hour = int(reminder_parts[0])
                        reminder_minute = int(reminder_parts[1])
                        if reminder_hour == current_hour and reminder_minute == current_minute:
                            users_with_exact_time += 1
                except (ValueError, IndexError):
                    continue
        
        if users_with_exact_time > 0:
            app.logger.info(f"Found {users_with_exact_time} users who should receive reminders at {current_hour:02d}:{current_minute:02d}")
        else:
            app.logger.debug(f"No users scheduled for reminders at {current_hour:02d}:{current_minute:02d}")
        
        reminders_sent = 0
        if not users_without_reservation:
            app.logger.info("No users found without active reservations. No reminders to send.")
            return 0

        for user in users_without_reservation:
            app.logger.info(f"Processing user: {user.email} (ID: {user.id}, Admin: {user.is_admin})")
            
            # Skip admin users
            if user.is_admin:
                app.logger.info(f"Skipping admin user: {user.email}")
                continue
                
            # Check if it's time to send reminder based on user preference
            reminder_time_str = getattr(user, 'reminder_time', '18:00') # Default to 18:00
            notification_pref = getattr(user, 'notification_preference', 'email')
            app.logger.info(f"User {user.email}: PrefTime='{reminder_time_str}', PrefMethod='{notification_pref}', CurrentTime={current_hour:02d}:{current_minute:02d}")

            try:
                if not reminder_time_str or ':' not in reminder_time_str:
                    app.logger.warning(f"Invalid or missing reminder_time format for user {user.email} (ID: {user.id}): '{reminder_time_str}'. Skipping.")
                    continue

                # Parse both hour and minute from user's preferred time
                reminder_parts = reminder_time_str.split(':')
                if len(reminder_parts) != 2:
                    app.logger.warning(f"Invalid reminder_time format for user {user.email}: '{reminder_time_str}'. Expected HH:MM format.")
                    continue
                    
                reminder_hour = int(reminder_parts[0])
                reminder_minute = int(reminder_parts[1])
                
                # Check if user already received a reminder today
                last_reminder_date = getattr(user, 'last_reminder_date', None)
                
                # Check if current time exactly matches user's preferred time (both hour and minute)
                # This allows users to set specific times like 11:14 AM and get reminders at exactly that time
                if reminder_hour == current_hour and reminder_minute == current_minute:
                    app.logger.info(f"MATCH: Current time ({current_hour:02d}:{current_minute:02d}) exactly matches reminder time ({reminder_hour:02d}:{reminder_minute:02d}) for user {user.email}.")
                    
                    # If user just changed reminder time (last_reminder_date is None), allow them to receive reminder
                    # If user already received reminder today at a different time, skip to prevent duplicates
                    if last_reminder_date is None:
                        app.logger.info(f"User {user.email} just changed reminder time to {reminder_time_str}. Allowing first reminder at new time.")
                    elif last_reminder_date == current_date:
                        app.logger.info(f"User {user.email} already received a reminder today ({current_date}). Skipping.")
                        continue
                    
                    message = f"Hello {user.full_name or user.username}, don't forget to book your parking spot for tomorrow if needed!"
                    
                    # Send reminder using user's preferred method
                    result = notification_service.send_daily_reminder(user, message)
                    
                    if result:
                        # Update the last reminder date to prevent duplicates
                        user.last_reminder_date = current_date
                        db.session.commit()
                        reminders_sent += 1
                        app.logger.info(f"SUCCESS: Reminder sent to {user.email} via {notification_pref} at {current_hour:02d}:{current_minute:02d}.")
                    else:
                        app.logger.error(f"FAILURE: Failed to send reminder to {user.email} via {notification_pref}.")
                else:
                    app.logger.debug(f"NO MATCH: Current time ({current_hour:02d}:{current_minute:02d}) does not match reminder time ({reminder_hour:02d}:{reminder_minute:02d}) for {user.email}. Skipping reminder.")
            except (ValueError, IndexError) as e:
                app.logger.error(f"ERROR: Invalid reminder_time format for user {user.email} (ID: {user.id}): '{reminder_time_str}'. Error: {e}")
                
        app.logger.info(f'Daily reminders job finished. Attempted to send to {reminders_sent} users at {current_hour:02d}:{current_minute:02d}.')
        return reminders_sent

def generate_monthly_reports(app):
    """Generate and send monthly activity reports to all users"""
    with app.app_context():
        report_service = ReportService(app)
        email_service = EmailService(app)
        
        app.logger.info("Starting monthly reports generation process...")
        
        # Get all users except admins
        users = User.query.filter_by(is_admin=False).all()
        app.logger.info(f"Found {len(users)} non-admin users to generate reports for")
        
        reports_sent = 0
        
        for user in users:
            try:
                # Get user's report format preference (default to HTML)
                report_format = getattr(user, 'report_format', 'html')
                app.logger.info(f"Generating {report_format} report for {user.email}...")
                
                # Generate the report
                report_path = report_service.generate_monthly_activity_report(user, report_format)
                app.logger.info(f"Report generated at {report_path}")
                
                # Get the month and year for the report (previous month)
                current_date = datetime.now(IST)
                if current_date.month == 1:
                    month_name = 'December'
                    year = current_date.year - 1
                else:
                    month = current_date.month - 1
                    month_name = datetime(2000, month, 1).strftime('%B')
                    year = current_date.year
                    
                # Prepare and send email
                subject = f"Your Monthly Parking Activity Report - {month_name} {year}"
                
                if report_format.lower() == 'pdf':
                    # For PDF reports, we attach the file
                    html_content = f"""
                    <html>
                        <body>
                            <h2>Monthly Parking Activity Report</h2>
                            <p>Hello {user.full_name},</p>
                            <p>Your monthly parking activity report for {month_name} {year} is attached to this email.</p>
                            <p>Thank you for using our Parking App!</p>
                        </body>
                    </html>
                    """
                    result = email_service.send_email(user.email, subject, html_content, attachments=[report_path])
                else:
                    # For HTML reports, we include the content directly in the email
                    try:
                        with open(report_path, 'r') as file:
                            html_content = file.read()
                    except Exception as e:
                        app.logger.error(f"Could not read HTML report file {report_path}: {str(e)}")
                        html_content = f"""
                        <html>
                            <body>
                                <h2>Monthly Parking Activity Report</h2>
                                <p>Hello {user.full_name},</p>
                                <p>Your monthly parking activity report for {month_name} {year} could not be loaded.</p>
                                <p>Please contact support for assistance.</p>
                            </body>
                        </html>
                        """
                    
                    result = email_service.send_email(user.email, subject, html_content)
                
                if result:
                    reports_sent += 1
                    app.logger.info(f"Monthly report sent to {user.email} via email")
                else:
                    app.logger.error(f"Failed to send monthly report to {user.email}")
                    
            except Exception as e:
                app.logger.error(f"Error generating/sending report for {user.email}: {str(e)}", exc_info=True)
                
        app.logger.info(f'Monthly reports generated and sent to {reports_sent}/{len(users)} users')

def cleanup_old_files(app):
    """Clean up old export and report files (older than 30 days)"""
    with app.app_context():
        # Define directories to clean
        # Get the absolute paths to the frontend static directories
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dirs_to_clean = [
            os.path.join(base_dir, 'frontend', 'static', 'reports'),
            os.path.join(base_dir, 'frontend', 'static', 'exports')
        ]
        
        # Get threshold date (30 days ago)
        threshold_date = datetime.now() - timedelta(days=30)
        
        # Count of deleted files
        deleted_count = 0
        
        # Process each directory
        for directory in dirs_to_clean:
            if not os.path.exists(directory):
                continue
                
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                # Skip if not a file
                if not os.path.isfile(file_path):
                    continue
                    
                # Get file modified time
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Delete if older than threshold
                if file_time < threshold_date:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        app.logger.error(f"Error deleting file {file_path}: {str(e)}")
                        
        app.logger.info(f'Cleanup completed: {deleted_count} old files removed')

def trigger_csv_export(app, user_id):
    """
    Trigger a CSV export job for a specific user
    
    Parameters:
    - app: Flask application instance
    - user_id: ID of the user for whom to generate the export
    
    Returns:
    - export_path: Path to the generated CSV file
    """
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            app.logger.error(f"User not found with ID: {user_id}")
            return None
            
        report_service = ReportService(app)
        notification_service = NotificationService(app)
        
        # Generate the CSV export
        export_path = report_service.generate_csv_export(user)
        
        # Send notification to the user
        # Convert the file system path to a relative URL path
        # The export_path is something like: E:\Desktop\parking_app_v2\frontend\static\exports\filename.csv
        # We need to extract just the relative part: /exports/filename.csv
        
        # Get the filename from the full path
        filename = os.path.basename(export_path)
        
        # Create the relative URL path
        relative_url = f"/static/exports/{filename}"
        
        server_name = app.config.get('SERVER_NAME')
        if server_name and 'none' not in server_name.lower():
            # Use full URL with server name
            file_url = f"http://{server_name}{relative_url}"
        else:
            # Use relative URL that will work regardless of domain
            file_url = relative_url
            
        notification_service.send_csv_export_notification(user, file_url)
        
        app.logger.info(f"CSV export generated for user {user.email} at {export_path}")
        return export_path 