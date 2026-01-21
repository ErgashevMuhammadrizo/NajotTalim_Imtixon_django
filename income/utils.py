"""
UTILS.PY - Professional utility functions for Income App
Features:
- Currency conversion and formatting
- Date/time utilities
- Financial calculations
- Data validation and sanitization
- File handling
- Email utilities
- Chart data preparation
- Error handling decorators
"""

import json
import csv
import re
import math
import hashlib
import uuid
import logging
import traceback
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from functools import wraps
from pathlib import Path

from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Sum, Count, Avg, Max, Min, F, Q, Case, When, Window
from django.db.models.functions import TruncMonth
from django.utils.dateformat import format as django_date_format
from django.utils.formats import date_format
from django.core.exceptions import ValidationError
from .models import Income, IncomeCategory, IncomeSource, IncomeTag
from .services import CurrencyConverter, EmailService
logger = logging.getLogger(__name__)

# ================ REPORT GENERATION ================

def generate_income_report(
    user, 
    start_date=None, 
    end_date=None, 
    currency='UZS',
    report_type='summary'
) -> Dict[str, Any]:
    """
    Generate comprehensive income report
    """
    if not start_date:
        start_date = timezone.now().date().replace(day=1)
    if not end_date:
        end_date = timezone.now().date()
    
    # Get incomes for period
    incomes = Income.objects.filter(
        user=user,
        date__range=[start_date, end_date],
        status='received'
    ).select_related('category', 'source_obj').prefetch_related('tags')
    
    # Calculate statistics
    total_income = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_converted = CurrencyConverter.convert(total_income, 'UZS', currency)
    
    category_stats = incomes.values('category__name', 'category__color').annotate(
        total=Sum('amount'),
        count=Count('id'),
        percentage=Window(
            expression=100.0 * Sum('amount') / Sum(Sum('amount')).over(),
            order_by=F('total').desc()
        )
    ).order_by('-total')
    
    monthly_trend = incomes.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('month')
    
    # Top sources
    top_sources = incomes.values('source').annotate(
        total=Sum('amount'),
        count=Count('id'),
        last_date=Max('date')
    ).order_by('-total')[:10]
    
    # Payment method distribution
    payment_stats = incomes.values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id'),
        percentage=Window(
            expression=100.0 * Sum('amount') / Sum(Sum('amount')).over()
        )
    ).order_by('-total')
    
    # Tax summary
    tax_summary = incomes.aggregate(
        total_tax=Sum('tax_amount'),
        taxable_income=Sum(Case(
            When(is_taxable=True, then=F('amount')),
            default=Decimal('0'),
            output_field=models.DecimalField()
        ))
    )
    
    # Prepare report data
    report_data = {
        'period': {
            'start': start_date,
            'end': end_date,
            'formatted': DateUtils.format_date_range(start_date, end_date)
        },
        'summary': {
            'total_income': total_income,
            'total_converted': total_converted,
            'currency': currency,
            'formatted_total': CurrencyConverter.format_currency(total_converted, currency),
            'transaction_count': incomes.count(),
            'average_income': incomes.aggregate(avg=Avg('amount'))['avg'] or Decimal('0'),
            'max_income': incomes.aggregate(max=Max('amount'))['max'] or Decimal('0'),
            'min_income': incomes.aggregate(min=Min('amount'))['min'] or Decimal('0'),
            'total_tax': tax_summary['total_tax'] or Decimal('0'),
            'taxable_income': tax_summary['taxable_income'] or Decimal('0')
        },
        'category_distribution': list(category_stats),
        'monthly_trend': list(monthly_trend),
        'top_sources': list(top_sources),
        'payment_methods': list(payment_stats),
        'generated_at': timezone.now(),
        'report_type': report_type
    }
    
    # Add detailed data if needed
    if report_type == 'detailed':
        report_data['incomes'] = list(incomes.values(
            'uuid', 'date', 'source', 'amount', 'currency',
            'category__name', 'payment_method', 'status',
            'description', 'tax_amount', 'is_taxable'
        )[:100])  # Limit to 100 records
    
    return report_data


