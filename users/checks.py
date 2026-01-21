"""
Custom system checks for users app
ULTRA PRO MAX VERSIYA
"""

from django.core.checks import register, Error, Info, Tags


@register(Tags.security)
def check_settings(app_configs, **kwargs):
    """
    Check security settings for users app
    """
    from django.conf import settings
    
    errors = []
    
    # Check if AUTH_USER_MODEL is set
    if not hasattr(settings, 'AUTH_USER_MODEL'):
        errors.append(
            Error(
                'AUTH_USER_MODEL is not set',
                hint='Add AUTH_USER_MODEL = "users.CustomUser" to settings.py',
                id='users.E001',
            )
        )
    
    # Check if login URL is set
    if not hasattr(settings, 'LOGIN_URL'):
        errors.append(
            Info(
                'LOGIN_URL is not set',
                hint='Add LOGIN_URL = "/users/login/" to settings.py for better security',
                id='users.I001',
            )
        )
    
    # Check email settings for production
    if not settings.DEBUG:
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            errors.append(
                Error(
                    'Console email backend in production',
                    hint='Change EMAIL_BACKEND to SMTP backend for production',
                    id='users.E002',
                )
            )
    
    return errors