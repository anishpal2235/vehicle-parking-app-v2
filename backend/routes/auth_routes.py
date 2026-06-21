from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db, ParkingReservation
from werkzeug.security import generate_password_hash
from utils.helpers import normalize_phone_number, validate_vehicle_format, normalize_vehicle_number, validate_email_domain
from datetime import datetime

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # If user exists and is admin, or if credentials are invalid, show generic error
        if not user or not user.check_password(password) or user.is_admin:
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user)
        return redirect(url_for('user.dashboard'))
        
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        address = request.form.get('address')
        pin_code = request.form.get('pin_code')
        phone = request.form.get('phone')
        vehicle_no = request.form.get('vehicle_no')
        
        # Validate email domain
        is_valid_domain, domain_message = validate_email_domain(email)
        if not is_valid_domain:
            flash(domain_message, 'danger')
            return redirect(url_for('auth.register'))
        
        # Use full name as username instead of email
        username = full_name
        
        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if username already exists
        user = User.query.filter_by(username=username).first()
        if user:
            # If username is taken, append a unique identifier
            username = f"{full_name}_{email.split('@')[0]}"
        
        # Check if phone number already exists using normalized comparison
        if phone:
            normalized_phone = normalize_phone_number(phone)
            if normalized_phone:
                # Get all users and compare normalized phone numbers
                users = User.query.all()
                for user in users:
                    if user.phone and normalize_phone_number(user.phone) == normalized_phone:
                        flash('Phone number already registered. Please use a different phone number.', 'danger')
                        return redirect(url_for('auth.register'))
        
        # Check vehicle number format and normalize
        normalized_vehicle_no = None
        if vehicle_no:
            is_valid, normalized_vehicle_no = validate_vehicle_format(vehicle_no)
            if not is_valid:
                flash('Vehicle number must be in the format AB12CD3456 (2 letters, 2 numbers, 2 letters, 4 numbers).', 'danger')
                return redirect(url_for('auth.register'))
            
            # First check if vehicle number is assigned to another user (case insensitive)
            all_users = User.query.all()
            for user in all_users:
                if user.vehicle_no and normalize_vehicle_number(user.vehicle_no) == normalized_vehicle_no:
                    flash('Vehicle number already registered. Please use a different vehicle number.', 'danger')
                    return redirect(url_for('auth.register'))
            
            # Then check if the vehicle is currently parked (in an active reservation)
            all_active_reservations = ParkingReservation.query.filter_by(active=True).all()
            for reservation in all_active_reservations:
                if normalize_vehicle_number(reservation.vehicle_no) == normalized_vehicle_no:
                    flash('This vehicle is currently parked. It cannot be registered until it is released.', 'danger')
                    return redirect(url_for('auth.register'))
        
        new_user = User(
            username=username, 
            email=email, 
            password=password,
            full_name=full_name,
            address=address,
            pin_code=pin_code,
            phone=phone,
            vehicle_no=normalized_vehicle_no  # Use the normalized version
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Send welcome email
            try:
                from services.email_service import EmailService
                from flask import current_app
                
                # Validate email before proceeding
                if not email or not isinstance(email, str) or '@' not in email:
                    current_app.logger.error(f"Invalid email for welcome email: {email} (type: {type(email)})")
                    flash('Registration successful! Welcome email could not be sent due to invalid email. Please log in.', 'warning')
                    return redirect(url_for('auth.login'))
                
                current_app.logger.info(f"Starting welcome email process for {email}")
                
                # Get the base URL for the application
                base_url = current_app.config.get('SERVER_NAME', 'localhost:5000')
                if not base_url or not isinstance(base_url, str):
                    base_url = 'localhost:5000'
                
                if not base_url.startswith('http'):
                    base_url = f"http://{base_url}"
                
                current_app.logger.info(f"Base URL: {base_url}")
                
                # Initialize email service with current app context
                current_app.logger.info("Initializing EmailService...")
                email_service = EmailService(current_app)
                current_app.logger.info("EmailService initialized successfully")
                
                subject = "Welcome to Parking Management System!"
                current_app.logger.info(f"Email subject: {subject}")
                
                # Create HTML content
                current_app.logger.info("Creating HTML email content...")
                html_content = f"""
                <html>
                    <head>
                        <style>
                            body {{
                                font-family: 'Segoe UI', Arial, sans-serif;
                                line-height: 1.6;
                                color: #333;
                                max-width: 600px;
                                margin: 0 auto;
                                padding: 20px;
                            }}
                            .container {{
                                background-color: #f9f9f9;
                                border-radius: 8px;
                                overflow: hidden;
                                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                            }}
                            .header {{
                                background-color: #007bff;
                                color: white;
                                padding: 20px;
                                text-align: center;
                            }}
                            .content {{
                                padding: 20px;
                                background-color: white;
                            }}
                            .welcome-box {{
                                background-color: #e3f2fd;
                                border-left: 4px solid #007bff;
                                padding: 15px;
                                margin: 20px 0;
                            }}
                            .btn {{
                                display: inline-block;
                                background-color: #007bff;
                                color: white;
                                text-decoration: none;
                                padding: 12px 24px;
                                border-radius: 4px;
                                font-weight: bold;
                                margin: 20px 0;
                            }}
                            .footer {{
                                background-color: #f5f5f5;
                                padding: 15px;
                                text-align: center;
                                font-size: 12px;
                                color: #666;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>Welcome to Parking Management System!</h1>
                                <p>Your account has been successfully created</p>
                            </div>
                            <div class="content">
                                <div class="welcome-box">
                                    <h2>Hello {full_name}!</h2>
                                    <p>Welcome to our Parking Management System. We're excited to have you on board!</p>
                                </div>
                                
                                <h3>Your Account Details:</h3>
                                <ul>
                                    <li><strong>Username:</strong> {username}</li>
                                    <li><strong>Email:</strong> {email}</li>
                                    {f'<li><strong>Phone:</strong> {phone}</li>' if phone else ''}
                                    {f'<li><strong>Vehicle Number:</strong> {vehicle_no}</li>' if vehicle_no else ''}
                                </ul>
                                
                                <h3>What You Can Do:</h3>
                                <ul>
                                    <li>Book parking spots in advance</li>
                                    <li>Receive daily reminders</li>
                                    <li>Get monthly activity reports</li>
                                    <li>Manage your parking preferences</li>
                                    <li>Track your parking history</li>
                                </ul>
                                
                                <p style="text-align: center;">
                                    <a href="{base_url}/login" class="btn">LOGIN NOW</a>
                                </p>
                                
                                <p><strong>Next Steps:</strong></p>
                                <ol>
                                    <li>Log in to your account</li>
                                    <li>Set your notification preferences</li>
                                    <li>Book your first parking spot!</li>
                                </ol>
                            </div>
                            <div class="footer">
                                <p>Thank you for choosing our Parking Management System!</p>
                                <p>If you have any questions, please contact our support team.</p>
                            </div>
                        </div>
                    </body>
                </html>
                """
                
                current_app.logger.info(f"HTML content created, length: {len(html_content)} characters")
                current_app.logger.info(f"About to send email to: {email} (type: {type(email)})")
                
                # Send the welcome email
                current_app.logger.info("Calling email_service.send_email()...")
                email_sent = email_service.send_email(email, subject, html_content)
                
                if email_sent:
                    current_app.logger.info(f"Welcome email sent successfully to {email}")
                    flash('Registration successful! A welcome email has been sent to your email address. Please log in.', 'success')
                else:
                    current_app.logger.warning(f"Failed to send welcome email to {email}")
                    flash('Registration successful! Welcome email could not be sent. Please log in.', 'warning')
                
            except Exception as email_error:
                # Log the email error but don't fail the registration
                current_app.logger.error(f"Failed to send welcome email to {email}: {str(email_error)}")
                current_app.logger.error(f"Error type: {type(email_error).__name__}")
                current_app.logger.error(f"Full error details: {email_error}")
                current_app.logger.error(f"Email variable at error time: {email} (type: {type(email)})")
                flash('Registration successful! Welcome email could not be sent. Please log in.', 'warning')
                
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('auth.register'))
        
    return render_template('auth/register.html')

