import requests
import os
import json
import logging
from datetime import datetime
from services.email_service import EmailService

# Create a logger for the module
logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, app=None):
        self.app = app
        self.email_service = EmailService(app)
        
        # Get Google Chat webhook URL from environment variables
        self.gchat_webhook_url = os.environ.get('GCHAT_WEBHOOK_URL', '')
        
    def send_daily_reminder(self, user, message):
        """
        Send a daily reminder to a user via their preferred notification method
        
        Parameters:
        - user: User object containing preferences
        - message: Message content
        """
        # Get user's notification preferences (default to email if not set)
        notification_method = getattr(user, 'notification_preference', 'email')
        gchat_email_value = getattr(user, 'gchat_email', None)
        webhook_url_set = bool(self.gchat_webhook_url)
        
        log_msg = (f"Checking notification for {user.email}. Method: '{notification_method}', "
                   f"GChat Email: '{gchat_email_value}', Webhook Set: {webhook_url_set}")
        if self.app:
            self.app.logger.info(log_msg)
        else:
            logger.info(log_msg)

        # Condition checks for Google Chat
        gchat_condition_met = (
            notification_method == 'gchat' and 
            webhook_url_set and 
            gchat_email_value # Check if gchat_email has a value
        )
        
        if gchat_condition_met:
            if self.app: self.app.logger.info(f"Attempting Google Chat notification for {user.email}.")
            else: logger.info(f"Attempting Google Chat notification for {user.email}.")
            # Call GChat and immediately return its result (True for success, False for failure)
            return self.send_gchat_notification(gchat_email_value, message)
        else:
            # Log why GChat wasn't chosen
            reason = []
            if notification_method != 'gchat': reason.append("preference is not gchat")
            if not webhook_url_set: reason.append("webhook URL not set")
            if not gchat_email_value: reason.append("user gchat_email not set")
            reason_str = ", ".join(reason) if reason else "fallback condition"
            
            if self.app: self.app.logger.info(f"Falling back to email for {user.email}. Reason: {reason_str}.")
            else: logger.info(f"Falling back to email for {user.email}. Reason: {reason_str}.")
            
            subject = "🚗 Your Daily Parking Reminder"
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
                            padding: 0;
                        }}
                        .container {{
                            background-color: #f9f9f9;
                            border-radius: 8px;
                            overflow: hidden;
                            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
                        }}
                        .header {{
                            background-color: #3498db;
                            color: white;
                            padding: 20px;
                            text-align: center;
                        }}
                        .content {{
                            padding: 20px;
                            background-color: white;
                        }}
                        .message {{
                            padding: 15px;
                            background-color: #f0f8ff;
                            border-left: 4px solid #3498db;
                            margin-bottom: 20px;
                        }}
                        .btn {{
                            display: inline-block;
                            background-color: #3498db;
                            color: white;
                            text-decoration: none;
                            padding: 10px 20px;
                            border-radius: 4px;
                            font-weight: bold;
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
                            <h1>Parking Reminder</h1>
                            <p>{datetime.now().strftime('%A, %B %d, %Y')}</p>
                        </div>
                        <div class="content">
                            <div class="message">
                                <p>{message}</p>
                            </div>
                            <p>Managing your parking has never been easier. Book a spot now to secure your space!</p>
                            <p style="text-align: center; margin: 30px 0;">
                                <a href="http://localhost:5000/user/dashboard" class="btn">BOOK A SPOT NOW</a>
                            </p>
                        </div>
                        <div class="footer">
                            <p>Thank you for using our Parking App!</p>
                            <p>This email was sent to {user.email}</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            return self.email_service.send_email(user.email, subject, html_content)
            
    def send_gchat_notification(self, user_email, message):
        """
        Send a notification to a user via Google Chat
        
        Parameters:
        - user_email: Email of the user to notify
        - message: Message content
        """
        try:
            # Prepare the payload for Google Chat webhook
            payload = {
                "text": message,
                "cards": [{
                    "header": {
                        "title": "Parking Reminder",
                        "subtitle": f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    },
                    "sections": [{
                        "widgets": [{
                            "textParagraph": {
                                "text": message
                            }
                        },
                        {
                            "buttons": [{
                                "textButton": {
                                    "text": "GO TO DASHBOARD",
                                    "onClick": {
                                        "openLink": {
                                            "url": "http://localhost:5000/user/dashboard"
                                        }
                                    }
                                }
                            }]
                        }]
                    }]
                }]
            }
            
            # Send the notification to Google Chat
            headers = {'Content-Type': 'application/json; charset=UTF-8'}
            response = requests.post(self.gchat_webhook_url, data=json.dumps(payload), headers=headers)
            
            if response.status_code == 200:
                if self.app:
                    self.app.logger.info(f"Google Chat notification sent to {user_email}")
                else:
                    logger.info(f"Google Chat notification sent to {user_email}")
                return True
            else:
                if self.app:
                    self.app.logger.error(f"Failed to send Google Chat notification: {response.text}")
                else:
                    logger.error(f"Failed to send Google Chat notification: {response.text}")
                return False
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error sending Google Chat notification: {str(e)}")
            else:
                logger.error(f"Error sending Google Chat notification: {str(e)}")
            return False

    def send_csv_export_notification(self, user, file_url):
        """
        Send a notification that a CSV export is ready
        
        Parameters:
        - user: User object
        - file_url: URL to the exported CSV file
        """
        # Make sure file_url is properly formatted
        if file_url.startswith('/'):
            # Handle relative URL - ensure it will work when clicked in email
            if self.app and self.app.config.get('SERVER_NAME'):
                file_url = f"http://{self.app.config.get('SERVER_NAME')}{file_url}"
            else:
                # Default to localhost if no server name is configured
                file_url = f"http://localhost:5000{file_url}"
            
        subject = "📊 Your Parking Data Export is Ready"
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
                        padding: 0;
                    }}
                    .container {{
                        background-color: #f9f9f9;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
                    }}
                    .header {{
                        background-color: #27ae60;
                        color: white;
                        padding: 20px;
                        text-align: center;
                    }}
                    .content {{
                        padding: 20px;
                        background-color: white;
                    }}
                    .download-box {{
                        background-color: #f2f9f2;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 20px;
                        margin: 20px 0;
                        text-align: center;
                    }}
                    .btn {{
                        display: inline-block;
                        background-color: #27ae60;
                        color: white;
                        text-decoration: none;
                        padding: 10px 20px;
                        border-radius: 4px;
                        font-weight: bold;
                    }}
                    .info {{
                        background-color: #e7f4fd;
                        padding: 10px 15px;
                        border-left: 4px solid #3498db;
                        margin-bottom: 20px;
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
                        <h1>Your Data Export is Ready</h1>
                        <p>{datetime.now().strftime('%A, %B %d, %Y')}</p>
                    </div>
                    <div class="content">
                        <p>Hello {user.full_name},</p>
                        <p>Your requested CSV export of parking data has been completed and is ready for download.</p>
                        
                        <div class="download-box">
                            <h3>🚗 Parking Data Export</h3>
                            <p>Your file is now available for download</p>
                            <p><a href="{file_url}" class="btn">DOWNLOAD CSV FILE</a></p>
                        </div>
                        
                        <div class="info">
                            <p><strong>Important:</strong> This link will be valid for 24 hours.</p>
                            <p>The export includes your complete parking history, including parking lot information, timestamps, duration, and costs.</p>
                        </div>
                        
                        <p>Need to analyze more data? You can always generate a new export from your dashboard.</p>
                    </div>
                    <div class="footer">
                        <p>Thank you for using our Parking App!</p>
                        <p>This email was sent to {user.email}</p>
                    </div>
                </div>
            </body>
        </html>
        """
        return self.email_service.send_email(user.email, subject, html_content) 