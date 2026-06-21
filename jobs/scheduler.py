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
        
        # Add daily reminder job - runs every hour to check user preferences
        scheduler.add_job(
            id='daily_reminders',
            func=send_daily_reminders,
            trigger='cron',
            hour='*',  # Run every hour
            minute=0,  # At the top of each hour
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
        
        # Add a job to verify scheduler is running - runs every 15 minutes
        scheduler.add_job(
            id='scheduler_heartbeat',
            func=scheduler_heartbeat,
            trigger='interval',
            minutes=15,
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
        
        # Get current hour
        current_time = datetime.now(IST)
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        app.logger.info(f"Running daily reminder check at {current_hour:02d}:{current_minute:02d}")
        
        # Get all users who don't have an active reservation
        active_user_ids = db.session.query(ParkingReservation.user_id).filter_by(active=True).distinct().all()
        active_user_ids = [u[0] for u in active_user_ids]
        
        users_without_reservation = User.query.filter(User.id.notin_(active_user_ids) if active_user_ids else True).all()
        
        app.logger.info(f"Found {len(users_without_reservation)} users without active reservations to check for reminders.")
        
        reminders_sent = 0
        if not users_without_reservation:
            app.logger.info("No users found without active reservations. No reminders to send.")

        for user in users_without_reservation:
            app.logger.info(f"Processing user: {user.email} (ID: {user.id}, Admin: {user.is_admin})")
            
            # Skip admin users
            if user.is_admin:
                app.logger.info(f"Skipping admin user: {user.email}")
                continue
                
            # Check if it's time to send reminder based on user preference
            reminder_time_str = getattr(user, 'reminder_time', '18:00') # Default to 18:00
            notification_pref = getattr(user, 'notification_preference', 'email')
            app.logger.info(f"User {user.email}: PrefTime='{reminder_time_str}', PrefMethod='{notification_pref}', CurrentHour={current_hour}")

            try:
                if not reminder_time_str or ':' not in reminder_time_str:
                    app.logger.warning(f"Invalid or missing reminder_time format for user {user.email} (ID: {user.id}): '{reminder_time_str}'. Skipping.")
                    continue

                reminder_hour = int(reminder_time_str.split(':')[0])
                
                # Log user reminder preference
                # app.logger.debug(f"User {user.full_name} preferred reminder time: {reminder_time_str}, current hour: {current_hour}") # Already have a similar log
                
                # Only send if the current hour matches the user's preferred hour
                if reminder_hour == current_hour:
                    app.logger.info(f"MATCH: Current hour ({current_hour}) matches reminder hour ({reminder_hour}) for user {user.email}.")
                    message = f"Hello {user.full_name or user.username}, don't forget to book your parking spot for tomorrow if needed!"
                    
                    # Send reminder using user's preferred method
                    result = notification_service.send_daily_reminder(user, message)
                    
                    if result:
                        reminders_sent += 1
                        app.logger.info(f"SUCCESS: Reminder sent to {user.email} via {notification_pref}.")
                    else:
                        app.logger.error(f"FAILURE: Failed to send reminder to {user.email} via {notification_pref}.")
                else:
                    app.logger.info(f"NO MATCH: Current hour ({current_hour}) does not match reminder hour ({reminder_hour}) for {user.email}. Skipping reminder.")
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
        dirs_to_clean = ['static/reports', 'static/exports']
        
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
        server_name = app.config.get('SERVER_NAME')
        if server_name and 'none' not in server_name.lower():
            # Use full URL with server name
            file_url = f"http://{server_name}/{export_path}"
        else:
            # Use relative URL that will work regardless of domain
            file_url = f"/{export_path}"
        notification_service.send_csv_export_notification(user, file_url)
        
        app.logger.info(f"CSV export generated for user {user.email} at {export_path}")
        return export_path 