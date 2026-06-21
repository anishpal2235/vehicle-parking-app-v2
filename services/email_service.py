import smtplib
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Create a logger for the module
logger = logging.getLogger(__name__)

# Import email configuration
try:
    from email_config import (
        SMTP_SERVER, 
        SMTP_PORT, 
        SMTP_USERNAME, 
        SMTP_PASSWORD, 
        SENDER_EMAIL
    )
    EMAIL_CONFIG_FOUND = True
except ImportError:
    logger.warning("Email configuration not found. Using default values.")
    EMAIL_CONFIG_FOUND = False
    # Default values (will be overridden by environment variables if present)
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'your-email@gmail.com'
    SMTP_PASSWORD = 'your-app-password'
    SENDER_EMAIL = 'parking-app@example.com'

class EmailService:
    def __init__(self, app=None):
        self.app = app
        
        # Get email configuration from environment variables or config
        self.smtp_server = os.environ.get('SMTP_SERVER', SMTP_SERVER)
        self.smtp_port = int(os.environ.get('SMTP_PORT', SMTP_PORT))
        self.smtp_username = os.environ.get('SMTP_USERNAME', SMTP_USERNAME)
        self.smtp_password = os.environ.get('SMTP_PASSWORD', SMTP_PASSWORD)
        self.sender_email = os.environ.get('SENDER_EMAIL', SENDER_EMAIL)
        
        # Log configuration status but not sensitive info
        if app:
            if EMAIL_CONFIG_FOUND:
                app.logger.info("Email configuration loaded from email_config.py")
            else:
                app.logger.warning("Using default email configuration. Emails may not send properly.")
        
    def send_email(self, recipient, subject, html_content, text_content=None, attachments=None):
        """
        Send an email to the recipient with the given subject and content
        
        Parameters:
        - recipient: Email address of the recipient
        - subject: Subject of the email
        - html_content: HTML content of the email
        - text_content: Plain text content (optional)
        - attachments: List of file paths to attach (optional)
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = recipient
            
            # Add plain text version if provided
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            # Add HTML version
            msg.attach(MIMEText(html_content, 'html'))
            
            # Add attachments if provided
            if attachments:
                for file_path in attachments:
                    with open(file_path, 'rb') as f:
                        part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                    msg.attach(part)
            
            # Connect to the SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            
            if self.app:
                self.app.logger.info(f"Trying to connect to {self.smtp_server}:{self.smtp_port} with username: {self.smtp_username}")
            else:
                logger.info(f"Trying to connect to {self.smtp_server}:{self.smtp_port} with username: {self.smtp_username}")
                
            server.login(self.smtp_username, self.smtp_password)
            
            # Send the email
            server.sendmail(self.sender_email, recipient, msg.as_string())
            server.quit()
            
            if self.app:
                self.app.logger.info(f"Email sent to {recipient} with subject: {subject}")
            else:
                logger.info(f"Email sent to {recipient} with subject: {subject}")
            return True
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Failed to send email: {str(e)}")
            else:
                logger.error(f"Failed to send email: {str(e)}")
            return False 