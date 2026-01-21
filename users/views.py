"""
Users app views - Authentication and User Management
ULTRA PRO MAX VERSIYA
"""

import uuid
import logging
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse
from django.db import transaction
from django.db.models import Q

from expenses import models

from .forms import (
    CustomUserCreationForm, LoginForm, ProfileUpdateForm,
    PasswordResetForm, PasswordResetConfirmForm
)
from .models import CustomUser, EmailVerification, PasswordResetToken

# Logger setup
logger = logging.getLogger(__name__)

# Constants
TOKEN_EXPIRY_HOURS = 24
PASSWORD_RESET_EXPIRY_HOURS = 1
EMAIL_SUBJECT_PREFIX = "Kirim-Chiqim | "


# ==================== HELPER FUNCTIONS ====================

def get_current_language_prefix():
    """Get current language prefix for URLs"""
    from django.utils import translation
    lang_code = translation.get_language()
    return lang_code if lang_code in ['uz', 'ru', 'en'] else 'uz'


def build_absolute_url(request, path):
    """Build absolute URL with proper language prefix"""
    lang_prefix = get_current_language_prefix()
    return request.build_absolute_uri(f'/{lang_prefix}{path}')


def send_template_email(subject, template_name, context, recipient_list):
    """Send email using HTML template"""
    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=EMAIL_SUBJECT_PREFIX + subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email sent to {recipient_list}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        return False


def create_email_verification(user):
    """Create email verification token"""
    try:
        # Delete old unused tokens
        EmailVerification.objects.filter(
            user=user, 
            is_used=False,
            expires_at__lt=timezone.now()
        ).delete()
        
        # Create new token
        token = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
        
        verification = EmailVerification.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        logger.info(f"Email verification created for user {user.username}")
        return verification
    except Exception as e:
        logger.error(f"Failed to create email verification: {e}")
        return None


def create_password_reset_token(user):
    """Create password reset token"""
    try:
        # Delete old unused tokens
        PasswordResetToken.objects.filter(
            user=user, 
            is_used=False,
            expires_at__lt=timezone.now()
        ).delete()
        
        # Create new token
        token = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(hours=PASSWORD_RESET_EXPIRY_HOURS)
        
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        logger.info(f"Password reset token created for user {user.username}")
        return reset_token
    except Exception as e:
        logger.error(f"Failed to create password reset token: {e}")
        return None


# ==================== AUTHENTICATION VIEWS ====================

@csrf_protect
def register_view(request):
    """
    User registration view with email verification
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save user but keep inactive
                    user = form.save(commit=False)
                    user.is_active = False
                    user.email_verified = False
                    user.save()
                    
                    # Create verification token
                    verification = create_email_verification(user)
                    if not verification:
                        messages.error(request, _("Tasdiqlash tokenini yaratishda xatolik"))
                        return render(request, 'users/register.html', {'form': form})
                    
                    # Send verification email
                    verification_url = build_absolute_url(
                        request, 
                        f"/verify-email/{verification.token}/"
                    )
                    
                    email_sent = send_template_email(
                        subject=_("Emailingizni tasdiqlang"),
                        template_name='users/verification_email.html',
                        context={
                            'user': user,
                            'verification_url': verification_url,
                            'expires_in_hours': TOKEN_EXPIRY_HOURS,
                        },
                        recipient_list=[user.email]
                    )
                    
                    if email_sent:
                        messages.success(
                            request,
                            _("Ro'yxatdan muvaffaqiyatli o'tdingiz! "
                              "Iltimos, emailingizni tasdiqlang.")
                        )
                        logger.info(f"User registered: {user.username}")
                        return redirect('users:register_success')
                    else:
                        messages.warning(
                            request,
                            _("Ro'yxatdan o'tdingiz, lekin email yuborishda xatolik. "
                              "Iltimos, qayta urinib ko'ring.")
                        )
                        return redirect('users:login')
                        
            except Exception as e:
                logger.error(f"Registration error: {e}")
                messages.error(
                    request,
                    _("Ro'yxatdan o'tishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
                )
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/register.html', {'form': form})


def register_success_view(request):
    """Registration success page"""
    return render(request, 'users/register_success.html')


@csrf_protect
def login_view(request):
    """
    User login view with remember me functionality
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    next_url = request.GET.get('next', '')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', True)
            
            # Try to authenticate with username or email
            user = None
            if '@' in identifier:
                try:
                    user_obj = CustomUser.objects.get(email=identifier)
                    user = authenticate(request, username=user_obj.username, password=password)
                except CustomUser.DoesNotExist:
                    pass
            else:
                user = authenticate(request, username=identifier, password=password)
            
            if user is not None:
                if not user.is_active:
                    messages.error(
                        request,
                        _("Hisobingiz faol emas. Iltimos, emailingizni tasdiqlang.")
                    )
                    return redirect('users:login')
                
                # Login user
                login(request, user)
                
                # Update last login
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                # Set session expiry
                if not remember_me:
                    request.session.set_expiry(0)  # Browser session
                else:
                    request.session.set_expiry(1209600)  # 2 weeks
                
                messages.success(request, _("Xush kelibsiz, {}!").format(user.get_display_name()))
                logger.info(f"User logged in: {user.username}")
                
                # Redirect to next URL or dashboard
                return redirect(next_url if next_url else 'dashboard')
            else:
                messages.error(request, _("Login yoki parol noto'g'ri"))
                logger.warning(f"Failed login attempt for: {identifier}")
    else:
        form = LoginForm()
    
    return render(request, 'users/login.html', {
        'form': form,
        'next': next_url
    })


