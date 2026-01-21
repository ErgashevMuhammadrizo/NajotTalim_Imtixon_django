# icome/views.py
import json
import csv
import xlsxwriter
import io
from datetime import datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q, F, Window , Case, When, Value , Max, DecimalField
from django.db.models.functions import TruncMonth, TruncYear, ExtractMonth
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _


from .models import Income, IncomeCategory, IncomeSource, IncomeTag, IncomeTemplate, IncomeGoal 
from .forms import (
    IncomeForm, IncomeCategoryForm, IncomeSourceForm, IncomeTagForm,
    IncomeTemplateForm, IncomeGoalForm, IncomeFilterForm, QuickIncomeForm
)


from .models import Income, IncomeCategory, IncomeSource, IncomeTag, IncomeTemplate, IncomeGoal
from .forms import (
    IncomeForm, IncomeCategoryForm, IncomeSourceForm, IncomeTagForm,
    IncomeTemplateForm, IncomeGoalForm, IncomeFilterForm, QuickIncomeForm
)
from income import models

# ================ CURRENCY CONVERSION ================
# Bu funksiya valyuta kurslarini API dan olish yoki manuel kurslar
CURRENCY_RATES = {
    'USD': 12500,  # 1 USD = 12500 UZS
    'EUR': 13500,  # 1 EUR = 13500 UZS
    'RUB': 140,    # 1 RUB = 140 UZS
    'UZS': 1,      # Asosiy valyuta
}

def convert_to_base_currency(amount, from_currency):
    """Valyutani asosiy valyutaga (UZS) o'tkazish"""
    if from_currency == 'UZS':
        return amount
    rate = CURRENCY_RATES.get(from_currency, 1)
    return amount * Decimal(rate)

def convert_from_base_currency(amount, to_currency):
    """Asosiy valyutadan boshqa valyutaga o'tkazish"""
    if to_currency == 'UZS':
        return amount
    rate = CURRENCY_RATES.get(to_currency, 1)
    return amount / Decimal(rate)

# ================ HELPER FUNCTIONS ================

def get_user_incomes(request):
    """Foydalanuvchining kirimlarini olish"""
    return Income.objects.filter(user=request.user).select_related(
        'category', 'source_obj'
    ).prefetch_related('tags')

def apply_filters(queryset, filter_form):
    """Filtrlarni qo'llash"""
    if filter_form.is_valid():
        # Vaqt oralig'i
        date_from, date_to = filter_form.get_date_range()
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        # Kategoriya
        category = filter_form.cleaned_data.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Manba
        source = filter_form.cleaned_data.get('source')
        if source:
            queryset = queryset.filter(source__icontains=source)
        
        # Miqdor oralig'i
        min_amount = filter_form.cleaned_data.get('min_amount')
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)
        
        max_amount = filter_form.cleaned_data.get('max_amount')
        if max_amount:
            queryset = queryset.filter(amount__lte=max_amount)
        
        # Holat
        status = filter_form.cleaned_data.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # To'lov usuli
        payment_method = filter_form.cleaned_data.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        # Valyuta
        currency = filter_form.cleaned_data.get('currency')
        if currency:
            queryset = queryset.filter(currency=currency)
        
        # Takrorlanuvchi
        is_recurring = filter_form.cleaned_data.get('is_recurring')
        if is_recurring == 'true':
            queryset = queryset.filter(is_recurring=True)
        elif is_recurring == 'false':
            queryset = queryset.filter(is_recurring=False)
        
        # Soliqqa tortiladigan
        is_taxable = filter_form.cleaned_data.get('is_taxable')
        if is_taxable == 'true':
            queryset = queryset.filter(is_taxable=True)
        elif is_taxable == 'false':
            queryset = queryset.filter(is_taxable=False)
        
        # Teglar
        tags = filter_form.cleaned_data.get('tags')
        if tags:
            queryset = queryset.filter(tags__in=tags).distinct()
        
        # Qidiruv
        search = filter_form.cleaned_data.get('search')
        if search:
            queryset = queryset.filter(
                Q(source__icontains=search) |
                Q(description__icontains=search) |
                Q(category__name__icontains=search) |
                Q(uuid__icontains=search)
            )
    
    return queryset

def get_summary_stats(queryset, target_currency='UZS'):
    """Statistik xulosani hisoblash (asosiy valyutada)"""
    stats = queryset.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id'),
        avg_amount=Avg('amount'),
        total_tax=Sum('tax_amount'),
        max_amount=Max('amount')
    )
    
    # Har bir valyuta uchun alohida hisob-kitob
    currency_stats = {}
    currencies = queryset.values('currency').distinct()
    
    for currency_data in currencies:
        currency = currency_data['currency']
        currency_queryset = queryset.filter(currency=currency)
        
        currency_stats[currency] = {
            'total': currency_queryset.aggregate(total=Sum('amount'))['total'] or 0,
            'count': currency_queryset.count(),
            'avg': currency_queryset.aggregate(avg=Avg('amount'))['avg'] or 0,
            'tax': currency_queryset.aggregate(total=Sum('tax_amount'))['total'] or 0,
        }
    
    # Asosiy valyutada umumiy summa
    total_in_base_currency = 0
    for currency, data in currency_stats.items():
        amount_in_base = convert_to_base_currency(data['total'], currency)
        total_in_base_currency += amount_in_base
    
    return {
        'total_amount': stats['total_amount'] or 0,
        'total_count': stats['total_count'] or 0,
        'avg_amount': stats['avg_amount'] or 0,
        'total_tax': stats['total_tax'] or 0,
        'max_amount': stats['max_amount'] or 0,
        'net_amount': (stats['total_amount'] or 0) - (stats['total_tax'] or 0),
        'total_in_base_currency': total_in_base_currency,
        'currency_stats': currency_stats,
    }

# ================ INCOME CRUD VIEWS ================

