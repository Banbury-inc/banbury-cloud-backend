"""
Email service for sending welcome emails and other user notifications using Twilio SendGrid.
"""
import os
import logging
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Bcc, Subject, PlainTextContent, HtmlContent

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails using Twilio SendGrid."""
    
    def __init__(self):
        """Initialize the email service with SendGrid configuration."""
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('SENDGRID_FROM_EMAIL', 'michael.mills@banbury.io')
        self.from_name = os.getenv('SENDGRID_FROM_NAME', 'Michael Mills')
        self.bcc_email = os.getenv('SENDGRID_BCC_EMAIL', 'mmills6060@gmail.com')  # Email to copy on all sends
        
        if not self.api_key:
            logger.warning("SENDGRID_API_KEY environment variable not set. Email functionality will be disabled.")
            self.client = None
        else:
            self.client = SendGridAPIClient(api_key=self.api_key)
    
    def send_welcome_email(self, user_email: str, user_first_name: str, user_last_name: str, username: str) -> bool:
        """
        Send a welcome email to a newly registered user using SendGrid template.
        
        Args:
            user_email: The user's email address
            user_first_name: The user's first name
            user_last_name: The user's last name
            username: The user's username
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.client:
            logger.warning("SendGrid client not initialized. Cannot send welcome email.")
            return False
            
        try:
            # Create the email content with template
            full_name = f"{user_first_name} {user_last_name}".strip()
            
            # Create the email message using SendGrid template
            message = Mail(
                from_email=From(self.from_email, self.from_name),
                to_emails=To(user_email)
            )
            
            # Add BCC to copy yourself on all emails
            if self.bcc_email and self.bcc_email != user_email:
                message.bcc = Bcc(self.bcc_email)
            
            # Set the template ID
            message.template_id = "d-f532cd6b475a437dab553dfea64ac8a6"
            
            # Set dynamic template data
            message.dynamic_template_data = {
                "first_name": user_first_name,
                "last_name": user_last_name,
                "full_name": full_name,
                "username": username,
                "email": user_email
            }
            
            # Send the email
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Welcome email sent successfully to {user_email} using template")
                return True
            else:
                logger.error(f"Failed to send welcome email to {user_email}. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending welcome email to {user_email}: {str(e)}")
            return False
    
    def send_password_reset_email(self, user_email: str, user_first_name: str, reset_link: str) -> bool:
        """
        Send a password reset email to a user.
        
        Args:
            user_email: The user's email address
            user_first_name: The user's first name
            reset_link: The password reset link
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.client:
            logger.warning("SendGrid client not initialized. Cannot send password reset email.")
            return False
            
        try:
            subject_text = "Password Reset Request - Banbury"
            
            # Plain text content
            plain_text_content = f"""
Password Reset Request

Hi {user_first_name},

We received a request to reset your password for your Banbury account.

Click the link below to reset your password:
{reset_link}

If you didn't request this password reset, please ignore this email. Your password will remain unchanged.

This link will expire in 24 hours.

Best regards,
The Banbury Team
            """.strip()
            
            # HTML content
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset Request</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #000;
            color: #fff;
            padding: 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 0 0 8px 8px;
        }}
        .reset-button {{
            display: inline-block;
            background-color: #000;
            color: #fff;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .warning {{
            background-color: #fff;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            border-left: 4px solid #ff6b6b;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Password Reset Request</h1>
    </div>
    <div class="content">
        <p>Hi {user_first_name},</p>
        
        <p>We received a request to reset your password for your Banbury account.</p>
        
        <p style="text-align: center;">
            <a href="{reset_link}" class="reset-button">Reset Your Password</a>
        </p>
        
        <div class="warning">
            <p><strong>Important:</strong> If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
            <p>This link will expire in 24 hours.</p>
        </div>
        
        <p>Best regards,<br>The Banbury Team</p>
    </div>
    <div class="footer">
        <p>This email was sent because a password reset was requested for your Banbury account.</p>
    </div>
</body>
</html>
            """.strip()
            
            # Create the email message
            message = Mail(
                from_email=From(self.from_email, self.from_name),
                to_emails=To(user_email),
                subject=Subject(subject_text),
                plain_text_content=PlainTextContent(plain_text_content),
                html_content=HtmlContent(html_content)
            )
            
            # Add BCC to copy yourself on all emails
            if self.bcc_email and self.bcc_email != user_email:
                message.bcc = Bcc(self.bcc_email)
            
            # Send the email
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Password reset email sent successfully to {user_email}")
                return True
            else:
                logger.error(f"Failed to send password reset email to {user_email}. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending password reset email to {user_email}: {str(e)}")
            return False


# Global instance of the email service
email_service = EmailService()
