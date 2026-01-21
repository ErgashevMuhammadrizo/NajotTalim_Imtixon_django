from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from users import views as users_views
from expenses.views import dashboard_view
import debug_toolbar

# Custom error handlers
handler404 = 'users.views.handler404'
handler500 = 'users.views.handler500'

# Global (language-independent) URLs
urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('test-api/', TemplateView.as_view(template_name='test_api.html'), name='test_api'),
]

# Language-prefixed URLs
urlpatterns += i18n_patterns(
    # Home
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),

    # Users app
    path('users/', include('users.urls', namespace='users')),
    path('income/', include('income.urls')),  # Yangi qo'shildi
    path('expenses/', include('expenses.urls')),  # Yangi qo'shildi

    # Email verification (til prefiksi bilan)
    path('verify-email/<str:token>/', users_views.verify_email_view, name='verify_email'),
    path('password-reset/<str:token>/', users_views.password_reset_confirm_view, name='password_reset_confirm_global'),

    # About pages
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('contact/', TemplateView.as_view(template_name='contact.html'), name='contact'),
    path('privacy/', TemplateView.as_view(template_name='privacy.html'), name='privacy'),
    path('terms/', TemplateView.as_view(template_name='terms.html'), name='terms'),

    prefix_default_language=True,
)

# Static and media files (development only)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