@login_required
def logout_view(request):
    """
    User logout view
    """
    username = request.user.username
    logout(request)
    messages.success(request, _("Siz tizimdan chiqdingiz"))
    logger.info(f"User logged out: {username}")
    return redirect('home')


# ==================== EMAIL VERIFICATION ====================

def verify_email_view(request, token):
    """
    Verify user email with token
    """
    try:
        verification = get_object_or_404(
            EmailVerification.objects.select_related('user'),
            token=token,
            is_used=False
        )
        
        # Check if token is expired
        if timezone.now() > verification.expires_at:
            verification.delete()
            messages.error(request, _("Tasdiqlash havolasining muddati o'tgan"))
            return redirect('users:login')
        
        # Activate user
        user = verification.user
        user.is_active = True
        user.email_verified = True
        user.save(update_fields=['is_active', 'email_verified'])
        
        # Mark token as used
        verification.is_used = True
        verification.save(update_fields=['is_used'])
        
        messages.success(
            request,
            _("Email muvaffaqiyatli tasdiqlandi! Endi hisobingizga kirishingiz mumkin.")
        )
        logger.info(f"Email verified for user: {user.username}")
        
        return redirect('users:login')
        
    except Http404:
        messages.error(request, _("Yaroqsiz yoki eskirgan tasdiqlash havolasi"))
        return redirect('home')


@login_required
def resend_verification_email(request):
    """
    Resend verification email for logged-in user
    """
    user = request.user
    
    if user.email_verified:
        messages.info(request, _("Sizning emailingiz allaqachon tasdiqlangan"))
        return redirect('users:profile')
    
    verification = create_email_verification(user)
    if verification:
        verification_url = build_absolute_url(
            request, 
            f"/verify-email/{verification.token}/"
        )
        
        email_sent = send_template_email(
            subject=_("Emailingizni tasdiqlang"),
            template_name='users/verification_email.html',
            context={
                'user': user,
                'verification_url': verification_url,
                'expires_in_hours': TOKEN_EXPIRY_HOURS,
            },
            recipient_list=[user.email]
        )
        
        if email_sent:
            messages.success(request, _("Tasdiqlash emaili qayta yuborildi"))
        else:
            messages.error(request, _("Email yuborishda xatolik"))
    
    return redirect('users:profile')


# ==================== PASSWORD MANAGEMENT ====================

