import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails via SMTP."""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS
        
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def send_verification_email(
        self,
        to_email: str,
        verification_code: Optional[str] = None
    ) -> bool:
        """
        Send email verification email with either a URL or code.
        
        Args:
            to_email: Recipient email address
            verification_url: URL for email verification
            verification_code: Optional verification code (alternative to URL)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        app_name = settings.APP_NAME

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your Email</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Verify Your Email</h1>
            </div>
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0;">
                <p style="font-size: 16px; margin-bottom: 20px;">Hello,</p>
                <p style="font-size: 16px; margin-bottom: 20px;">
                    Thank you for registering with {app_name}! Please verify your email address by entering the verification code below:
                </p>
                <div style="background: white; padding: 20px; border-radius: 8px; border: 2px solid #667eea; text-align: center; margin: 30px 0;">
                    <p style="font-size: 14px; color: #666; margin: 0 0 10px 0;">Your verification code is:</p>
                    <p style="font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 5px; margin: 0;">{verification_code}</p>
                </div>
                <p style="font-size: 14px; color: #666; margin-top: 20px;">
                    This code will expire in 24 hours. If you didn't create an account with {app_name}, please ignore this email.
                </p>
            </div>
            <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #999; font-size: 12px;">
                <p>© {app_name}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Verify Your Email
        
        Hello,
        
        Thank you for registering with {app_name}! Please verify your email address by entering the verification code below:
        
        Verification Code: {verification_code}
        
        This code will expire in 24 hours. If you didn't create an account with {app_name}, please ignore this email.
        """

        return await self.send_email(
            to_email=to_email,
            subject=f"Verify Your {app_name} Email Address",
            html_content=html_content,
            text_content=text_content
        )

# Global email service instance
email_service = EmailService()

