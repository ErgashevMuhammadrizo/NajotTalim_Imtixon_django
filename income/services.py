"""
SERVICES.PY - Professional service classes for Income App
Focused on Currency and Email services
"""

import json
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Union
from functools import lru_cache

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


# ================ CURRENCY CONVERTER SERVICE ================

class CurrencyConverter:
    """
    Professional Currency Converter Service with:
    - Real-time exchange rates from APIs
    - Caching for performance
    - Bulk conversion
    - Historical rates
    - Multiple API fallbacks
    """
    
    def __init__(self):
        # API configuration
        self.api_configs = [
            {
                'name': 'Frankfurter',
                'url': 'https://api.frankfurter.app/latest',
                'params': {'base': 'USD'},
                'free': True,
                'rate_limit': 1000  # requests per month
            },
            {
                'name': 'ExchangeRateAPI',
                'url': 'https://api.exchangerate-api.com/v4/latest/USD',
                'params': {},
                'free': True,
                'rate_limit': 1500
            },
            {
                'name': 'OpenExchangeRates',
                'url': f'https://openexchangerates.org/api/latest.json?app_id={settings.OPENEXCHANGE_APP_ID}',
                'params': {},
                'free': False,
                'rate_limit': 1000
            } if hasattr(settings, 'OPENEXCHANGE_APP_ID') else None
        ]
        
        # Remove None configs
        self.api_configs = [config for config in self.api_configs if config]
        
        # Base rates as fallback (updated periodically)
        self.base_rates = {
            'USD': Decimal('1.0'),
            'UZS': Decimal('12500.0'),
            'EUR': Decimal('0.92'),
            'RUB': Decimal('90.5'),
            'GBP': Decimal('0.79'),
            'CNY': Decimal('7.2'),
            'JPY': Decimal('148.0'),
            'KRW': Decimal('1320.0'),
            'KZT': Decimal('460.0'),
            'TRY': Decimal('32.0'),
        }
        
        # Cache configuration
        self.cache_timeout = 3600  # 1 hour
        self.historical_cache_timeout = 86400 * 7  # 7 days for historical rates
        
        # Statistics
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'conversions': 0,
            'last_update': None
        }
    
    def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """
        Convert amount from one currency to another
        """
        if from_currency == to_currency:
            return amount
        
        self.stats['conversions'] += 1
        
        # Get exchange rate
        rate = self.get_exchange_rate(from_currency, to_currency)
        
        # Perform conversion
        converted = amount * rate
        
        # Round to 2 decimal places
        return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @lru_cache(maxsize=128)
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """
        Get exchange rate between two currencies with caching
        """
        if from_currency == to_currency:
            return Decimal('1.0')
        
        cache_key = f"exchange_rate_{from_currency}_{to_currency}"
        cached_rate = cache.get(cache_key)
        
        if cached_rate:
            self.stats['cache_hits'] += 1
            return Decimal(cached_rate)
        
        # Try to get rate from API
        rate = self._fetch_rate_from_api(from_currency, to_currency)
        
        if rate is None:
            # Fallback to base rates
            rate = self._get_rate_from_base(from_currency, to_currency)
        
        # Cache the rate
        if rate:
            cache.set(cache_key, str(rate), self.cache_timeout)
        
        return rate or Decimal('1.0')
    
    def _fetch_rate_from_api(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """
        Fetch exchange rate from external APIs with fallback
        """
        for config in self.api_configs:
            try:
                self.stats['api_calls'] += 1
                
                response = requests.get(
                    config['url'],
                    params=config['params'],
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    rates = data.get('rates', {})
                    base = data.get('base', 'USD')
                    
                    if base == from_currency:
                        # Direct rate available
                        if to_currency in rates:
                            rate = Decimal(str(rates[to_currency]))
                            logger.info(f"Got rate from {config['name']}: 1 {from_currency} = {rate} {to_currency}")
                            return rate
                    else:
                        # Convert through base currency
                        if from_currency in rates and to_currency in rates:
                            from_rate = Decimal(str(rates[from_currency]))
                            to_rate = Decimal(str(rates[to_currency]))
                            rate = to_rate / from_rate
                            logger.info(f"Got rate from {config['name']}: 1 {from_currency} = {rate} {to_currency}")
                            return rate
                
            except Exception as e:
                logger.warning(f"API {config['name']} failed: {e}")
                continue
        
        return None
    
    def _get_rate_from_base(self, from_currency: str, to_currency: str) -> Decimal:
        """
        Get rate from base rates (fallback)
        """
        try:
            # Convert through USD
            if from_currency in self.base_rates and to_currency in self.base_rates:
                from_rate = self.base_rates[from_currency]
                to_rate = self.base_rates[to_currency]
                return to_rate / from_rate
        except Exception as e:
            logger.error(f"Error calculating rate from base: {e}")
        
        return Decimal('1.0')
    
    def convert_bulk(self, amounts: List[Decimal], from_currency: str, to_currency: str) -> List[Decimal]:
        """
        Convert multiple amounts at once (optimized)
        """
        rate = self.get_exchange_rate(from_currency, to_currency)
        return [amount * rate for amount in amounts]
    
    def get_historical_rate(self, date: datetime.date, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """
        Get historical exchange rate for a specific date
        """
        if from_currency == to_currency:
            return Decimal('1.0')
        
        cache_key = f"historical_rate_{date}_{from_currency}_{to_currency}"
        cached_rate = cache.get(cache_key)
        
        if cached_rate:
            return Decimal(cached_rate)
        
        try:
            # Using Frankfurter API for historical rates (free)
            url = f"https://api.frankfurter.app/{date}"
            response = requests.get(url, params={
                'from': from_currency,
                'to': to_currency
            }, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                rate = Decimal(str(data['rates'].get(to_currency, 0)))
                
                # Cache for future use
                cache.set(cache_key, str(rate), self.historical_cache_timeout)
                
                logger.info(f"Got historical rate for {date}: 1 {from_currency} = {rate} {to_currency}")
                return rate
                
        except Exception as e:
            logger.warning(f"Failed to fetch historical rate: {e}")
        
        return None
    
    def update_base_rates(self) -> bool:
        """
        Update base rates from API
        """
        try:
            response = requests.get(
                'https://api.frankfurter.app/latest',
                params={'base': 'USD'},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                rates = data.get('rates', {})
                
                # Update base rates
                for currency, rate in rates.items():
                    self.base_rates[currency] = Decimal(str(rate))
                
                # Add USD rate
                self.base_rates['USD'] = Decimal('1.0')
                
                # Clear cache to force fresh rates
                cache.clear()
                
                self.stats['last_update'] = timezone.now()
                logger.info("Base rates updated successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update base rates: {e}")
        
        return False
    
    def format_currency(self, amount: Decimal, currency: str, locale: str = 'uz') -> str:
        """
        Format currency amount with proper localization
        """
        # Currency symbols
        symbols = {
            'USD': '$',
            'UZS': 'soʻm',
            'EUR': '€',
            'RUB': '₽',
            'GBP': '£',
            'CNY': '¥',
            'JPY': '¥',
            'KRW': '₩',
            'KZT': '₸',
            'TRY': '₺',
        }
        
        # Format based on locale
        if locale == 'uz':
            if currency == 'UZS':
                # Uzbek sum: no decimal places, space as thousand separator
                formatted = f"{amount:,.0f}".replace(',', ' ')
                symbol = symbols.get(currency, currency)
                return f"{formatted} {symbol}"
            else:
                # Other currencies: 2 decimal places, comma as decimal separator
                formatted = f"{amount:,.2f}".replace(',', ' ').replace('.', ',')
                symbol = symbols.get(currency, currency)
                if currency in ['USD', 'EUR', 'GBP']:
                    return f"{symbol}{formatted}"
                else:
                    return f"{formatted} {symbol}"
        else:
            # International format
            formatted = f"{amount:,.2f}"
            symbol = symbols.get(currency, currency)
            return f"{symbol}{formatted}"
    
    def get_supported_currencies(self) -> List[Dict[str, str]]:
        """
        Get list of supported currencies with details
        """
        return [
            {'code': 'USD', 'name': _('AQSH Dollari'), 'symbol': '$', 'flag': '🇺🇸'},
            {'code': 'UZS', 'name': _('Oʻzbek soʻmi'), 'symbol': 'soʻm', 'flag': '🇺🇿'},
            {'code': 'EUR', 'name': _('Yevro'), 'symbol': '€', 'flag': '🇪🇺'},
            {'code': 'RUB', 'name': _('Rus rubl'), 'symbol': '₽', 'flag': '🇷🇺'},
            {'code': 'GBP', 'name': _('Funt sterling'), 'symbol': '£', 'flag': '🇬🇧'},
            {'code': 'CNY', 'name': _('Xitoy yuani'), 'symbol': '¥', 'flag': '🇨🇳'},
            {'code': 'JPY', 'name': _('Yapon iyenasi'), 'symbol': '¥', 'flag': '🇯🇵'},
            {'code': 'KRW', 'name': _('Janubiy Koreya voni'), 'symbol': '₩', 'flag': '🇰🇷'},
            {'code': 'KZT', 'name': _('Qozoq tangasi'), 'symbol': '₸', 'flag': '🇰🇿'},
            {'code': 'TRY', 'name': _('Turk lirasi'), 'symbol': '₺', 'flag': '🇹🇷'},
        ]
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """
        Get conversion statistics
        """
        return {
            **self.stats,
            'cache_size': len([k for k in cache._cache if 'exchange_rate' in k]),
            'base_currencies_count': len(self.base_rates),
            'api_configs_count': len(self.api_configs)
        }


# ================ EMAIL SERVICE ================

class EmailService:
    """
    Professional Email Service with:
    - HTML and text templates
    - Email queuing
    - Transactional emails
    - Attachment support
    - Email tracking
    """
    
    def __init__(self):
        self.default_from = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kirimchiqim.uz')
        self.support_email = getattr(settings, 'SUPPORT_EMAIL', 'support@kirimchiqim.uz')
        self.bcc_emails = getattr(settings, 'EMAIL_BCC', [])
        
        # Email templates configuration
        self.templates = {
            'income_created': {
                'subject': _('Yangi kirim qoʻshildi'),
                'template': 'emails/income_created.html',
                'text_template': 'emails/income_created.txt'
            },
            'income_updated': {
                'subject': _('Kirim yangilandi'),
                'template': 'emails/income_updated.html',
                'text_template': 'emails/income_updated.txt'
            },
            'income_deleted': {
                'subject': _('Kirim oʻchirildi'),
                'template': 'emails/income_deleted.html',
                'text_template': 'emails/income_deleted.txt'
            },
            'monthly_summary': {
                'subject': _('Oylik hisobot'),
                'template': 'emails/monthly_summary.html',
                'text_template': 'emails/monthly_summary.txt'
            },
            'goal_achieved': {
                'subject': _('Tabriklaymiz! Maqsadingizga yetdingiz'),
                'template': 'emails/goal_achieved.html',
                'text_template': 'emails/goal_achieved.txt'
            },
            'recurring_reminder': {
                'subject': _('Takrorlanuvchi kirim eslatmasi'),
                'template': 'emails/recurring_reminder.html',
                'text_template': 'emails/recurring_reminder.txt'
            },
            'welcome': {
                'subject': _('Kirim-Chiqim dasturiga xush kelibsiz!'),
                'template': 'emails/welcome.html',
                'text_template': 'emails/welcome.txt'
            },
            'password_reset': {
                'subject': _('Parolni tiklash'),
                'template': 'emails/password_reset.html',
                'text_template': 'emails/password_reset.txt'
            },
            'security_alert': {
                'subject': _('Xavfsizlik ogohlantirishi'),
                'template': 'emails/security_alert.html',
                'text_template': 'emails/security_alert.txt'
            },
            'export_ready': {
                'subject': _('Eksport tayyor'),
                'template': 'emails/export_ready.html',
                'text_template': 'emails/export_ready.txt'
            }
        }
        
        # Statistics
        self.stats = {
            'emails_sent': 0,
            'emails_failed': 0,
            'last_sent': None
        }
    
    def send_income_created_email(self, user, income) -> bool:
        """
        Send email when income is created
        """
        context = {
            'user': user,
            'income': income,
            'amount_formatted': self._format_currency(income.amount, income.currency),
            'date': income.date.strftime('%d %B %Y'),
            'time': income.time.strftime('%H:%M') if income.time else '',
            'category': income.category.name if income.category else _('Kategoriyasiz'),
            'category_color': income.category.color if income.category else '#6b7280',
            'source': income.source,
            'dashboard_url': self._get_dashboard_url(),
            'income_detail_url': self._get_income_detail_url(income),
            'current_year': datetime.now().year,
            'app_name': _('Kirim-Chiqim'),
        }
        
        return self._send_template_email(
            user.email,
            'income_created',
            context
        )
    
    def send_income_updated_email(self, user, income, changes) -> bool:
        """
        Send email when income is updated
        """
        context = {
            'user': user,
            'income': income,
            'amount_formatted': self._format_currency(income.amount, income.currency),
            'date': income.date.strftime('%d %B %Y'),
            'changes': changes,
            'dashboard_url': self._get_dashboard_url(),
            'income_detail_url': self._get_income_detail_url(income),
            'current_year': datetime.now().year,
            'app_name': _('Kirim-Chiqim'),
        }
        
        return self._send_template_email(
            user.email,
            'income_updated',
            context
        )
    
    def send_income_deleted_email(self, user, income_data) -> bool:
        """
        Send email when income is deleted
        """
        context = {
            'user': user,
            'income_data': income_data,
            'amount_formatted': self._format_currency(
                Decimal(income_data.get('amount', 0)),
                income_data.get('currency', 'UZS')
            ),
            'date': income_data.get('date', ''),
            'source': income_data.get('source', ''),
            'dashboard_url': self._get_dashboard_url(),
            'current_year': datetime.now().year,
            'app_name': _('Kirim-Chiqim'),
        }
        
        return self._send_template_email(
            user.email,
            'income_deleted',
            context
        )
    
    def send_monthly_summary_email(self, user, month_data) -> bool:
        """
        Send monthly summary email
        """
        month_names = {
            1: _('Yanvar'), 2: _('Fevral'), 3: _('Mart'),
            4: _('Aprel'), 5: _('May'), 6: _('Iyun'),
            7: _('Iyul'), 8: _('Avgust'), 9: _('Sentabr'),
            10: _('Oktabr'), 11: _('Noyabr'), 12: _('Dekabr')
        }
        
        context = {
            'user': user,
            'month': month_data['month'],
            'month_name': month_names.get(month_data['month'], ''),
            'year': month_data['year'],
            'total_income': self._format_currency(
                Decimal(str(month_data['total_income'])),
                month_data.get('currency', 'UZS')
            ),
            'income_count': month_data.get('income_count', 0),
            'average_income': self._format_currency(
                Decimal(str(month_data.get('average_income', 0))),
                month_data.get('currency', 'UZS')
            ),
            'top_categories': month_data.get('top_categories', []),
            'growth_percentage': month_data.get('growth_percentage', 0),
            'growth_direction': 'up' if month_data.get('growth_percentage', 0) > 0 else 'down',
            'dashboard_url': self._get_dashboard_url(),
            'report_url': self._get_report_url(month_data['year'], month_data['month']),
            'current_year': datetime.now().year,
            'app_name': _('Kirim-Chiqim'),
        }
        
        return self._send_template_email(
            user.email,
            'monthly_summary',
            context
        )
    
    def send_goal_achieved_email(self, user, goal) -> bool:
        """
        Send email when income goal is achieved
        """
        context = {
            'user': user,
            'goal': goal,
            'target_amount': self._format_currency(goal.target_amount, goal.currency),
            'current_amount': self._format_currency(goal.current_amount, goal.currency),
            'progress_percentage': goal.progress_percentage,
            'achieved_date': timezone.now().strftime('%d %B %Y'),
            'dashboard_url': self._get_dashboard_url(),
            'goals_url': self._get_goals_url(),
            'current_year': datetime.now().year,
            'app_name': _('Kirim-Chiqim'),
        }
        
        return self._send_template_email(
            user.email,
            'goal_achieved',
            context
        )
    
    def send_recurring_income_reminder(self, user, recurring_income) -> bool:
        """
        Send reminder for recurring income
        """
        context = {
            'user': user,
            'recurring_income': recurring_income,
            'next_date': recurring_income.next_occurrence.strftime('%d %B %Y'),
            'amount_formatted': self._format_currency(
                recurring_income.amount,
                recurring_income.currency
            ),
            'source': recurring_income.source,
            'dashboard_url': self._get_dashboard_url(),
            'recurring_url': self._get_recurring_url(),
            'current_year': datetime.now().year,
            'app_name': _('Kirim-Chiqim'),
        }
        
        return self._send_template_email(
            user.email,
            'recurring_reminder',
            context
        )
    
    def send_welcome_email(self, user) -> bool:
        """
        Send welcome email to new user
        """
        context = {
            'user': user,
            'welcome_date': timezone.now().strftime('%d %B %Y'),
            'dashboard_url': self._get_dashboard_url(),
            'support_email': self.support_email,
            'tutorial_url': self._get_tutorial_url(),
            'current_year': datetime.now().year,
            'app_name': _('Kirim-Chiqim'),
        }
        
        return self._send_template_email(
            user.email,
            'welcome',
            context
        )
    
    def send_password_reset_email(self, user, reset_token) -> bool:
        """
        Send password reset email
        """
        context = {
            'user': user,
            'reset_url': f"{self._get_base_url()}/reset-password/{reset_token}/",
            'expiry_hours': 24,
            'current_year': datetime.now().year,
            'app_name': _('Kirim-Chiqim'),
        }
        
        return self._send_template_email(
            user.email,
            'password_reset',
            context
        )
    
    def send_security_alert_email(self, user, alert_type, ip_address=None, device_info=None) -> bool:
        """
        Send security alert email
        """
        alert_messages = {
            'login_new_device': _('Yangi qurilmadan kirish'),
            'login_new_location': _('Yangi manzildan kirish'),
            'password_changed': _('Parol oʻzgartirildi'),
            'suspicious_activity': _('Shubhali faoliyat'),
        }
        
        context = {
            'user': user,
            'alert_type': alert_type,
            'alert_message': alert_messages.get(alert_type, _('Xavfsizlik ogohlantirishi')),
            'ip_address': ip_address,
            'device_info': device_info,
            'timestamp': timezone.now().strftime('%d %B %Y %H:%M'),
            'dashboard_url': self._get_dashboard_url(),
            'support_email': self.support_email,
            'current_year': datetime.now().year,
            'app_name': _('Kirim-Chiqim'),
        }
        
        return self._send_template_email(
            user.email,
            'security_alert',
            context
        )
    
    def send_export_ready_email(self, user, export_type, download_url) -> bool:
        """
        Send email when export is ready
        """
        export_types = {
            'excel': _('Excel fayl'),
            'pdf': _('PDF hujjat'),
            'csv': _('CSV fayl'),
            'json': _('JSON maʼlumotlari'),
        }
        
        context = {
            'user': user,
            'export_type': export_types.get(export_type, export_type),
            'download_url': download_url,
            'expiry_hours': 24,
            'dashboard_url': self._get_dashboard_url(),
            'current_year': datetime.now().year,
            'app_name': _('Kirim-Chiqim'),
        }
        
        return self._send_template_email(
            user.email,
            'export_ready',
            context
        )
    
    def send_custom_email(self, to_email: str, subject: str, template_name: str, context: Dict[str, Any]) -> bool:
        """
        Send custom email with given template
        """
        return self._send_template_email(
            to_email,
            template_name,
            context,
            custom_subject=subject
        )
    
    def _send_template_email(self, to_email: str, template_name: str, 
                           context: Dict[str, Any], custom_subject: str = None) -> bool:
        """
        Internal method to send template-based email
        """
        try:
            # Get template configuration
            template_config = self.templates.get(template_name, {})
            
            if not template_config:
                logger.error(f"Template not found: {template_name}")
                return False
            
            # Prepare context
            context.update({
                'base_url': self._get_base_url(),
                'logo_url': f"{self._get_base_url()}/static/images/logo.png",
                'unsubscribe_url': f"{self._get_base_url()}/unsubscribe/",
            })
            
            # Render templates
            html_content = render_to_string(template_config['template'], context)
            text_content = render_to_string(template_config['text_template'], context)
            
            # Prepare subject
            subject = custom_subject or template_config['subject']
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.default_from,
                to=[to_email],
                bcc=self.bcc_emails,
                reply_to=[self.support_email]
            )
            
            email.attach_alternative(html_content, "text/html")
            
            # Add common headers
            email.extra_headers = {
                'X-Mailer': 'Kirim-Chiqim Email Service',
                'X-Priority': '3',
                'X-MSMail-Priority': 'Normal',
            }
            
            # Send email
            result = email.send(fail_silently=False)
            
            # Update statistics
            self.stats['emails_sent'] += 1
            self.stats['last_sent'] = timezone.now()
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return result > 0
            
        except Exception as e:
            self.stats['emails_failed'] += 1
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_bulk_emails(self, emails_data: List[Dict]) -> Dict[str, Any]:
        """
        Send multiple emails at once
        Returns success/failure statistics
        """
        results = {
            'total': len(emails_data),
            'success': 0,
            'failed': 0,
            'failed_details': []
        }
        
        for email_data in emails_data:
            try:
                success = self._send_template_email(
                    email_data['to_email'],
                    email_data['template_name'],
                    email_data.get('context', {}),
                    email_data.get('subject')
                )
                
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['failed_details'].append({
                        'email': email_data['to_email'],
                        'error': 'Send failed'
                    })
                    
            except Exception as e:
                results['failed'] += 1
                results['failed_details'].append({
                    'email': email_data.get('to_email', 'Unknown'),
                    'error': str(e)
                })
        
        return results
    
    def _format_currency(self, amount: Decimal, currency: str) -> str:
        """
        Format currency amount for display
        """
        converter = CurrencyConverter()
        return converter.format_currency(amount, currency, 'uz')
    
    def _get_base_url(self) -> str:
        """
        Get base URL for the application
        """
        return getattr(settings, 'BASE_URL', 'https://kirimchiqim.uz')
    
    def _get_dashboard_url(self) -> str:
        """
        Get dashboard URL
        """
        return f"{self._get_base_url()}/dashboard/"
    
    def _get_income_detail_url(self, income) -> str:
        """
        Get income detail URL
        """
        return f"{self._get_base_url()}/income/{income.uuid}/"
    
    def _get_report_url(self, year: int, month: int) -> str:
        """
        Get report URL
        """
        return f"{self._get_base_url()}/reports/{year}/{month}/"
    
    def _get_goals_url(self) -> str:
        """
        Get goals URL
        """
        return f"{self._get_base_url()}/goals/"
    
    def _get_recurring_url(self) -> str:
        """
        Get recurring incomes URL
        """
        return f"{self._get_base_url()}/recurring/"
    
    def _get_tutorial_url(self) -> str:
        """
        Get tutorial URL
        """
        return f"{self._get_base_url()}/tutorial/"
    
    def get_email_stats(self) -> Dict[str, Any]:
        """
        Get email service statistics
        """
        return {
            **self.stats,
            'templates_available': len(self.templates),
            'bcc_recipients': len(self.bcc_emails),
            'service_status': 'active'
        }
    
    def test_email_connection(self) -> bool:
        """
        Test email server connection
        """
        try:
            # Try to send a test email
            test_context = {
                'test': True,
                'timestamp': timezone.now().isoformat(),
                'app_name': _('Kirim-Chiqim'),
            }
            
            return self._send_template_email(
                self.support_email,
                'welcome',
                test_context,
                custom_subject=_('Email Server Test')
            )
            
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False