@csrf_protect
def password_reset_view(request):
    """
    Request password reset
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            try:
                user = CustomUser.objects.get(email=email, is_active=True)
                
                # Create reset token
                reset_token = create_password_reset_token(user)
                if reset_token:
                    reset_url = build_absolute_url(
                        request, 
                        f"/password-reset/{reset_token.token}/"
                    )
                    
                    email_sent = send_template_email(
                        subject=_("Parolni tiklash"),
                        template_name='users/password_reset_email.html',
                        context={
                            'user': user,
                            'reset_url': reset_url,
                            'expires_in_hours': PASSWORD_RESET_EXPIRY_HOURS,
                        },
                        recipient_list=[user.email]
                    )
                    
                    if email_sent:
                        logger.info(f"Password reset requested for: {user.email}")
                
                # Always show success message (security best practice)
                messages.success(
                    request,
                    _("Agar bu email ro'yxatdan o'tgan bo'lsa, "
                      "parol tiklash havolasi yuborildi.")
                )
                
            except CustomUser.DoesNotExist:
                # Log but don't show error to user (security)
                logger.info(f"Password reset attempt for non-existent email: {email}")
                messages.success(
                    request,
                    _("Agar bu email ro'yxatdan o'tgan bo'lsa, "
                      "parol tiklash havolasi yuborildi.")
                )
            
            return redirect('users:login')
    else:
        form = PasswordResetForm()
    
    return render(request, 'users/password_reset.html', {'form': form})


@csrf_protect
def password_reset_confirm_view(request, token):
    """
    Confirm password reset with token
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    try:
        reset_token = get_object_or_404(
            PasswordResetToken.objects.select_related('user'),
            token=token,
            is_used=False
        )
        
        # Check if token is expired
        if timezone.now() > reset_token.expires_at:
            reset_token.delete()
            messages.error(request, _("Parol tiklash havolasining muddati o'tgan"))
            return redirect('users:password_reset')
        
        user = reset_token.user
        
        if request.method == 'POST':
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                # Update password
                new_password = form.cleaned_data['new_password1']
                user.set_password(new_password)
                user.save(update_fields=['password'])
                
                # Mark token as used
                reset_token.is_used = True
                reset_token.save(update_fields=['is_used'])
                
                messages.success(request, _("Parol muvaffaqiyatli o'zgartirildi"))
                logger.info(f"Password reset completed for user: {user.username}")
                
                return redirect('users:login')
        else:
            form = PasswordResetConfirmForm()
        
        return render(request, 'users/password_reset_confirm.html', {
            'form': form,
            'token': token,
            'user': user
        })
        
    except Http404:
        messages.error(request, _("Yaroqsiz yoki eskirgan parol tiklash havolasi"))
        return redirect('users:password_reset')


@login_required
@csrf_protect
def change_password_view(request):
    """
    Change password for logged-in user
    """
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            user = request.user
            new_password = form.cleaned_data['new_password1']
            
            # Update password
            user.set_password(new_password)
            user.save(update_fields=['password'])
            
            # Keep user logged in
            update_session_auth_hash(request, user)
            
            messages.success(request, _("Parol muvaffaqiyatli o'zgartirildi"))
            logger.info(f"Password changed for user: {user.username}")
            
            return redirect('users:profile')
    else:
        form = PasswordResetConfirmForm()
    
    return render(request, 'users/change_password.html', {'form': form})


# ==================== PROFILE MANAGEMENT ====================

@login_required
def profile_view(request):
    """
    View user profile
    """
    user = request.user
    context = {
        'user': user,
        'profile_complete_percentage': calculate_profile_completion(user),
    }
    return render(request, 'users/profile.html', context)


@login_required
@csrf_protect
def profile_edit_view(request):
    """
    Edit user profile
    """
    user = request.user
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Profil muvaffaqiyatli yangilandi"))
            logger.info(f"Profile updated for user: {user.username}")
            return redirect('users:profile')
    else:
        form = ProfileUpdateForm(instance=user)
    
    return render(request, 'users/profile_edit.html', {
        'form': form,
        'profile_complete_percentage': calculate_profile_completion(user),
    })


# ==================== SETTINGS & PREFERENCES ====================