def calculate_tax(
    amount: Decimal,
    tax_rate: Decimal = None,
    currency: str = 'UZS',
    include_details: bool = False
) -> Dict[str, Any]:
    """
    Calculate tax for income amount
    """
    # Default tax rates by currency (in percentage)
    default_tax_rates = {
        'UZS': Decimal('12.0'),  # 12% VAT for Uzbekistan
        'USD': Decimal('10.0'),  # 10% for USD
        'EUR': Decimal('20.0'),  # 20% VAT for Europe
        'RUB': Decimal('20.0'),  # 20% VAT for Russia
    }
    
    if tax_rate is None:
        tax_rate = default_tax_rates.get(currency, Decimal('10.0'))
    
    tax_amount = (amount * tax_rate / Decimal('100.0')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    
    net_amount = amount - tax_amount
    
    result = {
        'gross_amount': amount,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'net_amount': net_amount,
        'currency': currency
    }
    
    if include_details:
        result.update({
            'formatted_gross': CurrencyConverter.format_currency(amount, currency),
            'formatted_tax': CurrencyConverter.format_currency(tax_amount, currency),
            'formatted_net': CurrencyConverter.format_currency(net_amount, currency),
            'tax_percentage': f"{tax_rate}%",
            'tax_ratio': float(tax_amount / amount) if amount > 0 else 0
        })
    
    return result


def send_income_notification(
    user,
    income,
    notification_type: str = 'created',
    additional_data: Dict[str, Any] = None
) -> bool:
    """
    Send income notification to user
    """
    if additional_data is None:
        additional_data = {}
    
    try:
        # Prepare notification data
        notification_data = {
            'income_id': str(income.uuid),
            'user_id': user.id,
            'user_email': user.email,
            'user_name': user.get_full_name() or user.username,
            'income_amount': str(income.amount),
            'income_currency': income.currency,
            'income_source': income.source,
            'income_date': income.date.isoformat(),
            'notification_type': notification_type,
            'timestamp': timezone.now().isoformat(),
            **additional_data
        }
        
        # Format amount for display
        formatted_amount = CurrencyConverter.format_currency(
            income.amount,
            income.currency
        )
        
        # Determine message based on notification type
        messages = {
            'created': _('Yangi kirim qo\'shildi: {amount} - {source}'),
            'updated': _('Kirim yangilandi: {amount} - {source}'),
            'deleted': _('Kirim o\'chirildi: {amount} - {source}'),
            'received': _('Kirim qabul qilindi: {amount} - {source}'),
            'pending': _('Kirim kutilmoqda: {amount} - {source}'),
            'recurring_created': _('Takrorlanuvchi kirim yaratildi: {amount} - {source}'),
        }
        
        message_template = messages.get(notification_type, _('Kirim yangilandi: {amount} - {source}'))
        message = message_template.format(
            amount=formatted_amount,
            source=income.source
        )
        
        # Send email notification
        if user.email:
            EmailService.send_income_notification(user.email, {
                'amount': formatted_amount,
                'source': income.source,
                'date': income.date.strftime('%d.%m.%Y'),
                'category': income.category.name if income.category else '',
                'message': message,
                'type': notification_type
            })
        
        # Send in-app notification (you would implement this based on your notification system)
        # Example: create_notification(user, 'income', message, notification_data)
        
        # Log notification
        logger.info(f"Income notification sent: {notification_type} - User: {user.id}, Income: {income.uuid}")
        
        # You could also send push notification here
        # send_push_notification(user, 'Kirim bildirishnomasi', message)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send income notification: {str(e)}")
        return False


def validate_currency(currency_code: str, raise_exception: bool = False) -> bool:
    """
    Validate currency code
    """
    valid_currencies = ['USD', 'UZS', 'EUR', 'RUB', 'GBP', 'CNY', 'JPY', 'KRW']
    is_valid = currency_code in valid_currencies
    
    if not is_valid and raise_exception:
        raise ValueError(_('Noto\'g\'ri valyuta kodi: {}').format(currency_code))
    
    return is_valid


def format_currency(
    amount: Union[Decimal, float, str, int],
    currency: str = 'UZS',
    locale: str = 'uz-UZ',
    show_symbol: bool = True
) -> str:
    """
    Format currency amount with proper localization
    """
    # Convert to Decimal if needed
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount))
        except:
            amount = Decimal('0')
    
    # Uzbek specific formatting
    if locale == 'uz-UZ':
        # Format for Uzbek locale
        if currency == 'UZS':
            # Remove decimal for UZS
            formatted = f"{amount:,.0f}".replace(',', ' ')
            if show_symbol:
                return f"{formatted} soʻm"
            return formatted
        else:
            # Show 2 decimal places for other currencies
            formatted = f"{amount:,.2f}".replace(',', ' ')
            if show_symbol:
                symbols = {
                    'USD': '$',
                    'EUR': '€',
                    'RUB': '₽',
                    'GBP': '£',
                    'CNY': '¥',
                    'JPY': '¥',
                    'KRW': '₩'
                }
                symbol = symbols.get(currency, currency)
                return f"{symbol}{formatted.replace('.', ',')}"
            return formatted.replace('.', ',')
    
    else:
        # Use Intl.NumberFormat style for other locales
        try:
            # This would use JavaScript Intl.NumberFormat in frontend
            # For backend, we'll use simple formatting
            formatted = f"{amount:,.2f}"
            if show_symbol:
                return f"{currency} {formatted}"
            return formatted
        except:
            return str(amount)


