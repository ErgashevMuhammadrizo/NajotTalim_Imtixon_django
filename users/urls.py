"""
Users app URL configuration
ULTRA PRO MAX VERSIYA
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from django.utils.translation import gettext_lazy as _
from . import views

app_name = 'users'

urlpatterns = [
    # ========== AUTHENTICATION ==========
    path('register/', views.register_view, name='register'),
    path('register/success/', views.register_success_view, name='register_success'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ========== EMAIL VERIFICATION ==========
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    
    # ========== PASSWORD MANAGEMENT ==========
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('password-reset/<str:token>/', 
         views.password_reset_confirm_view, name='password_reset_confirm'),
    path('change-password/', views.change_password_view, name='change_password'),
    
    # ========== PROFILE MANAGEMENT ==========
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    
    # ========== ACCOUNT MANAGEMENT ==========
    path('account/deactivate/', views.account_deactivate_view, name='account_deactivate'),
    path('account/delete/', views.delete_account_view, name='account_delete'),
    
    # ========== SETTINGS ==========
    path('settings/language/', views.change_language_view, name='change_language'),
    path('settings/notifications/', views.update_notification_settings, name='update_notifications'),
    
    # ========== UTILITY ==========
    path('health/', views.health_check_view, name='health_check'),
    
    # ========== DJANGO DEFAULT AUTH (fallback) ==========
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html'
         ), name='password_reset_done'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ), name='password_reset_complete'),
]