@login_required
@require_http_methods(["POST"])
def change_language_view(request):
    """
    Change user language preference (AJAX)
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        language = request.POST.get('language')
        
        if language in dict(CustomUser.LanguageChoices.choices):
            user = request.user
            user.language = language
            user.save(update_fields=['language'])
            
            # Update session language
            from django.utils import translation
            translation.activate(language)
            request.session[translation.LANGUAGE_SESSION_KEY] = language
            
            logger.info(f"Language changed to {language} for user: {user.username}")
            
            return JsonResponse({
                'success': True,
                'message': _("Til muvaffaqiyatli o'zgartirildi"),
                'language': language
            })
    
    return JsonResponse({
        'success': False,
        'message': _("Xatolik yuz berdi")
    }, status=400)


@login_required
@require_http_methods(["POST"])
def update_notification_settings(request):
    """
    Update notification preferences (AJAX)
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        user = request.user
        email_notifications = request.POST.get('email_notifications') == 'true'
        push_notifications = request.POST.get('push_notifications') == 'true'
        
        user.email_notifications = email_notifications
        user.push_notifications = push_notifications
        user.save(update_fields=['email_notifications', 'push_notifications'])
        
        logger.info(f"Notification settings updated for user: {user.username}")
        
        return JsonResponse({
            'success': True,
            'message': _("Sozlamalar saqlandi")
        })
    
    return JsonResponse({
        'success': False,
        'message': _("Xatolik yuz berdi")
    }, status=400)


# ==================== ACCOUNT MANAGEMENT ====================

@login_required
def account_deactivate_view(request):
    """
    Deactivate user account
    """
    if request.method == 'POST':
        user = request.user
        username = user.username
        
        # Soft delete - deactivate account
        user.is_active = False
        user.save(update_fields=['is_active'])
        
        # Logout user
        logout(request)
        
        messages.success(
            request,
            _("Hisobingiz deaktivatsiya qilindi. "
              "Qayta faollashtirish uchun login qiling.")
        )
        logger.info(f"Account deactivated: {username}")
        
        return redirect('home')
    
    return render(request, 'users/account_deactivate.html')


@login_required
@csrf_protect
def delete_account_view(request):
    """
    Permanently delete user account
    """
    if request.method == 'POST':
        user = request.user
        username = user.username
        
        # Verify password
        password = request.POST.get('password')
        if not user.check_password(password):
            messages.error(request, _("Parol noto'g'ri"))
            return render(request, 'users/account_delete.html')
        
        # Logout first
        logout(request)
        
        # Delete user (cascade will handle related objects)
        user.delete()
        
        messages.success(request, _("Hisobingiz butunlay o'chirildi"))
        logger.info(f"Account permanently deleted: {username}")
        
        return redirect('home')
    
    return render(request, 'users/account_delete.html')


# ==================== UTILITY FUNCTIONS ====================

def calculate_profile_completion(user):
    """
    Calculate profile completion percentage
    """
    total_fields = 5  # first_name, last_name, email, phone, date_of_birth
    completed_fields = 0
    
    if user.first_name and user.last_name:
        completed_fields += 1  # Count name as one field
    if user.email:
        completed_fields += 1
    if user.phone:
        completed_fields += 1
    if user.date_of_birth:
        completed_fields += 1
    if user.country:
        completed_fields += 1
    
    return min(100, int((completed_fields / total_fields) * 100))


def health_check_view(request):
    """
    Health check endpoint for monitoring
    """
    return JsonResponse({
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
        'service': 'users',
    })


# ==================== ERROR HANDLERS ====================

def handler404(request, exception):
    """Custom 404 handler"""
    return render(request, 'users/errors/404.html', status=404)


def handler500(request):
    """Custom 500 handler"""
    return render(request, 'users/errors/500.html', status=500)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from income.models import Income
from expenses.models import Expense
from django.db.models import Sum

@login_required
def dashboard(request):
    # Foydalanuvchi
    user = request.user

    # Jami Kirim
    total_income = Income.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0

    # Jami Chiqim
    total_expense = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0

    # Joriy Balans
    current_balance = total_income - total_expense

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'current_balance': current_balance,
    }
    return render(request, 'dashboard.html', context)