@auth.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate email domain
        is_valid_domain, domain_message = validate_email_domain(email)
        if not is_valid_domain:
            flash(domain_message, 'danger')
            return redirect(url_for('auth.admin_login'))
        
        user = User.query.filter_by(email=email, is_admin=True).first()
        
        if not user or not user.check_password(password):
            flash('Invalid admin credentials.', 'danger')
            return redirect(url_for('auth.admin_login'))
        
        login_user(user)
        return redirect(url_for('admin.dashboard'))
        
    return render_template('auth/admin_login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@auth.route('/test-email', methods=['GET', 'POST'])
def test_email():
    """Test endpoint to verify email functionality"""
    if request.method == 'POST':
        test_email = request.form.get('test_email')
        if test_email:
            try:
                from services.email_service import EmailService
                from flask import current_app
                
                email_service = EmailService(current_app)
                
                subject = "Test Email from Parking App"
                html_content = """
                <html>
                    <body>
                        <h1>Test Email</h1>
                        <p>This is a test email to verify the email service is working.</p>
                        <p>If you receive this, the email configuration is correct.</p>
                        <p>Time sent: """ + str(datetime.now()) + """</p>
                    </body>
                </html>
                """
                
                email_sent = email_service.send_email(test_email, subject, html_content)
                if email_sent:
                    flash('Test email sent successfully! Please check your inbox (and spam folder).', 'success')
                else:
                    flash('Failed to send test email. Check the logs for details.', 'danger')
                    
            except Exception as e:
                current_app.logger.error(f"Test email error: {str(e)}")
                flash(f'Error sending test email: {str(e)}', 'danger')
                
        return redirect(url_for('auth.test_email'))
    
    return render_template('auth/test_email.html')