@login_required
def income_list(request):
    """Kirimlar ro'yxati"""
    incomes = get_user_incomes(request)
    
    # Filtrlash
    filter_form = IncomeFilterForm(request.GET, user=request.user)
    if filter_form.is_valid():
        incomes = apply_filters(incomes, filter_form)
    
    # Saralash
    sort_by = request.GET.get('sort', '-date')
    valid_sorts = ['date', '-date', 'amount', '-amount', 'source', '-source', 
                   'created_at', '-created_at']
    if sort_by in valid_sorts:
        incomes = incomes.order_by(sort_by)
    else:
        incomes = incomes.order_by('-date', '-created_at')
    
    # Pagination
    paginator = Paginator(incomes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistika
    stats = get_summary_stats(incomes)
    
    # Oylik statistika
    current_month = timezone.now().month
    current_year = timezone.now().year
    this_month_stats = Income.objects.filter(
        user=request.user,
        date__year=current_year,
        date__month=current_month
    ).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    # Top kategoriyalar
    top_categories = Income.objects.filter(
        user=request.user,
        date__year=current_year
    ).values('category__name', 'category__color', 'category__icon').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5]
    
    # Valyuta distribyutsiyasi
    currency_distribution = Income.objects.filter(
        user=request.user,
        date__year=current_year
    ).values('currency').annotate(
        total=Sum('amount'),
        count=Count('id'),
        total_in_uzs=Sum(F('amount') * Case(
            When(currency='USD', then=Value(CURRENCY_RATES['USD'])),
            When(currency='EUR', then=Value(CURRENCY_RATES['EUR'])),
            When(currency='RUB', then=Value(CURRENCY_RATES['RUB'])),
            default=Value(1),
            output_field=DecimalField() 
        ))
    ).order_by('-total_in_uzs')
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'sort_by': sort_by,
        'stats': stats,
        'this_month_total': this_month_stats['total'] or 0,
        'this_month_count': this_month_stats['count'] or 0,
        'top_categories': top_categories,
        'currency_distribution': currency_distribution,
        'currency_rates': CURRENCY_RATES,
    }
    
    # AJAX so'rov uchun JSON qaytarish
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = {
            'html': render_to_string('income/partials/income_table.html', context, request),
            'stats': stats,
            'pagination': {
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
            }
        }
        return JsonResponse(data)
    
    return render(request, 'income/income_list.html', context)

@login_required
def income_detail(request, uuid):
    """Kirimni batafsil ko'rish"""
    income = get_object_or_404(Income, uuid=uuid, user=request.user)
    
    # Valyuta konvertatsiyasi
    amount_in_uzs = convert_to_base_currency(income.amount, income.currency)
    
    # O'xshash kirimlar
    similar_incomes = Income.objects.filter(
        user=request.user,
        category=income.category
    ).exclude(uuid=uuid)[:5]
    
    context = {
        'income': income,
        'amount_in_uzs': amount_in_uzs,
        'similar_incomes': similar_incomes,
    }
    return render(request, 'income/income_detail.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def income_create(request):
    """Yangi kirim qo'shish"""
    if request.method == 'POST':
        form = IncomeForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            income.save()
            form.save_m2m()
            
            # Maqsadlarni yangilash
            update_income_goals(request.user, income)
            
            messages.success(request, _('Kirim muvaffaqiyatli qo\'shildi!'))
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': _('Kirim qo\'shildi!'),
                    'redirect_url': reverse('income:detail', args=[income.uuid])
                })
            
            return redirect('income:detail', uuid=income.uuid)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': _('Formani to\'ldirishda xatolik!')
                }, status=400)
    else:
        # Shablon yordamida yaratish
        template_id = request.GET.get('template')
        if template_id:
            try:
                template = IncomeTemplate.objects.get(
                    id=template_id, 
                    user=request.user,
                    is_active=True
                )
                initial_data = {
                    'amount': template.amount,
                    'currency': template.currency,
                    'category': template.category,
                    'source': template.source,
                    'payment_method': template.payment_method,
                    'description': template.description,
                }
                form = IncomeForm(initial=initial_data, user=request.user)
            except IncomeTemplate.DoesNotExist:
                form = IncomeForm(user=request.user)
        else:
            form = IncomeForm(user=request.user)
    
    context = {
        'form': form,
        'is_create': True,
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('income/partials/income_form_fields.html', context, request)
        return JsonResponse({'html': html})
    
    return render(request, 'income/income_form.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def income_update(request, uuid):
    """Kirimni tahrirlash"""
    income = get_object_or_404(Income, uuid=uuid, user=request.user)
    
    if request.method == 'POST':
        form = IncomeForm(request.POST, request.FILES, instance=income, user=request.user)
        if form.is_valid():
            income = form.save()
            form.save_m2m()
            
            # Maqsadlarni yangilash
            update_income_goals(request.user, income)
            
            messages.success(request, _('Kirim muvaffaqiyatli yangilandi!'))
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': _('Kirim yangilandi!'),
                    'redirect_url': reverse('income:detail', args=[income.uuid])
                })
            
            return redirect('income:detail', uuid=income.uuid)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': _('Formani to\'ldirishda xatolik!')
                }, status=400)
    else:
        form = IncomeForm(instance=income, user=request.user)
    
    context = {
        'form': form,
        'income': income,
        'is_create': False,
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('income/partials/income_form_fields.html', context, request)
        return JsonResponse({'html': html})
    
    return render(request, 'income/income_form.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def income_delete(request, uuid):
    """Kirimni o'chirish"""
    income = get_object_or_404(Income, uuid=uuid, user=request.user)
    
    if request.method == 'POST':
        income.delete()
        
        # Maqsadlarni yangilash
        update_income_goals(request.user)
        
        messages.success(request, _('Kirim muvaffaqiyatli o\'chirildi!'))
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': _('Kirim o\'chirildi!'),
            })
        
        return redirect('income:list')
    
    context = {'income': income}
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('income/partials/delete_confirm_modal.html', context, request)
        return JsonResponse({'html': html})
    
    return render(request, 'income/income_delete.html', context)

# ================ STATISTICS & REPORTS ================

