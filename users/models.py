"""
Users app models - Custom User and related models
ULTRA PRO MAX VERSIYA
"""

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from django.core.validators import RegexValidator
from django.utils import timezone
from django.conf import settings


class CustomUser(AbstractUser):
    """
    Custom User model with extended fields
    """
    
    class LanguageChoices(models.TextChoices):
        UZBEK = 'uz', _('O‘zbek')
        RUSSIAN = 'ru', _('Русский')
        ENGLISH = 'en', _('English')
    
    class CurrencyChoices(models.TextChoices):
        UZS = 'UZS', 'UZS (Soʻm)'
        USD = 'USD', 'USD ($)'
        EUR = 'EUR', 'EUR (€)'
        RUB = 'RUB', 'RUB (₽)'
    
    # ========== IDENTIFICATION ==========
    uuid = models.UUIDField(
        _('UUID'),
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    # ========== CONTACT INFORMATION ==========
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_("Telefon raqami formati: '+998901234567'. 9-15 ta raqam.")
    )
    phone = models.CharField(
        _('Telefon raqam'),
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        unique=True,
        db_index=True
    )
    
    # ========== PREFERENCES ==========
    language = models.CharField(
        _('Til'),
        max_length=2,
        choices=LanguageChoices.choices,
        default=LanguageChoices.UZBEK
    )
    
    default_currency = models.CharField(
        _('Asosiy valyuta'),
        max_length=3,
        choices=CurrencyChoices.choices,
        default=CurrencyChoices.UZS
    )
    
    timezone = models.CharField(
        _('Vaqt mintaqasi'),
        max_length=50,
        default='Asia/Tashkent',
        choices=[
            ('Asia/Tashkent', 'Asia/Tashkent (Uzbekistan)'),
            ('Europe/Moscow', 'Europe/Moscow (Russia)'),
            ('America/New_York', 'America/New_York (USA)'),
            ('Europe/London', 'Europe/London (UK)'),
        ]
    )
    
    country = CountryField(
        _('Davlat'),
        blank=True,
        null=True
    )
    
    # ========== VERIFICATION STATUS ==========
    email_verified = models.BooleanField(
        _('Email tasdiqlangan'),
        default=False,
        db_index=True
    )
    
    phone_verified = models.BooleanField(
        _('Telefon tasdiqlangan'),
        default=False,
        db_index=True
    )
    
    # ========== NOTIFICATION PREFERENCES ==========
    email_notifications = models.BooleanField(
        _('Email xabarnomalar'),
        default=True
    )
    
    push_notifications = models.BooleanField(
        _('Push xabarnomalar'),
        default=True
    )
    
    marketing_emails = models.BooleanField(
        _('Marketing email lari'),
        default=False
    )
    
    # ========== PROFILE INFORMATION ==========
    date_of_birth = models.DateField(
        _('Tug‘ilgan sana'),
        blank=True,
        null=True,
        db_index=True
    )
    
    profile_image = models.ImageField(
        _('Profil rasmi'),
        upload_to='profile_images/%Y/%m/%d/',
        blank=True,
        null=True,
        max_length=500
    )
    
    bio = models.TextField(
        _('Bio'),
        max_length=500,
        blank=True,
        null=True
    )
    
    # ========== ACTIVITY TRACKING ==========
    last_activity = models.DateTimeField(
        _('Oxirgi faollik'),
        auto_now=True,
        db_index=True
    )
    
    last_login_ip = models.GenericIPAddressField(
        _('Oxirgi login IP'),
        blank=True,
        null=True
    )
    
    login_count = models.PositiveIntegerField(
        _('Loginlar soni'),
        default=0
    )
    
    # ========== ACCOUNT STATUS ==========
    is_premium = models.BooleanField(
        _('Premium foydalanuvchi'),
        default=False,
        db_index=True
    )
    
    premium_expires_at = models.DateTimeField(
        _('Premium muddati'),
        blank=True,
        null=True
    )
    
    # ========== SECURITY ==========
    two_factor_enabled = models.BooleanField(
        _('Ikki faktorli autentifikatsiya'),
        default=False
    )
    
    # ========== META INFORMATION ==========
    profile_completed = models.BooleanField(
        _('Profil to‘ldirilgan'),
        default=False,
        db_index=True
    )
    
    created_from_ip = models.GenericIPAddressField(
        _('Yaratilgan IP'),
        blank=True,
        null=True
    )
    
    # ========== METHODS ==========
    
    class Meta:
        verbose_name = _('Foydalanuvchi')
        verbose_name_plural = _('Foydalanuvchilar')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['phone'], name='idx_user_phone'),
            models.Index(fields=['is_active', 'email_verified'], name='idx_user_active'),
            models.Index(fields=['date_joined'], name='idx_user_date_joined'),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_full_name() or self.email})"
    
    def save(self, *args, **kwargs):
        """Override save to update profile completion"""
        # Update profile completion
        self.profile_completed = (
            bool(self.first_name) and 
            bool(self.last_name) and 
            bool(self.email) and 
            bool(self.phone) and 
            bool(self.date_of_birth)
        )
        
        # Call parent save
        super().save(*args, **kwargs)
    
    def get_display_name(self):
        """Get display name for the user"""
        if self.get_full_name():
            return self.get_full_name()
        return self.username or self.email.split('@')[0]
    
    def get_initials(self):
        """Get user initials for avatar"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        elif self.username:
            return self.username[0].upper()
        return "U"
    
    def get_avatar_color(self):
        """Get consistent color for user avatar"""
        colors = [
            '#1abc9c', '#2ecc71', '#3498db', '#9b59b6',
            '#e74c3c', '#f39c12', '#d35400', '#16a085',
        ]
        hash_value = sum(ord(char) for char in self.username or self.email)
        return colors[hash_value % len(colors)]
    
    def is_premium_active(self):
        """Check if premium subscription is active"""
        if not self.is_premium:
            return False
        if self.premium_expires_at:
            return timezone.now() < self.premium_expires_at
        return True
    
    def get_statistics(self):
        """Get user statistics"""
        # This will be populated by signals or other apps
        return {
            'total_income': 0,
            'total_expense': 0,
            'accounts_count': 0,
            'transactions_count': 0,
        }


class EmailVerification(models.Model):
    """Email verification token model"""
    
    uuid = models.UUIDField(
        _('UUID'),
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='email_verifications',
        verbose_name=_('Foydalanuvchi')
    )
    
    token = models.CharField(
        _('Token'),
        max_length=255,
        unique=True,
        db_index=True
    )
    
    created_at = models.DateTimeField(
        _('Yaratilgan vaqt'),
        auto_now_add=True,
        db_index=True
    )
    
    expires_at = models.DateTimeField(
        _('Muddati'),
        db_index=True
    )
    
    is_used = models.BooleanField(
        _('Ishlatilgan'),
        default=False,
        db_index=True
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP manzil'),
        blank=True,
        null=True
    )
    
    user_agent = models.TextField(
        _('User agent'),
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name = _('Email tasdiqlash')
        verbose_name_plural = _('Email tasdiqlashlar')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token', 'is_used'], name='idx_email_verify_token'),
            models.Index(fields=['user', 'is_used'], name='idx_email_verify_user'),
            models.Index(fields=['expires_at'], name='idx_email_verify_expires'),
        ]
    
    def __str__(self):
        return f"Email verification for {self.user.email}"
    
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid"""
        return not self.is_used and not self.is_expired()