def parse_date_range(
    date_range_str: str,
    default_period: str = 'this_month'
) -> Tuple[date, date]:
    """
    Parse date range string to start and end dates
    Supports: 'today', 'yesterday', 'this_week', 'last_week', 
              'this_month', 'last_month', 'this_year', 'last_year',
              'custom:YYYY-MM-DD:YYYY-MM-DD', 'last_30_days', 'last_90_days'
    """
    today = timezone.now().date()
    
    if not date_range_str:
        date_range_str = default_period
    
    # Handle predefined periods
    if date_range_str == 'today':
        return today, today
    
    elif date_range_str == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    
    elif date_range_str == 'this_week':
        start = today - timedelta(days=today.weekday())
        return start, today
    
    elif date_range_str == 'last_week':
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        return start, end
    
    elif date_range_str == 'this_month':
        start = today.replace(day=1)
        return start, today
    
    elif date_range_str == 'last_month':
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
        return start, end
    
    elif date_range_str == 'this_year':
        start = today.replace(month=1, day=1)
        return start, today
    
    elif date_range_str == 'last_year':
        end = today.replace(year=today.year-1, month=12, day=31)
        start = end.replace(month=1, day=1)
        return start, end
    
    elif date_range_str == 'last_30_days':
        start = today - timedelta(days=30)
        return start, today
    
    elif date_range_str == 'last_90_days':
        start = today - timedelta(days=90)
        return start, today
    
    elif date_range_str.startswith('custom:'):
        # Format: custom:YYYY-MM-DD:YYYY-MM-DD
        parts = date_range_str.split(':')
        if len(parts) == 3:
            try:
                start = datetime.strptime(parts[1], '%Y-%m-%d').date()
                end = datetime.strptime(parts[2], '%Y-%m-%d').date()
                return start, end
            except ValueError:
                pass
    
    # Default: this month
    start = today.replace(day=1)
    return start, today


def get_month_range(year: int, month: int) -> Tuple[date, date]:
    """
    Get start and end dates for a specific month
    """
    if month < 1 or month > 12:
        raise ValueError(_('Oy raqami 1-12 orasida bo\'lishi kerak'))
    
    if month == 12:
        start_date = date(year, 12, 1)
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        start_date = date(year, month, 1)
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date


def get_quarter_range(year: int, quarter: int) -> Tuple[date, date]:
    """
    Get start and end dates for a specific quarter
    Quarter: 1 (Jan-Mar), 2 (Apr-Jun), 3 (Jul-Sep), 4 (Oct-Dec)
    """
    if quarter < 1 or quarter > 4:
        raise ValueError(_('Chorak raqami 1-4 orasida bo\'lishi kerak'))
    
    start_month = 3 * (quarter - 1) + 1
    end_month = start_month + 2
    
    start_date = date(year, start_month, 1)
    
    if end_month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, end_month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date


