"""
Users app admin configuration
ULTRA PRO MAX VERSIYA
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from .models import CustomUser, EmailVerification, PasswordResetToken, LoginHistory


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin panel configuration for CustomUser"""
    
    list_display = (
        'username', 'email', 'first_name', 'last_name', 
        'is_active', 'email_verified', 'is_staff', 
        'date_joined', 'last_activity'
    )
    
    list_filter = (
        'is_staff', 'is_superuser', 'is_active', 'email_verified',
        'language', 'default_currency', 'country',
        'date_joined', 'last_activity'
    )
    
    search_fields = (
        'username', 'email', 'first_name', 'last_name', 
        'phone', 'uuid'
    )
    
    ordering = ('-date_joined',)
    
    readonly_fields = (
        'uuid', 'last_login', 'date_joined', 'last_activity',
        'login_count', 'last_login_ip', 'created_from_ip',
    )
    
    fieldsets = (
        (_('Asosiy maʼlumotlar'), {
            'fields': (
                'uuid', 'username', 'password',
                'first_name', 'last_name', 'email', 'phone'
            )
        }),
        (_('Profil maʼlumotlari'), {
            'fields': (
                'profile_image', 'date_of_birth', 'country', 
                'bio', 'language', 'default_currency', 'timezone'
            )
        }),
        (_('Tasdiqlash holati'), {
            'fields': (
                'email_verified', 'phone_verified',
            )
        }),
        (_('Xabarnoma sozlamalari'), {
            'fields': (
                'email_notifications', 'push_notifications', 
                'marketing_emails',
            )
        }),
        (_('Faollik'), {
            'fields': (
                'last_login', 'last_activity', 'login_count',
                'last_login_ip', 'created_from_ip',
            )
        }),
        (_('Premium'), {
            'fields': (
                'is_premium', 'premium_expires_at',
            )
        }),
        (_('Xavfsizlik'), {
            'fields': (
                'two_factor_enabled',
            )
        }),
        (_('Ruxsatlar'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        (_('Yaratilgan vaqt'), {
            'fields': ('date_joined',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2',
                'first_name', 'last_name', 'phone', 'is_active', 'is_staff'
            ),
        }),
    )
    
    actions = ['activate_users', 'deactivate_users', 'resend_verification']
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request, 
            _("%(count)d foydalanuvchi faollashtirildi") % {'count': updated},
            messages.SUCCESS
        )
    activate_users.short_description = _("Tanlangan foydalanuvchilarni faollashtirish")
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request, 
            _("%(count)d foydalanuvchi deaktivatsiya qilindi") % {'count': updated},
            messages.WARNING
        )
    deactivate_users.short_description = _("Tanlangan foydalanuvchilarni deaktivatsiya qilish")
    
    def resend_verification(self, request, queryset):
        """Resend verification email"""
        from .views import resend_verification_email
        
        count = 0
        for user in queryset:
            # Simulate request for the view
            class FakeRequest:
                def __init__(self):
                    self.method = 'POST'
                    self.user = user
                    self.META = {'HTTP_HOST': 'localhost:8000'}
            
            resend_verification_email(FakeRequest())
            count += 1
        
        self.message_user(
            request, 
            _("%(count)d foydalanuvchiga tasdiqlash emaili yuborildi") % {'count': count},
            messages.SUCCESS
        )
    resend_verification.short_description = _("Tasdiqlash emailini qayta yuborish")
    
    def email_verified_display(self, obj):
        """Display email verification status with icon"""
        if obj.email_verified:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                _('Tasdiqlangan')
            )
        return format_html(
            '<span style="color: red;">✗ {}</span>',
            _('Tasdiqlanmagan')
        )
    email_verified_display.short_description = _('Email tasdiqlash')
    
    def view_on_site(self, obj):
        """View user on site link"""
        return reverse('users:profile')
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            # Add related fields if needed
        )


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """Admin panel for EmailVerification"""
    
    list_display = (
        'user', 'token_truncated', 'created_at', 
        'expires_at', 'is_used', 'is_expired_display'
    )
    
    list_filter = (
        'is_used', 'created_at', 'expires_at',
    )
    
    search_fields = (
        'user__username', 'user__email', 'token',
        'ip_address', 'uuid'
    )
    
    readonly_fields = (
        'uuid', 'created_at', 'expires_at',
        'token', 'ip_address', 'user_agent'
    )
    
    fieldsets = (
        (_('Asosiy maʼlumotlar'), {
            'fields': (
                'uuid', 'user', 'token',
            )
        }),
        (_('Holat'), {
            'fields': (
                'is_used', 'created_at', 'expires_at',
            )
        }),
        (_('Texnik maʼlumotlar'), {
            'fields': (
                'ip_address', 'user_agent',
            )
        }),
    )
    
    def token_truncated(self, obj):
        """Display truncated token"""
        return f"{obj.token[:20]}..." if len(obj.token) > 20 else obj.token
    token_truncated.short_description = _('Token')
    
    def is_expired_display(self, obj):
        """Display expiry status"""
        if obj.is_expired():
            return format_html(
                '<span style="color: red;">{} ✓</span>',
                _('Muddati o‘tgan')
            )
        return format_html(
            '<span style="color: green;">{} ✗</span>',
            _('Faol')
        )
    is_expired_display.short_description = _('Muddati')


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin panel for PasswordResetToken"""
    
    list_display = (
        'user', 'token_truncated', 'created_at', 
        'expires_at', 'is_used', 'is_expired_display'
    )
    
    list_filter = (
        'is_used', 'created_at', 'expires_at',
    )
    
    search_fields = (
        'user__username', 'user__email', 'token',
        'ip_address', 'uuid'
    )
    
    readonly_fields = (
        'uuid', 'created_at', 'expires_at',
        'token', 'ip_address', 'user_agent'
    )
    
    fieldsets = (
        (_('Asosiy maʼlumotlar'), {
            'fields': (
                'uuid', 'user', 'token',
            )
        }),
        (_('Holat'), {
            'fields': (
                'is_used', 'created_at', 'expires_at',
            )
        }),
        (_('Texnik maʼlumotlar'), {
            'fields': (
                'ip_address', 'user_agent',
            )
        }),
    )
    
    def token_truncated(self, obj):
        """Display truncated token"""
        return f"{obj.token[:20]}..." if len(obj.token) > 20 else obj.token
    token_truncated.short_description = _('Token')
    
    def is_expired_display(self, obj):
        """Display expiry status"""
        if obj.is_expired():
            return format_html(
                '<span style="color: red;">{} ✓</span>',
                _('Muddati o‘tgan')
            )
        return format_html(
            '<span style="color: green;">{} ✗</span>',
            _('Faol')
        )
    is_expired_display.short_description = _('Muddati')


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    """Admin panel for LoginHistory"""
    
    list_display = (
        'user', 'username', 'status_display', 
        'ip_address', 'device', 'created_at'
    )
    
    list_filter = (
        'status', 'created_at', 'device', 'browser',
    )
    
    search_fields = (
        'user__username', 'user__email', 'username', 'email',
        'ip_address', 'location', 'device', 'browser'
    )
    
    readonly_fields = (
        'uuid', 'created_at', 'user', 'username', 'email',
        'status', 'ip_address', 'user_agent', 'location',
        'device', 'browser'
    )
    
    fieldsets = (
        (_('Kirish maʼlumotlari'), {
            'fields': (
                'user', 'username', 'email', 'status',
            )
        }),
        (_('Texnik maʼlumotlar'), {
            'fields': (
                'ip_address', 'location', 'device', 'browser',
                'user_agent'
            )
        }),
        (_('Vaqt'), {
            'fields': ('created_at',)
        }),
    )
    
    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'success': 'green',
            'failed': 'orange',
            'locked': 'red',
        }
        color = colors.get(obj.status, 'gray')
        
        status_text = dict(LoginHistory.LoginStatus.choices).get(obj.status, obj.status)
        return format_html(
            '<span style="color: {};">● {}</span>',
            color, status_text
        )
    status_display.short_description = _('Holat')
    
    def has_add_permission(self, request):
        """Disable adding login history manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing login history"""
        return False