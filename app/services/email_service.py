from typing import List, Optional

import resend
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class EmailService:
    def __init__(self):
        if settings.RESEND_API_KEY:
            resend.api_key = settings.RESEND_API_KEY
            self.enabled = True
        else:
            self.enabled = False
            logger.warning("Resend API key not configured - email sending disabled")

    async def send_verification_email(
        self, to_email: str, username: str, verification_token: str
    ) -> bool:
        """Send email verification email"""
        if not self.enabled:
            logger.warning(
                f"Cannot send verification email to {to_email} - email service disabled"
            )
            return False

        try:
            # In a real app, you'd have proper HTML templates
            verification_url = f"{settings.ALLOWED_ORIGINS[0] if settings.ALLOWED_ORIGINS else 'http://localhost:3000'}/verify-email?token={verification_token}"

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Welcome to DevPocket!</h2>
                <p>Hi {username},</p>
                <p>Thank you for signing up! Please verify your email address by clicking the link below:</p>
                <p style="margin: 20px 0;">
                    <a href="{verification_url}"
                       style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
                        Verify Email Address
                    </a>
                </p>
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{verification_url}</p>
                <p>This verification link will expire in 24 hours.</p>
                <p>Best regards,<br>The DevPocket Team</p>
            </div>
            """

            text_content = f"""
            Welcome to DevPocket!

            Hi {username},

            Thank you for signing up! Please verify your email address by visiting:
            {verification_url}

            This verification link will expire in 24 hours.

            Best regards,
            The DevPocket Team
            """

            response = resend.emails.send(
                {
                    "from": settings.EMAIL_FROM,
                    "to": [to_email],
                    "subject": "Verify your DevPocket account",
                    "html": html_content,
                    "text": text_content,
                }
            )

            logger.info(
                f"Verification email sent successfully to {to_email}",
                extra={"email_id": response.get("id"), "recipient": to_email},
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send verification email to {to_email}: {str(e)}")
            return False

    async def send_password_reset_email(
        self, to_email: str, username: str, reset_token: str
    ) -> bool:
        """Send password reset email"""
        if not self.enabled:
            logger.warning(
                f"Cannot send password reset email to {to_email} - email service disabled"
            )
            return False

        try:
            reset_url = f"{settings.ALLOWED_ORIGINS[0] if settings.ALLOWED_ORIGINS else 'http://localhost:3000'}/reset-password?token={reset_token}"

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Password Reset Request</h2>
                <p>Hi {username},</p>
                <p>You requested to reset your password for your DevPocket account.</p>
                <p>Click the link below to reset your password:</p>
                <p style="margin: 20px 0;">
                    <a href="{reset_url}"
                       style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
                        Reset Password
                    </a>
                </p>
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{reset_url}</p>
                <p>This reset link will expire in 1 hour.</p>
                <p>If you didn't request this password reset, you can safely ignore this email.</p>
                <p>Best regards,<br>The DevPocket Team</p>
            </div>
            """

            text_content = f"""
            Password Reset Request

            Hi {username},

            You requested to reset your password for your DevPocket account.

            Visit this link to reset your password:
            {reset_url}

            This reset link will expire in 1 hour.

            If you didn't request this password reset, you can safely ignore this email.

            Best regards,
            The DevPocket Team
            """

            response = resend.emails.send(
                {
                    "from": settings.EMAIL_FROM,
                    "to": [to_email],
                    "subject": "Reset your DevPocket password",
                    "html": html_content,
                    "text": text_content,
                }
            )

            logger.info(
                f"Password reset email sent successfully to {to_email}",
                extra={"email_id": response.get("id"), "recipient": to_email},
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {str(e)}")
            return False

    async def send_welcome_email(self, to_email: str, username: str) -> bool:
        """Send welcome email after successful verification"""
        if not self.enabled:
            logger.warning(
                f"Cannot send welcome email to {to_email} - email service disabled"
            )
            return False

        try:
            dashboard_url = f"{settings.ALLOWED_ORIGINS[0] if settings.ALLOWED_ORIGINS else 'http://localhost:3000'}/dashboard"

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Welcome to DevPocket! 🎉</h2>
                <p>Hi {username},</p>
                <p>Your email has been successfully verified! You're now ready to start using DevPocket.</p>
                <p>DevPocket is your mobile-first cloud IDE that lets you code anywhere, anytime.</p>
                <h3>What you can do now:</h3>
                <ul>
                    <li>Create development environments</li>
                    <li>Access a full terminal in your browser</li>
                    <li>Code with your favorite tools and languages</li>
                    <li>Sync your work across all devices</li>
                </ul>
                <p style="margin: 20px 0;">
                    <a href="{dashboard_url}"
                       style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
                        Go to Dashboard
                    </a>
                </p>
                <p>If you have any questions, feel free to reach out to us!</p>
                <p>Happy coding!<br>The DevPocket Team</p>
            </div>
            """

            text_content = f"""
            Welcome to DevPocket!

            Hi {username},

            Your email has been successfully verified! You're now ready to start using DevPocket.

            DevPocket is your mobile-first cloud IDE that lets you code anywhere, anytime.

            What you can do now:
            - Create development environments
            - Access a full terminal in your browser
            - Code with your favorite tools and languages
            - Sync your work across all devices

            Visit your dashboard: {dashboard_url}

            If you have any questions, feel free to reach out to us!

            Happy coding!
            The DevPocket Team
            """

            response = resend.emails.send(
                {
                    "from": settings.EMAIL_FROM,
                    "to": [to_email],
                    "subject": "Welcome to DevPocket! Your account is ready 🎉",
                    "html": html_content,
                    "text": text_content,
                }
            )

            logger.info(
                f"Welcome email sent successfully to {to_email}",
                extra={"email_id": response.get("id"), "recipient": to_email},
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send welcome email to {to_email}: {str(e)}")
            return False


# Singleton instance
email_service = EmailService()