def get_week_range(reference_date: date = None) -> Tuple[date, date]:
    """
    Get start and end dates for the week containing reference_date
    Monday is considered the first day of week
    """
    if reference_date is None:
        reference_date = timezone.now().date()
    
    # Monday is 0, Sunday is 6
    start_date = reference_date - timedelta(days=reference_date.weekday())
    end_date = start_date + timedelta(days=6)
    
    return start_date, end_date


# ================ ADDITIONAL IMPORTED FUNCTIONS ================

def generate_income_stats(user, start_date=None, end_date=None, currency='UZS'):
    """
    Generate comprehensive income statistics
    """
    if not start_date:
        start_date = timezone.now().date().replace(day=1)
    if not end_date:
        end_date = timezone.now().date()
    
    incomes = Income.objects.filter(
        user=user,
        date__range=[start_date, end_date],
        status='received'
    )
    
    # Basic stats
    total = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    count = incomes.count()
    avg = incomes.aggregate(avg=Avg('amount'))['avg'] or Decimal('0')
    max_income = incomes.aggregate(max=Max('amount'))['max'] or Decimal('0')
    min_income = incomes.aggregate(min=Min('amount'))['min'] or Decimal('0')
    
    # Convert to target currency
    total_converted = CurrencyConverter.convert(total, 'UZS', currency)
    avg_converted = CurrencyConverter.convert(avg, 'UZS', currency)
    max_converted = CurrencyConverter.convert(max_income, 'UZS', currency)
    min_converted = CurrencyConverter.convert(min_income, 'UZS', currency)
    
    # Daily average
    days_diff = (end_date - start_date).days + 1
    daily_avg = total_converted / days_diff if days_diff > 0 else Decimal('0')
    
    # Category distribution
    categories = incomes.values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Weekly pattern
    weekly_pattern = {}
    for income in incomes:
        weekday = income.date.strftime('%A')
        weekly_pattern[weekday] = weekly_pattern.get(weekday, Decimal('0')) + income.amount
    
    # Monthly trend (last 6 months)
    six_months_ago = end_date - timedelta(days=180)
    monthly_trend = incomes.filter(
        date__gte=six_months_ago
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    return {
        'period': {
            'start': start_date,
            'end': end_date,
            'days': days_diff
        },
        'totals': {
            'amount': total_converted,
            'count': count,
            'average': avg_converted,
            'max': max_converted,
            'min': min_converted,
            'daily_average': daily_avg
        },
        'formatted': {
            'total': CurrencyConverter.format_currency(total_converted, currency),
            'average': CurrencyConverter.format_currency(avg_converted, currency),
            'daily_average': CurrencyConverter.format_currency(daily_avg, currency)
        },
        'categories': list(categories),
        'weekly_pattern': weekly_pattern,
        'monthly_trend': list(monthly_trend),
        'currency': currency
    }


def calculate_income_tax(income, tax_rate=None):
    """
    Calculate tax for a specific income
    """
    if tax_rate is None:
        # Use default tax rate based on currency
        default_rates = {
            'UZS': Decimal('12.0'),
            'USD': Decimal('10.0'),
            'EUR': Decimal('20.0'),
            'RUB': Decimal('20.0')
        }
        tax_rate = default_rates.get(income.currency, Decimal('10.0'))
    
    if income.is_taxable:
        tax_amount = (income.amount * tax_rate / Decimal('100.0')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    else:
        tax_amount = Decimal('0.0')
    
    return {
        'taxable': income.is_taxable,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'net_amount': income.amount - tax_amount,
        'currency': income.currency
    }


def send_bulk_income_notification(user, incomes, notification_type='bulk_import'):
    """
    Send notification for bulk income operations
    """
    try:
        total_amount = sum(income.amount for income in incomes)
        count = len(incomes)
        
        notification_data = {
            'user_id': user.id,
            'user_email': user.email,
            'operation_type': notification_type,
            'income_count': count,
            'total_amount': str(total_amount),
            'currency': incomes[0].currency if incomes else 'UZS',
            'timestamp': timezone.now().isoformat()
        }
        
        if user.email:
            subject = _('Kirimlar guruhli amali')
            message = _('{count} ta kirim muvaffaqiyatli {operation}. Jami summa: {amount}').format(
                count=count,
                operation=notification_type,
                amount=CurrencyConverter.format_currency(total_amount, incomes[0].currency if incomes else 'UZS')
            )
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email]
            )
        
        logger.info(f"Bulk income notification sent: {notification_type} - {count} incomes")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send bulk income notification: {str(e)}")
        return False


