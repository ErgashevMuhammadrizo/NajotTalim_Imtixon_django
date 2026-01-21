"""
Users app signals - Signal handlers for user events
ULTRA PRO MAX VERSIYA
"""

import logging
from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver
from django.utils import translation
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import CustomUser, LoginHistory, EmailVerification, PasswordResetToken

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def set_user_language(sender, instance, created, **kwargs):
    """Set user language preference"""
    if created and instance.language:
        translation.activate(instance.language)


@receiver(post_save, sender=CustomUser)
def send_welcome_email(sender, instance, created, **kwargs):
    """Send welcome email to new user"""
    if created and instance.email:
        try:
            subject = "Kirim-Chiqim - Xush kelibsiz!"
            message = render_to_string('users/emails/welcome_email.html', {
                'user': instance,
                'site_name': 'Kirim-Chiqim',
            })
            
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                html_message=message,
                fail_silently=True,
            )
            logger.info(f"Welcome email sent to {instance.email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")


@receiver(pre_save, sender=CustomUser)
def track_user_changes(sender, instance, **kwargs):
    """Track user changes for auditing"""
    if instance.pk:
        try:
            old_user = CustomUser.objects.get(pk=instance.pk)
            
            # Track email changes
            if old_user.email != instance.email:
                logger.info(f"User {instance.username} changed email: {old_user.email} -> {instance.email}")
                instance.email_verified = False
            
            # Track phone changes
            if old_user.phone != instance.phone:
                logger.info(f"User {instance.username} changed phone: {old_user.phone} -> {instance.phone}")
                instance.phone_verified = False
            
        except CustomUser.DoesNotExist:
            pass


@receiver(post_save, sender=LoginHistory)
def update_user_login_stats(sender, instance, created, **kwargs):
    """Update user login statistics"""
    if created and instance.user and instance.status == 'success':
        try:
            user = instance.user
            user.login_count += 1
            user.last_login_ip = instance.ip_address
            user.save(update_fields=['login_count', 'last_login_ip'])
        except Exception as e:
            logger.error(f"Failed to update login stats: {e}")


@receiver(pre_delete, sender=CustomUser)
def cleanup_user_data(sender, instance, **kwargs):
    """Cleanup user data before deletion"""
    try:
        # Log deletion
        logger.info(f"User {instance.username} ({instance.email}) is being deleted")
        
        # You can add additional cleanup logic here
        # For example, anonymize data instead of deletion
        
    except Exception as e:
        logger.error(f"Error in user cleanup: {e}")


@receiver(post_delete, sender=EmailVerification)
def log_email_verification_deletion(sender, instance, **kwargs):
    """Log email verification token deletion"""
    logger.info(f"Email verification token deleted for user {instance.user.username}")


@receiver(post_delete, sender=PasswordResetToken)
def log_password_reset_deletion(sender, instance, **kwargs):
    """Log password reset token deletion"""
    logger.info(f"Password reset token deleted for user {instance.user.username}")


# User activity signals (to be connected from other apps)
def user_created_transaction(sender, user, **kwargs):
    """Signal when user creates a transaction"""
    logger.info(f"User {user.username} created a transaction")


def user_updated_profile(sender, user, changes, **kwargs):
    """Signal when user updates profile"""
    logger.info(f"User {user.username} updated profile: {changes}")


def user_changed_password(sender, user, **kwargs):
    """Signal when user changes password"""
    logger.info(f"User {user.username} changed password")