class PasswordResetToken(models.Model):
    """Password reset token model"""
    
    uuid = models.UUIDField(
        _('UUID'),
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name=_('Foydalanuvchi')
    )
    
    token = models.CharField(
        _('Token'),
        max_length=255,
        unique=True,
        db_index=True
    )
    
    created_at = models.DateTimeField(
        _('Yaratilgan vaqt'),
        auto_now_add=True,
        db_index=True
    )
    
    expires_at = models.DateTimeField(
        _('Muddati'),
        db_index=True
    )
    
    is_used = models.BooleanField(
        _('Ishlatilgan'),
        default=False,
        db_index=True
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP manzil'),
        blank=True,
        null=True
    )
    
    user_agent = models.TextField(
        _('User agent'),
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name = _('Parol tiklash tokeni')
        verbose_name_plural = _('Parol tiklash tokenlari')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token', 'is_used'], name='idx_pwd_reset_token'),
            models.Index(fields=['user', 'is_used'], name='idx_pwd_reset_user'),
            models.Index(fields=['expires_at'], name='idx_pwd_reset_expires'),
        ]
    
    def __str__(self):
        return f"Password reset for {self.user.email}"
    
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid"""
        return not self.is_used and not self.is_expired()


class LoginHistory(models.Model):
    """User login history model"""
    
    class LoginStatus(models.TextChoices):
        SUCCESS = 'success', _('Muvaffaqiyatli')
        FAILED = 'failed', _('Muvaffaqiyatsiz')
        LOCKED = 'locked', _('Bloklangan')
    
    uuid = models.UUIDField(
        _('UUID'),
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='login_history',
        verbose_name=_('Foydalanuvchi'),
        blank=True,
        null=True  # For failed attempts where user is not identified
    )
    
    username = models.CharField(
        _('Username'),
        max_length=150,
        blank=True,
        null=True
    )
    
    email = models.EmailField(
        _('Email'),
        blank=True,
        null=True
    )
    
    status = models.CharField(
        _('Holat'),
        max_length=10,
        choices=LoginStatus.choices,
        default=LoginStatus.SUCCESS,
        db_index=True
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP manzil'),
        blank=True,
        null=True
    )
    
    user_agent = models.TextField(
        _('User agent'),
        blank=True,
        null=True
    )
    
    location = models.CharField(
        _('Lokatsiya'),
        max_length=255,
        blank=True,
        null=True
    )
    
    device = models.CharField(
        _('Qurilma'),
        max_length=255,
        blank=True,
        null=True
    )
    
    browser = models.CharField(
        _('Brauzer'),
        max_length=255,
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(
        _('Yaratilgan vaqt'),
        auto_now_add=True,
        db_index=True
    )
    
    class Meta:
        verbose_name = _('Login tarixi')
        verbose_name_plural = _('Login tarixlari')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status'], name='idx_login_history_user'),
            models.Index(fields=['ip_address'], name='idx_login_history_ip'),
            models.Index(fields=['created_at', 'status'], name='idx_login_history_date'),
        ]
    
    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.status} - {self.created_at}"
        return f"{self.username} - {self.status} - {self.created_at}"