@login_required
def income_stats(request):
    """Kirim statistikasi"""
    today = timezone.now().date()
    current_year = today.year
    
    # Umumiy statistika
    total_stats = Income.objects.filter(user=request.user).aggregate(
        total=Sum('amount'),
        count=Count('id'),
        avg=Avg('amount'),
        max=Max('amount'),
        total_tax=Sum('tax_amount')
    )
    
    # Kunlik kirimlar (oxirgi 30 kun)
    daily_incomes = []
    for i in range(29, -1, -1):
        date = today - timedelta(days=i)
        daily_total = Income.objects.filter(
            user=request.user,
            date=date,
            status='received'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        daily_incomes.append({
            'date': date.strftime('%Y-%m-%d'),
            'date_display': date.strftime('%d %b'),
            'total': daily_total,
        })
    
    # Haftalik kirimlar (oxirgi 8 hafta)
    weekly_incomes = []
    for i in range(7, -1, -1):
        week_end = today - timedelta(days=i*7)
        week_start = week_end - timedelta(days=6)
        
        weekly_total = Income.objects.filter(
            user=request.user,
            date__range=[week_start, week_end],
            status='received'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        weekly_incomes.append({
            'week': f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}",
            'total': weekly_total,
        })
    
    # Oylik kirimlar (oxirgi 12 oy)
    monthly_incomes = []
    for i in range(11, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        month_end = (month_start.replace(
            month=month_start.month % 12 + 1, 
            year=month_start.year + (1 if month_start.month == 12 else 0),
            day=1
        ) - timedelta(days=1))
        
        monthly_total = Income.objects.filter(
            user=request.user,
            date__range=[month_start, month_end],
            status='received'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_incomes.append({
            'month': month_start.strftime('%Y-%m'),
            'month_name': month_start.strftime('%b %Y'),
            'total': monthly_total,
        })
    
    # Valyuta bo'yicha taqsimot
    currency_distribution = Income.objects.filter(
        user=request.user,
        date__year=current_year
    ).values('currency').annotate(
        total=Sum('amount'),
        count=Count('id'),
        total_in_uzs=Sum(F('amount') * Case(
            When(currency='USD', then=Value(CURRENCY_RATES['USD'])),
            When(currency='EUR', then=Value(CURRENCY_RATES['EUR'])),
            When(currency='RUB', then=Value(CURRENCY_RATES['RUB'])),
            default=Value(1),
            output_field=DecimalField()
        ))
    ).order_by('-total_in_uzs')
    
    # To'lov usullari bo'yicha
    payment_method_stats = Income.objects.filter(
        user=request.user,
        date__year=current_year
    ).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Kategoriyalar bo'yicha
    category_stats = Income.objects.filter(
        user=request.user,
        date__year=current_year
    ).values('category__name', 'category__color').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:10]
    
    context = {
        'total_stats': total_stats,
        'daily_incomes': daily_incomes,
        'weekly_incomes': weekly_incomes,
        'monthly_incomes': monthly_incomes,
        'currency_distribution': list(currency_distribution),
        'payment_method_stats': list(payment_method_stats),
        'category_stats': list(category_stats),
        'current_year': current_year,
        'currency_rates': CURRENCY_RATES,
    }
    
    return render(request, 'income/income_stats.html', context)

@login_required
def income_analytics(request):
    """Kirimlar tahlili"""
    year = request.GET.get('year', timezone.now().year)
    
    try:
        year = int(year)
    except ValueError:
        year = timezone.now().year
    
    # Yillik solishtirish
    yearly_comparison = []
    for y in range(year-2, year+1):
        yearly_stats = Income.objects.filter(
            user=request.user,
            date__year=y,
            status='received'
        ).aggregate(
            total=Sum('amount'),
            count=Count('id'),
            avg=Avg('amount')
        )
        
        yearly_comparison.append({
            'year': y,
            'total': yearly_stats['total'] or 0,
            'count': yearly_stats['count'] or 0,
            'avg': yearly_stats['avg'] or 0,
        })
    
    # Oylik tahlil
    monthly_analysis = []
    for month in range(1, 13):
        month_stats = Income.objects.filter(
            user=request.user,
            date__year=year,
            date__month=month,
            status='received'
        ).aggregate(
            total=Sum('amount'),
            count=Count('id'),
            avg=Avg('amount')
        )
        
        monthly_analysis.append({
            'month': month,
            'month_name': datetime(year, month, 1).strftime('%B'),
            'total': month_stats['total'] or 0,
            'count': month_stats['count'] or 0,
            'avg': month_stats['avg'] or 0,
        })
    
    # Kategoriyalar o'sishi
    category_growth = []
    categories = IncomeCategory.objects.filter(
        Q(user=request.user) | Q(is_default=True)
    )
    
    for category in categories:
        current_year_total = Income.objects.filter(
            user=request.user,
            category=category,
            date__year=year,
            status='received'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        previous_year_total = Income.objects.filter(
            user=request.user,
            category=category,
            date__year=year-1,
            status='received'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        if previous_year_total > 0:
            growth = ((current_year_total - previous_year_total) / previous_year_total) * 100
        else:
            growth = 100 if current_year_total > 0 else 0
        
        category_growth.append({
            'category': category.name,
            'current_year': current_year_total,
            'previous_year': previous_year_total,
            'growth': round(growth, 1),
            'color': category.color
        })
    
    # Maqsadlarga yaqinlik
    goals_progress = IncomeGoal.objects.filter(
        user=request.user,
        status='active'
    )[:5]
    
    for goal in goals_progress:
        goal.update_status()
    
    context = {
        'year': year,
        'yearly_comparison': yearly_comparison,
        'monthly_analysis': monthly_analysis,
        'category_growth': category_growth,
        'goals_progress': goals_progress,
        'available_years': range(timezone.now().year - 5, timezone.now().year + 1),
    }
    
    return render(request, 'income/income_analytics.html', context)

# ================ DASHBOARD VIEWS ================

@login_required
def dashboard(request):
    """Asosiy dashboard"""
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Bugungi kirimlar
    today_income = Income.objects.filter(
        user=request.user,
        date=today,
        status='received'
    )
    
    today_stats = today_income.aggregate(
        total=Sum('amount'),
        count=Count('id'),
        avg=Avg('amount')
    )
    
    # Haftalik kirimlar
    week_income = Income.objects.filter(
        user=request.user,
        date__gte=week_start,
        status='received'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Oylik kirimlar
    month_income = Income.objects.filter(
        user=request.user,
        date__gte=month_start,
        status='received'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Yillik kirimlar
    year_income = Income.objects.filter(
        user=request.user,
        date__year=today.year,
        status='received'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Oxirgi 5 kirim
    recent_incomes = Income.objects.filter(
        user=request.user
    ).select_related('category').order_by('-date', '-created_at')[:5]
    
    # Top kategoriyalar (bu oy)
    top_categories = Income.objects.filter(
        user=request.user,
        date__month=today.month,
        date__year=today.year,
        status='received'
    ).values('category__name', 'category__color').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5]
    
    # Valyuta distribyutsiyasi
    currency_stats = Income.objects.filter(
        user=request.user,
        date__year=today.year,
        status='received'
    ).values('currency').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Faol maqsadlar
    active_goals = IncomeGoal.objects.filter(
        user=request.user,
        status='active'
    )[:3]
    
    for goal in active_goals:
        goal.update_status()
    
    # Haftalik trend (oxirgi 4 hafta)
    weekly_trend = []
    for i in range(3, -1, -1):
        week_end = today - timedelta(days=i*7)
        week_start = week_end - timedelta(days=6)
        
        week_total = Income.objects.filter(
            user=request.user,
            date__range=[week_start, week_end],
            status='received'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        weekly_trend.append({
            'week': f"{week_start.strftime('%d %b')}",
            'total': week_total,
        })
    
    context = {
        'today_stats': today_stats,
        'week_income': week_income,
        'month_income': month_income,
        'year_income': year_income,
        'recent_incomes': recent_incomes,
        'top_categories': top_categories,
        'currency_stats': list(currency_stats),
        'active_goals': active_goals,
        'weekly_trend': weekly_trend,
        'currency_rates': CURRENCY_RATES,
        'today': today,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
@require_GET
def dashboard_stats(request):
    """Dashboard uchun statistikalar (AJAX)"""
    today = timezone.now().date()
    
    # Bugungi kirim
    today_income = Income.objects.filter(
        user=request.user,
        date=today,
        status='received'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Bu hafta kirim
    week_start = today - timedelta(days=today.weekday())
    week_income = Income.objects.filter(
        user=request.user,
        date__gte=week_start,
        status='received'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Bu oy kirim
    month_start = today.replace(day=1)
    month_income = Income.objects.filter(
        user=request.user,
        date__gte=month_start,
        status='received'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Oxirgi 5 kirim
    recent_incomes = Income.objects.filter(
        user=request.user
    ).select_related('category').order_by('-date', '-created_at')[:5]
    
    recent_incomes_list = []
    for income in recent_incomes:
        recent_incomes_list.append({
            'uuid': str(income.uuid),
            'source': income.source,
            'amount': str(income.amount),
            'currency': income.currency,
            'category': income.category.name,
            'date': income.date.strftime('%Y-%m-%d'),
            'color': income.category.color,
        })
    
    # Faol maqsadlar
    active_goals = IncomeGoal.objects.filter(
        user=request.user,
        status='active'
    )[:3]
    
    goals_list = []
    for goal in active_goals:
        goal.update_status()
        goals_list.append({
            'id': goal.id,
            'name': goal.name,
            'progress': goal.progress_percentage,
            'current': goal.current_amount,
            'target': goal.target_amount,
            'remaining_days': goal.remaining_days,
        })
    
    return JsonResponse({
        'today_income': str(today_income),
        'week_income': str(week_income),
        'month_income': str(month_income),
        'recent_incomes': recent_incomes_list,
        'active_goals': goals_list,
    })

# ================ HELPER FUNCTIONS ================

def update_income_goals(user, income=None):
    """Kirim maqsadlarini yangilash"""
    goals = IncomeGoal.objects.filter(
        user=user,
        status='active'
    )
    
    for goal in goals:
        goal.update_status()

# ================ OTHER VIEWS ================

@login_required
def template_create(request):
    """Shablon yaratish"""
    if request.method == 'POST':
        form = IncomeTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.user = request.user
            template.save()
            
            messages.success(request, _("Shablon muvaffaqiyatli yaratildi"))
            return redirect('income:income_add')
    else:
        form = IncomeTemplateForm()
    
    context = {
        'form': form,
        'title': _("Yangi shablon yaratish"),
    }
    return render(request, 'income/template_form.html', context)

@login_required
def income_tag_create(request):
    """Teg yaratish"""
    if request.method == 'POST':
        form = IncomeTagForm(request.POST)
        if form.is_valid():
            tag = form.save(commit=False)
            tag.user = request.user
            tag.save()
            messages.success(request, _('Teg muvaffaqiyatli yaratildi!'))
            return redirect('income:list')
    else:
        form = IncomeTagForm()
    
    return render(request, 'income/tag_form.html', {'form': form})

# ... (qolgan viewlar o'zgarmagan holda)

@login_required
def template_create(request):
    """
    Income template (shablon) yaratish view
    URL: /income/template/create/
    """
    if request.method == 'POST':
        form = IncomeTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.user = request.user
            template.save()

            messages.success(request, _("Shablon muvaffaqiyatli yaratildi"))
            return redirect('income:income_add')
    else:
        form = IncomeTemplateForm()

    context = {
        'form': form,
        'title': _("Yangi shablon yaratish"),
    }
    return render(request, 'income/template_form.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def income_delete(request, uuid):
    """Kirimni o'chirish"""
    income = get_object_or_404(Income, uuid=uuid, user=request.user)
    
    if request.method == 'POST':
        # Ma'lumotlarni saqlash (audit uchun)
        deleted_data = {
            'uuid': str(income.uuid),
            'amount': str(income.amount),
            'source': income.source,
            'date': str(income.date),
        }
        
        income.delete()
        
        # Maqsadlarni yangilash
        update_income_goals(request.user)
        
        messages.success(request, _('Kirim muvaffaqiyatli o\'chirildi!'))
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': _('Kirim o\'chirildi!'),
                'deleted_data': deleted_data
            })
        
        return redirect('income:list')
    
    context = {'income': income}
    
    # AJAX so'rov uchun
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('income/partials/delete_confirm_modal.html', context, request)
        return JsonResponse({'html': html})
    
    return render(request, 'income/income_delete.html', context)


# ================ CATEGORY VIEWS ================

@login_required
def category_list(request):
    """Kategoriyalar ro'yxati"""
    categories = IncomeCategory.objects.filter(
        Q(user=request.user) | Q(is_default=True)
    ).select_related('user').order_by('is_default', 'name')
    
    # Statistika
    for category in categories:
        stats = Income.objects.filter(
            user=request.user,
            category=category
        ).aggregate(
            count=Count('id'),
            total=Sum('amount'),
            avg=Avg('amount')
        )
        category.income_count = stats['count'] or 0
        category.total_amount = stats['total'] or 0
        category.avg_amount = stats['avg'] or 0
    
    context = {'categories': categories}
    return render(request, 'income/category_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def category_create(request):
    """Yangi kategoriya yaratish"""
    if request.method == 'POST':
        form = IncomeCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            
            messages.success(request, _('Kategoriya muvaffaqiyatli yaratildi!'))
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': _('Kategoriya yaratildi!'),
                    'category': {
                        'id': category.id,
                        'name': category.name,
                        'color': category.color,
                        'icon': category.icon
                    }
                })
            
            return redirect('income:categories')
    else:
        form = IncomeCategoryForm()
    
    context = {'form': form, 'is_create': True}
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('income/partials/category_form_modal.html', context, request)
        return JsonResponse({'html': html})
    
    return render(request, 'income/category_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def category_update(request, pk):
    """Kategoriyani tahrirlash"""
    category = get_object_or_404(IncomeCategory, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = IncomeCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            
            messages.success(request, _('Kategoriya muvaffaqiyatli yangilandi!'))
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': _('Kategoriya yangilandi!')
                })
            
            return redirect('income:categories')
    else:
        form = IncomeCategoryForm(instance=category)
    
    context = {'form': form, 'category': category, 'is_create': False}
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('income/partials/category_form_modal.html', context, request)
        return JsonResponse({'html': html})
    
    return render(request, 'income/category_form.html', context)


@login_required
@require_http_methods(["POST"])
def category_delete(request, pk):
    """Kategoriyani o'chirish"""
    category = get_object_or_404(IncomeCategory, pk=pk, user=request.user)
    
    # Kategoriyada kirimlar bormi?
    income_count = Income.objects.filter(category=category).count()
    
    if income_count > 0:
        # Alternative kategoriyaga o'tkazish
        alt_category_id = request.POST.get('alternative_category')
        if alt_category_id:
            try:
                alt_category = IncomeCategory.objects.get(
                    id=alt_category_id,
                    user=request.user
                )
                Income.objects.filter(category=category).update(category=alt_category)
            except IncomeCategory.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': _('Noto\'g\'ri alternativa kategoriya tanlandi!')
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'message': _('Bu kategoriyada kirimlar mavjud. Iltimos, alternativa kategoriya tanlang.')
            }, status=400)
    
    category.delete()
    
    messages.success(request, _('Kategoriya muvaffaqiyatli o\'chirildi!'))
    
    return JsonResponse({
        'success': True,
        'message': _('Kategoriya o\'chirildi!')
    })


# ================ SOURCE VIEWS ================

@login_required
def source_list(request):
    """Manbalar ro'yxati"""
    sources = IncomeSource.objects.filter(
        user=request.user
    ).order_by('name')
    
    # Statistika
    for source in sources:
        stats = Income.objects.filter(
            user=request.user,
            source_obj=source
        ).aggregate(
            count=Count('id'),
            total=Sum('amount'),
            last_date=Max('date')
        )
        source.income_count = stats['count'] or 0
        source.total_amount = stats['total'] or 0
        source.last_income_date = stats['last_date']
    
    context = {'sources': sources}
    return render(request, 'income/source_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def source_create(request):
    """Yangi manba yaratish"""
    if request.method == 'POST':
        form = IncomeSourceForm(request.POST)
        if form.is_valid():
            source = form.save(commit=False)
            source.user = request.user
            source.save()
            
            messages.success(request, _('Manba muvaffaqiyatli yaratildi!'))
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': _('Manba yaratildi!'),
                    'source': {
                        'id': source.id,
                        'name': source.name
                    }
                })
            
            return redirect('income:sources')
    else:
        form = IncomeSourceForm()
    
    context = {'form': form}
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('income/partials/source_form_modal.html', context, request)
        return JsonResponse({'html': html})
    
    return render(request, 'income/source_form.html', context)


# ================ STATISTICS & REPORTS ================

@login_required
def income_stats(request):
    """Kirim statistikasi"""
    # Asosiy ko'rsatkichlar
    today = timezone.now().date()
    current_year = today.year
    current_month = today.month
    
    # Umumiy statistika
    total_stats = Income.objects.filter(user=request.user).aggregate(
        total=Sum('amount'),
        count=Count('id'),
        avg=Avg('amount'),
        max=Max('amount'),
        total_tax=Sum('tax_amount')
    )
    
    # Oylik trend (oxirgi 12 oy)
    monthly_trend = []
    for i in range(11, -1, -1):
        month_date = today - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        month_end = (month_start.replace(
            month=month_start.month % 12 + 1, 
            year=month_start.year + (1 if month_start.month == 12 else 0),
            day=1
        ) - timedelta(days=1))
        
        month_stats = Income.objects.filter(
            user=request.user,
            date__range=[month_start, month_end]
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        monthly_trend.append({
            'month': month_start.strftime('%Y-%m'),
            'month_name': month_start.strftime('%b %Y'),
            'total': month_stats['total'] or 0,
            'count': month_stats['count'] or 0,
        })
    
    # Kunlik trend (oxirgi 30 kun)
    daily_trend = Income.objects.filter(
        user=request.user,
        date__gte=today - timedelta(days=30)
    ).values('date').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('date')
    
    # Kategoriyalar bo'yicha taqsimot
    category_distribution = Income.objects.filter(
        user=request.user,
        date__year=current_year
    ).values('category__name', 'category__color').annotate(
        total=Sum('amount'),
        percentage=Window(
            expression=100.0 * Sum('amount') / Sum(Sum('amount')).over(),
            order_by=F('total').desc()
        )
    ).order_by('-total')
    
    # To'lov usullari bo'yicha
    payment_method_stats = Income.objects.filter(
        user=request.user,
        date__year=current_year
    ).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Top 10 manba
    top_sources = Income.objects.filter(
        user=request.user,
        date__year=current_year
    ).values('source').annotate(
        total=Sum('amount'),
        count=Count('id'),
        last_date=Max('date')
    ).order_by('-total')[:10]
    
    context = {
        'total_stats': total_stats,
        'monthly_trend': monthly_trend,
        'daily_trend': list(daily_trend),
        'category_distribution': list(category_distribution),
        'payment_method_stats': list(payment_method_stats),
        'top_sources': list(top_sources),
        'current_year': current_year,
    }
    
    return render(request, 'income/income_stats.html', context)


@login_required
@require_GET
def income_analytics(request):
    """Kirimlar tahlili"""
    year = request.GET.get('year', timezone.now().year)
    
    try:
        year = int(year)
    except ValueError:
        year = timezone.now().year
    
    # Yillik taqqoslash
    yearly_comparison = []
    for y in range(year-2, year+1):
        yearly_stats = Income.objects.filter(
            user=request.user,
            date__year=y
        ).aggregate(
            total=Sum('amount'),
            count=Count('id'),
            avg=Avg('amount')
        )
        
        yearly_comparison.append({
            'year': y,
            'total': yearly_stats['total'] or 0,
            'count': yearly_stats['count'] or 0,
            'avg': yearly_stats['avg'] or 0,
        })
    
    # Oylik tahlil
    monthly_analysis = Income.get_yearly_summary(request.user, year)
    
    # Kategoriyalar o'zgarishi
    category_growth = []
    categories = IncomeCategory.objects.filter(
        Q(user=request.user) | Q(is_default=True)
    )
    
    for category in categories:
        current_year_total = Income.objects.filter(
            user=request.user,
            category=category,
            date__year=year
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        previous_year_total = Income.objects.filter(
            user=request.user,
            category=category,
            date__year=year-1
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        if previous_year_total > 0:
            growth = ((current_year_total - previous_year_total) / previous_year_total) * 100
        else:
            growth = 100 if current_year_total > 0 else 0
        
        category_growth.append({
            'category': category.name,
            'current_year': current_year_total,
            'previous_year': previous_year_total,
            'growth': growth,
            'color': category.color
        })
    
    # Prognoz (oddiy hisob)
    current_month = timezone.now().month
    months_passed = min(current_month, 12)
    
    if months_passed > 0:
        year_to_date = Income.objects.filter(
            user=request.user,
            date__year=year,
            date__month__lte=months_passed
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_avg = year_to_date / months_passed
        forecast = monthly_avg * 12
    else:
        forecast = 0
    
    context = {
        'year': year,
        'yearly_comparison': yearly_comparison,
        'monthly_analysis': monthly_analysis,
        'category_growth': category_growth,
        'forecast': forecast,
        'available_years': range(timezone.now().year - 5, timezone.now().year + 1),
    }
    
    return render(request, 'income/income_analytics.html', context)


@login_required
def income_export(request):
    """Kirimlarni export qilish"""
    incomes = get_user_incomes(request)
    
    # Filtrlash
    filter_form = IncomeFilterForm(request.GET, user=request.user)
    if filter_form.is_valid():
        incomes = apply_filters(incomes, filter_form)
    
    format_type = request.GET.get('format', 'excel')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="incomes_{timezone.now().date()}.csv"'
        
        response.write('\ufeff')  # UTF-8 BOM
        
        writer = csv.writer(response)
        
        # Sarlavhalar
        headers = [
            'ID', 'Sana', 'Manba', 'Kategoriya', 
            'Miqdor', 'Valyuta', 'Net Miqdor', 'Soliq',
            'To\'lov Usuli', 'Holat', 'Takrorlanuvchi',
            'Tavsif', 'Yaratilgan', 'Yangilangan'
        ]
        writer.writerow(headers)
        
        # Ma'lumotlar
        for income in incomes:
            writer.writerow([
                str(income.uuid)[:8],
                income.date.isoformat(),
                income.source,
                income.category.name,
                str(income.amount),
                income.currency,
                str(income.net_amount),
                str(income.tax_amount),
                income.get_payment_method_display(),
                income.get_status_display(),
                'Ha' if income.is_recurring else 'Yo\'q',
                income.description or '',
                income.created_at.strftime('%Y-%m-%d %H:%M'),
                income.updated_at.strftime('%Y-%m-%d %H:%M'),
            ])
        
        return response
    
    elif format_type == 'excel':
        output = io.BytesIO()
        
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Kirimlar')
        
        # Formatlar
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3b82f6',
            'color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})
        money_format = workbook.add_format({'num_format': '#,##0.00'})
        
        # Sarlavhalar
        headers = [
            'ID', 'Sana', 'Manba', 'Kategoriya', 
            'Miqdor', 'Valyuta', 'Net Miqdor', 'Soliq',
            'To\'lov Usuli', 'Holat', 'Takrorlanuvchi',
            'Tavsif', 'Yaratilgan', 'Yangilangan'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Ma'lumotlar
        for row, income in enumerate(incomes, start=1):
            worksheet.write(row, 0, str(income.uuid)[:8])
            worksheet.write(row, 1, income.date, date_format)
            worksheet.write(row, 2, income.source)
            worksheet.write(row, 3, income.category.name)
            worksheet.write(row, 4, float(income.amount), money_format)
            worksheet.write(row, 5, income.currency)
            worksheet.write(row, 6, float(income.net_amount), money_format)
            worksheet.write(row, 7, float(income.tax_amount), money_format)
            worksheet.write(row, 8, income.get_payment_method_display())
            worksheet.write(row, 9, income.get_status_display())
            worksheet.write(row, 10, 'Ha' if income.is_recurring else 'Yo\'q')
            worksheet.write(row, 11, income.description or '')
            worksheet.write(row, 12, income.created_at, datetime_format)
            worksheet.write(row, 13, income.updated_at, datetime_format)
        
        # Kenglikni sozlash
        worksheet.set_column('A:A', 10)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 10)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 10)
        worksheet.set_column('I:I', 15)
        worksheet.set_column('J:J', 15)
        worksheet.set_column('K:K', 15)
        worksheet.set_column('L:L', 40)
        worksheet.set_column('M:M', 18)
        worksheet.set_column('N:N', 18)
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="incomes_{timezone.now().date()}.xlsx"'
        
        return response
    
    return redirect('income:list')


# ================ QUICK ACTIONS ================

@login_required
@require_http_methods(["GET", "POST"])
def quick_add(request):
    """Tez kirim qo'shish"""
    if request.method == 'POST':
        form = QuickIncomeForm(request.POST, user=request.user)
        if form.is_valid():
            income = Income.objects.create(
                user=request.user,
                amount=form.cleaned_data['amount'],
                category=form.cleaned_data['category'],
                source=form.cleaned_data.get('source', ''),
                description=form.cleaned_data.get('description', ''),
                date=timezone.now().date(),
                time=timezone.now().time(),
                currency='UZS',  # Default
                status='received',
                payment_method='cash',
            )
            
            # Maqsadlarni yangilash
            update_income_goals(request.user, income)
            
            return JsonResponse({
                'success': True,
                'message': _('Kirim muvaffaqiyatli qo\'shildi!'),
                'income': {
                    'id': str(income.uuid),
                    'amount': str(income.amount),
                    'source': income.source,
                    'category': income.category.name,
                    'date': income.date.strftime('%Y-%m-%d'),
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': _('Formani to\'ldirishda xatolik!')
            }, status=400)
    
    # GET so'rovi uchun formani qaytarish
    form = QuickIncomeForm(user=request.user)
    
    html = render_to_string('income/partials/quick_add_modal.html', 
                          {'form': form}, request)
    return JsonResponse({'html': html})


@login_required
@require_POST
def bulk_delete(request):
    """Bir nechta kirimlarni o'chirish"""
    try:
        data = json.loads(request.body)
        income_ids = data.get('ids', [])
        
        if not income_ids:
            return JsonResponse({
                'success': False,
                'message': _('Hech narsa tanlanmadi!')
            }, status=400)
        
        # Faqat foydalanuvchining kirimlarini o'chirish
        deleted_count, _ = Income.objects.filter(
            uuid__in=income_ids,
            user=request.user
        ).delete()
        
        # Maqsadlarni yangilash
        update_income_goals(request.user)
        
        messages.success(request, 
            _('{} ta kirim o\'chirildi!').format(deleted_count))
        
        return JsonResponse({
            'success': True,
            'message': _('{} ta kirim o\'chirildi!').format(deleted_count),
            'deleted_count': deleted_count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_POST
def bulk_update_category(request):
    """Bir nechta kirimlarni kategoriyasini yangilash"""
    try:
        data = json.loads(request.body)
        income_ids = data.get('ids', [])
        category_id = data.get('category_id')
        
        if not income_ids or not category_id:
            return JsonResponse({
                'success': False,
                'message': _('Kirimlar va kategoriya tanlanishi kerak!')
            }, status=400)
        
        # Kategoriyani tekshirish
        try:
            category = IncomeCategory.objects.get(
                id=category_id,
                user=request.user
            )
        except IncomeCategory.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': _('Noto\'g\'ri kategoriya!')
            }, status=400)
        
        # Kirimlarni yangilash
        updated_count = Income.objects.filter(
            uuid__in=income_ids,
            user=request.user
        ).update(category=category)
        
        # Maqsadlarni yangilash
        update_income_goals(request.user)
        
        messages.success(request, 
            _('{} ta kirim kategoriyasi yangilandi!').format(updated_count))
        
        return JsonResponse({
            'success': True,
            'message': _('{} ta kirim kategoriyasi yangilandi!').format(updated_count),
            'updated_count': updated_count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ================ GOAL VIEWS ================

@login_required
def goal_list(request):
    """Kirim maqsadlari ro'yxati"""
    goals = IncomeGoal.objects.filter(
        user=request.user
    ).prefetch_related('categories').order_by('-created_at')
    
    # Har bir maqsad uchun progressni yangilash
    for goal in goals:
        goal.update_status()
    
    context = {'goals': goals}
    return render(request, 'income/goal_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def goal_create(request):
    """Yangi kirim maqsadi yaratish"""
    if request.method == 'POST':
        form = IncomeGoalForm(request.POST, user=request.user)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            form.save_m2m()  # Many-to-many saqlash
            
            messages.success(request, _('Maqsad muvaffaqiyatli yaratildi!'))
            return redirect('income:goals')
    else:
        form = IncomeGoalForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'income/goal_form.html', context)


@login_required
def goal_detail(request, pk):
    """Maqsadni batafsil ko'rish"""
    goal = get_object_or_404(IncomeGoal, pk=pk, user=request.user)
    
    # Maqsadga tegishli kirimlar
    related_incomes = Income.objects.filter(
        user=request.user,
        date__range=[goal.start_date, goal.end_date],
        status='received'
    )
    
    if goal.categories.exists():
        related_incomes = related_incomes.filter(
            category__in=goal.categories.all()
        )
    
    # Oylik progress
    monthly_progress = []
    current_date = goal.start_date
    
    while current_date <= min(goal.end_date, timezone.now().date()):
        month_start = current_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_incomes = related_incomes.filter(
            date__range=[month_start, month_end]
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_progress.append({
            'month': month_start.strftime('%B %Y'),
            'amount': month_incomes,
            'target': goal.target_amount / 12,  # Taxminiy oylik maqsad
        })
        
        current_date = month_end + timedelta(days=1)
    
    context = {
        'goal': goal,
        'related_incomes': related_incomes[:10],
        'monthly_progress': monthly_progress,
    }
    
    return render(request, 'income/goal_detail.html', context)


# ================ API ENDPOINTS ================

@login_required
@require_GET
def api_monthly_summary(request):
    """Oylik xulosa API"""
    year = request.GET.get('year', timezone.now().year)
    
    try:
        year = int(year)
    except ValueError:
        year = timezone.now().year
    
    monthly_data = Income.get_yearly_summary(request.user, year)
    
    return JsonResponse({
        'year': year,
        'data': monthly_data,
    })


@login_required
@require_GET
def api_category_stats(request):
    """Kategoriya statistikasi API"""
    categories = IncomeCategory.objects.filter(
        Q(user=request.user) | Q(is_default=True)
    )
    
    stats = []
    for category in categories:
        category_stats = Income.objects.filter(
            user=request.user,
            category=category
        ).aggregate(
            total=Sum('amount'),
            count=Count('id'),
            avg=Avg('amount')
        )
        
        stats.append({
            'id': category.id,
            'name': category.name,
            'color': category.color,
            'icon': category.icon,
            'total': category_stats['total'] or 0,
            'count': category_stats['count'] or 0,
            'avg': category_stats['avg'] or 0,
        })
    
    return JsonResponse({'categories': stats})


@login_required
@csrf_exempt
@require_POST
def api_duplicate_income(request, uuid):
    """Kirimni nusxalash API"""
    try:
        income = Income.objects.get(uuid=uuid, user=request.user)
        
        # Yangi kirim yaratish (nusxalash)
        new_income = Income.objects.create(
            user=request.user,
            amount=income.amount,
            currency=income.currency,
            category=income.category,
            source=income.source,
            source_obj=income.source_obj,
            payment_method=income.payment_method,
            date=timezone.now().date(),
            time=timezone.now().time(),
            status='received',
            description=income.description,
            is_taxable=income.is_taxable,
            tax_amount=income.tax_amount,
            is_recurring=False,  # Nusxalangan kirim takrorlanmaydi
        )
        
        # Teglarni nusxalash
        new_income.tags.set(income.tags.all())
        
        return JsonResponse({
            'success': True,
            'message': _('Kirim muvaffaqiyatli nusxalandi!'),
            'new_uuid': str(new_income.uuid)
        })
    except Income.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': _('Kirim topilmadi!')
        }, status=404)


# ================ HELPER FUNCTIONS ================

def update_income_goals(user, income=None):
    """Kirim maqsadlarini yangilash"""
    goals = IncomeGoal.objects.filter(
        user=user,
        status='active'
    )
    
    for goal in goals:
        # Agar yangi kirim qo'shilgan bo'lsa va u maqsadga tegishli bo'lsa
        if income:
            if (goal.start_date <= income.date <= goal.end_date and
                income.status == 'received'):
                
                # Agar kategoriya cheklangan bo'lsa
                if goal.categories.exists():
                    if income.category in goal.categories.all():
                        goal.update_status()
                else:
                    goal.update_status()
        else:
            # Umuman yangilash
            goal.update_status()


@login_required
@require_GET
def get_autocomplete_sources(request):
    """Manbalar avtomatik to'ldirish"""
    query = request.GET.get('q', '')
    
    if query:
        sources = Income.objects.filter(
            user=request.user,
            source__icontains=query
        ).values_list('source', flat=True).distinct()[:10]
    else:
        sources = Income.objects.filter(
            user=request.user
        ).values_list('source', flat=True).distinct()[:10]
    
    return JsonResponse({'sources': list(sources)})


# ================ DASHBOARD WIDGETS ================

@login_required
@require_GET
def dashboard_stats(request):
    """Dashboard uchun statistikalar"""
    today = timezone.now().date()
    
    # Bugungi kirim
    today_income = Income.objects.filter(
        user=request.user,
        date=today,
        status='received'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Bu hafta kirim
    week_start = today - timedelta(days=today.weekday())
    week_income = Income.objects.filter(
        user=request.user,
        date__gte=week_start,
        status='received'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Bu oy kirim
    month_start = today.replace(day=1)
    month_income = Income.objects.filter(
        user=request.user,
        date__gte=month_start,
        status='received'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Oxirgi 5 kirim
    recent_incomes = Income.objects.filter(
        user=request.user
    ).select_related('category').order_by('-date', '-created_at')[:5]
    
    recent_incomes_list = []
    for income in recent_incomes:
        recent_incomes_list.append({
            'uuid': str(income.uuid),
            'source': income.source,
            'amount': str(income.amount),
            'currency': income.currency,
            'category': income.category.name,
            'date': income.date.strftime('%Y-%m-%d'),
            'color': income.category.color,
        })
    
    # Faol maqsadlar
    active_goals = IncomeGoal.objects.filter(
        user=request.user,
        status='active'
    )[:3]
    
    goals_list = []
    for goal in active_goals:
        goals_list.append({
            'id': goal.id,
            'name': goal.name,
            'progress': goal.progress_percentage,
            'current': goal.current_amount,
            'target': goal.target_amount,
            'remaining_days': goal.remaining_days,
        })
    
    return JsonResponse({
        'today_income': str(today_income),
        'week_income': str(week_income),
        'month_income': str(month_income),
        'recent_incomes': recent_incomes_list,
        'active_goals': goals_list,
    })