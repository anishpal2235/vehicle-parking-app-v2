"""
Debug script for monthly reports.
This will test the generation and sending of monthly reports for a specific user.
"""

from app import create_app
import logging
import sys
from datetime import datetime
from jobs.scheduler import generate_monthly_reports
from models import db, User, IST, ParkingReservation

# Setup logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Create the Flask app
app = create_app()

def test_monthly_report(user_email=None, current_month=False):
    """
    Test the monthly report generation and sending for a specific user.
    If user_email is not provided, it will run for all non-admin users.
    
    Parameters:
    - user_email: Email of the user to generate report for
    - current_month: If True, generate report for current month instead of previous month
    """
    with app.app_context():
        if user_email:
            # Find the user
            user = User.query.filter_by(email=user_email).first()
            if not user:
                print(f"User with email {user_email} not found!")
                return
                
            print(f"Found user: {user.full_name} ({user.email})")
            print(f"Report format preference: {getattr(user, 'report_format', 'html')}")
            
            # Create a list with just this user
            users = [user]
        else:
            # Get all non-admin users
            users = User.query.filter_by(is_admin=False).all()
            print(f"Found {len(users)} non-admin users")
            
        # For each user, generate and send the report
        for user in users:
            try:
                # Import the necessary services
                from services.report_service import ReportService
                from services.email_service import EmailService
                
                # Create service instances
                report_service = ReportService(app)
                email_service = EmailService(app)
                
                # Get report format preference (default to HTML)
                report_format = getattr(user, 'report_format', 'html')
                
                # Generate the report
                if current_month:
                    # Generate for current month using the new method
                    current_date = datetime.now(IST)
                    month_name = current_date.strftime('%B')
                    print(f"Generating {report_format} report for CURRENT MONTH ({month_name}) for {user.email}...")
                    
                    # Use the dedicated method for current month reports
                    report_path = report_service.generate_current_month_report(user, report_format)
                else:
                    # Use standard previous month logic
                    print(f"Generating {report_format} report for PREVIOUS MONTH for {user.email}...")
                    report_path = report_service.generate_monthly_activity_report(user, report_format)
                
                print(f"Report generated at: {report_path}")
                
                # Get the month and year for the report
                current_date = datetime.now(IST)
                if current_month:
                    month_name = current_date.strftime('%B')
                    year = current_date.year
                else:
                    # Previous month calculation
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
                    with open(report_path, 'r') as file:
                        html_content = file.read()
                        
                    result = email_service.send_email(user.email, subject, html_content)
                
                if result:
                    print(f"SUCCESS: Monthly report email sent to {user.email}")
                else:
                    print(f"FAILURE: Could not send monthly report email to {user.email}")
                    
            except Exception as e:
                print(f"ERROR generating/sending report for {user.email}: {str(e)}")
                import traceback
                traceback.print_exc()

def generate_current_month_report():
    """Generate a report for the current month"""
    choice = input("Run for all users (a) or a specific user (s)? [a/s]: ").lower()
    
    if choice == 's':
        email = input("Enter the user's email: ")
        test_monthly_report(email, current_month=True)
    else:
        test_monthly_report(current_month=True)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--current":
            # Generate report for current month
            generate_current_month_report()
        else:
            # If an email is provided as a command line argument
            test_monthly_report(sys.argv[1])
    else:
        # Otherwise, ask the user what they want to do
        print("\nMonthly Report Generator")
        print("1. Generate previous month report")
        print("2. Generate current month (May) report")
        choice = input("Enter your choice (1/2): ")
        
        if choice == '2':
            generate_current_month_report()
        else:
            # Default to previous month behavior
            choice = input("Run for all users (a) or a specific user (s)? [a/s]: ").lower()
            
            if choice == 's':
                email = input("Enter the user's email: ")
                test_monthly_report(email)
            else:
                test_monthly_report() 