def validate_income_data(data):
    """
    Validate income data before saving
    """
    errors = {}
    
    # Check required fields
    required_fields = ['amount', 'currency', 'source', 'date']
    for field in required_fields:
        if field not in data or not data[field]:
            errors[field] = _('Bu maydon to\'ldirilishi shart')
    
    # Validate amount
    if 'amount' in data and data['amount']:
        try:
            amount = Decimal(str(data['amount']))
            if amount <= 0:
                errors['amount'] = _('Miqdor musbat son bo\'lishi kerak')
        except:
            errors['amount'] = _('Noto\'g\'ri miqdor formati')
    
    # Validate currency
    if 'currency' in data and data['currency']:
        if not validate_currency(data['currency']):
            errors['currency'] = _('Noto\'g\'ri valyuta kodi')
    
    # Validate date
    if 'date' in data and data['date']:
        try:
            datetime.strptime(str(data['date']), '%Y-%m-%d')
        except:
            errors['date'] = _('Noto\'g\'ri sana formati (YYYY-MM-DD)')
    
    return errors


def format_income_for_display(income, currency='UZS'):
    """
    Format income object for display
    """
    converted_amount = CurrencyConverter.convert(income.amount, income.currency, currency)
    
    return {
        'id': str(income.uuid),
        'source': income.source,
        'amount': float(income.amount),
        'converted_amount': float(converted_amount),
        'currency': currency,
        'formatted_amount': CurrencyConverter.format_currency(converted_amount, currency),
        'category': income.category.name if income.category else _('Kategoriyasiz'),
        'category_color': income.category.color if income.category else '#6b7280',
        'date': income.date.isoformat(),
        'formatted_date': income.date.strftime('%d.%m.%Y'),
        'status': income.get_status_display(),
        'payment_method': income.get_payment_method_display(),
        'description': income.description or '',
        'is_recurring': income.is_recurring,
        'tags': [tag.name for tag in income.tags.all()],
        'created_at': income.created_at.isoformat(),
        'updated_at': income.updated_at.isoformat()
    }


def get_income_analytics(user, period='month', currency='UZS'):
    """
    Get advanced analytics for income
    """
    today = timezone.now().date()
    start_date, end_date = parse_date_range(period)
    
    incomes = Income.objects.filter(
        user=user,
        date__range=[start_date, end_date],
        status='received'
    )
    
    # Growth calculation
    prev_start, prev_end = parse_date_range('last_' + period)
    previous_incomes = Income.objects.filter(
        user=user,
        date__range=[prev_start, prev_end],
        status='received'
    )
    
    current_total = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    previous_total = previous_incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    current_converted = CurrencyConverter.convert(current_total, 'UZS', currency)
    previous_converted = CurrencyConverter.convert(previous_total, 'UZS', currency)
    
    growth = FinancialCalculator.calculate_growth_rate(current_converted, previous_converted)
    
    # Forecast
    forecast_data = FinancialCalculator.forecast_trend(
        [CurrencyConverter.convert(i.amount, i.currency, currency) for i in incomes.order_by('date')],
        periods=3
    )
    
    # Volatility
    amounts = [float(CurrencyConverter.convert(i.amount, i.currency, currency)) for i in incomes]
    volatility = FinancialCalculator.calculate_volatility(amounts) if amounts else 0
    
    # Seasonality
    seasonality = FinancialCalculator.detect_seasonality(incomes)
    
    return {
        'period': {
            'current': {'start': start_date, 'end': end_date},
            'previous': {'start': prev_start, 'end': prev_end}
        },
        'growth': {
            'percentage': float(growth),
            'amount': float(current_converted - previous_converted),
            'direction': 'up' if growth > 0 else 'down',
            'formatted': f"{'+' if growth > 0 else ''}{growth}%"
        },
        'forecast': forecast_data,
        'volatility': volatility,
        'seasonality': seasonality,
        'currency': currency,
        'timestamp': timezone.now().isoformat()
    }