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
    from config.email_config import (
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
            
            # Log configuration details (without sensitive info)
            app.logger.info(f"Email service initialized with:")
            app.logger.info(f"  SMTP Server: {self.smtp_server}")
            app.logger.info(f"  SMTP Port: {self.smtp_port}")
            app.logger.info(f"  SMTP Username: {self.smtp_username}")
            app.logger.info(f"  Sender Email: {self.sender_email}")
            app.logger.info(f"  Password configured: {'Yes' if self.smtp_password and self.smtp_password != 'your-app-password' else 'No'}")
        else:
            if EMAIL_CONFIG_FOUND:
                logger.info("Email configuration loaded from email_config.py")
            else:
                logger.warning("Using default email configuration. Emails may not send properly.")
            
            # Log configuration details (without sensitive info)
            logger.info(f"Email service initialized with:")
            logger.info(f"  SMTP Server: {self.smtp_server}")
            logger.info(f"  SMTP Port: {self.smtp_port}")
            logger.info(f"  SMTP Username: {self.smtp_username}")
            logger.info(f"  Sender Email: {self.sender_email}")
            logger.info(f"  Password configured: {'Yes' if self.smtp_password and self.smtp_password != 'your-app-password' else 'No'}")
        
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
            # Validate recipient email with better error handling
            if recipient is None:
                if self.app:
                    self.app.logger.error("Recipient email is None")
                else:
                    logger.error("Recipient email is None")
                return False
                
            if not isinstance(recipient, str):
                if self.app:
                    self.app.logger.error(f"Recipient email is not a string: {type(recipient)}")
                else:
                    logger.error(f"Recipient email is not a string: {type(recipient)}")
                return False
                
            if not recipient.strip() or '@' not in recipient:
                if self.app:
                    self.app.logger.error(f"Invalid recipient email format: '{recipient}'")
                else:
                    logger.error(f"Invalid recipient email format: '{recipient}'")
                return False
            
            # Log email attempt with more details
            if self.app:
                self.app.logger.info(f"Starting email send process to {recipient}")
                self.app.logger.info(f"Subject: {subject}")
                self.app.logger.info(f"Content length: {len(html_content)} characters")
            else:
                logger.info(f"Starting email send process to {recipient}")
                logger.info(f"Subject: {subject}")
                logger.info(f"Content length: {len(html_content)} characters")
            
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
            
            # Log email attempt
            if self.app:
                self.app.logger.info(f"Attempting to send email to {recipient} via {self.smtp_server}:{self.smtp_port}")
            else:
                logger.info(f"Attempting to send email to {recipient} via {self.smtp_server}:{self.smtp_port}")
            
            # Connect to the SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            
            if self.app:
                self.app.logger.info(f"Connected to SMTP server, attempting login with username: {self.smtp_username}")
            else:
                logger.info(f"Connected to SMTP server, attempting login with username: {self.smtp_username}")
                
            server.login(self.smtp_username, self.smtp_password)
            
            # Send the email
            server.sendmail(self.sender_email, recipient, msg.as_string())
            server.quit()
            
            if self.app:
                self.app.logger.info(f"Email sent successfully to {recipient} with subject: {subject}")
            else:
                logger.info(f"Email sent successfully to {recipient} with subject: {subject}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP Authentication failed: {str(e)}"
            if self.app:
                self.app.logger.error(error_msg)
            else:
                logger.error(error_msg)
            return False
            
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipient email refused: {str(e)}"
            if self.app:
                self.app.logger.error(error_msg)
            else:
                logger.error(error_msg)
            return False
            
        except smtplib.SMTPServerDisconnected as e:
            error_msg = f"SMTP server disconnected: {str(e)}"
            if self.app:
                self.app.logger.error(error_msg)
            else:
                logger.error(error_msg)
            return False
            
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error occurred: {str(e)}"
            if self.app:
                self.app.logger.error(error_msg)
            else:
                logger.error(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Unexpected error sending email: {str(e)}"
            if self.app:
                self.app.logger.error(error_msg)
                self.app.logger.error(f"Error type: {type(e).__name__}")
                self.app.logger.error(f"Error details: {str(e)}")
            else:
                logger.error(error_msg)
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {str(e)}")
            return False 