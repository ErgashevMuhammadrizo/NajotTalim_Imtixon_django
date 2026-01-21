# expenses/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
import csv
import xlwt

from .models import Expense, ExpenseCategory, ExpenseTag, Budget
from .forms import ExpenseForm, ExpenseCategoryForm, ExpenseTagForm, BudgetForm, QuickExpenseForm
from income.models import Income


# ==================== Expense Views ====================

class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Expense.objects.filter(user=self.request.user).select_related('category')
        
        # Filtrlash
        category = self.request.GET.get('category')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        currency = self.request.GET.get('currency')
        payment_method = self.request.GET.get('payment_method')
        search = self.request.GET.get('search')
        
        if category:
            queryset = queryset.filter(category_id=category)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if currency:
            queryset = queryset.filter(currency=currency)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(category__name__icontains=search) |
                Q(location__icontains=search)
            )
        
        return queryset.order_by('-date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.filter(user=self.request.user, is_active=True)
        context['total_amount'] = self.get_queryset().aggregate(
            total=Sum('amount_in_uzs')
        )['total'] or 0
        
        # Filter parametrlari
        context['filter_params'] = {
            'category': self.request.GET.get('category', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'currency': self.request.GET.get('currency', ''),
            'payment_method': self.request.GET.get('payment_method', ''),
            'search': self.request.GET.get('search', ''),
        }
        
        return context


class ExpenseDetailView(LoginRequiredMixin, DetailView):
    model = Expense
    template_name = 'expenses/expense_detail.html'
    context_object_name = 'expense'
    
    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # Valyuta kursini sozlash
        currency = form.cleaned_data.get('currency', 'UZS')
        if currency != 'UZS':
            # Bu yerda valyuta kursi API dan olish mumkin
            form.instance.exchange_rate = 1.0  # Default
        else:
            form.instance.exchange_rate = 1.0
        
        response = super().form_valid(form)
        messages.success(self.request, _("Chiqim muvaffaqiyatli qo'shildi!"))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_create'] = True
        return context


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    
    def get_success_url(self):
        return reverse_lazy('expenses:detail', kwargs={'pk': self.object.pk})
    
    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Chiqim muvaffaqiyatli yangilandi!"))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_create'] = False
        return context


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expenses:list')
    
    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, _("Chiqim muvaffaqiyatli o'chirildi!"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def quick_create_expense(request):
    """Tez chiqim qo'shish (AJAX uchun)"""
    form = QuickExpenseForm(request.POST)
    
    if form.is_valid():
        expense = form.save(commit=False)
        expense.user = request.user
        expense.currency = 'UZS'
        expense.exchange_rate = 1.0
        expense.amount_in_uzs = expense.amount
        expense.save()
        
        return JsonResponse({
            'success': True,
            'message': _("Chiqim qo'shildi!"),
            'expense_id': str(expense.id)
        })
    
    return JsonResponse({
        'success': False,
        'errors': form.errors
    }, status=400)


# ==================== Category Views ====================

class CategoryListView(LoginRequiredMixin, ListView):
    model = ExpenseCategory
    template_name = 'expenses/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user).annotate(
            total_expenses=Sum('expenses__amount_in_uzs'),
            expense_count=Count('expenses')
        ).order_by('-total_expenses')


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('expenses:category_list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, _("Kategoriya muvaffaqiyatli qo'shildi!"))
        return response


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('expenses:category_list')
    
    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Kategoriya muvaffaqiyatli yangilandi!"))
        return response


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = ExpenseCategory
    template_name = 'expenses/category_confirm_delete.html'
    success_url = reverse_lazy('expenses:category_list')
    
    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        # Kategoriyaga bog'liq chiqimlarni tekshirish
        if self.object.expenses.exists():
            messages.error(self.request, 
                _("Bu kategoriyaga bog'liq chiqimlar mavjud. Iltimos, avval ularni o'chiring yoki boshqa kategoriyaga o'tkazing."))
            return redirect('expenses:category_list')
        
        messages.success(self.request, _("Kategoriya muvaffaqiyatli o'chirildi!"))
        return super().form_valid(form)


# ==================== Budget Views ====================

class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    template_name = 'expenses/budget_list.html'
    context_object_name = 'budgets'
    
    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user, is_active=True).select_related('category')


class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'expenses/budget_form.html'
    success_url = reverse_lazy('expenses:budget_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, _("Byudjet muvaffaqiyatli qo'shildi!"))
        return response


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'expenses/budget_form.html'
    success_url = reverse_lazy('expenses:budget_list')
    
    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Byudjet muvaffaqiyatli yangilandi!"))
        return response


class BudgetDeleteView(LoginRequiredMixin, DeleteView):
    model = Budget
    template_name = 'expenses/budget_confirm_delete.html'
    success_url = reverse_lazy('expenses:budget_list')
    
    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, _("Byudjet muvaffaqiyatli o'chirildi!"))
        return super().form_valid(form)


# ==================== API Views ====================

@login_required
def expense_stats(request):
    """Chiqim statistikasi API"""
    period = request.GET.get('period', 'month')  # day, week, month, year
    currency = request.GET.get('currency', 'UZS')
    
    today = timezone.now().date()
    stats = {}
    
    if period == 'day':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        start_date = today.replace(day=1)
        # Oxirgi oy kuni
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
    else:  # year
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    
    # Chiqimlar
    expenses = Expense.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    )
    
    # Jami chiqim
    total_expense = expenses.aggregate(total=Sum('amount_in_uzs'))['total'] or 0
    
    # Kategoriyalar bo'yicha
    category_stats = expenses.values(
        'category__name', 'category__color', 'category__icon'
    ).annotate(
        total=Sum('amount_in_uzs'),
        count=Count('id')
    ).order_by('-total')
    
    # Kunlik trend
    daily_trend = expenses.values('date').annotate(
        total=Sum('amount_in_uzs')
    ).order_by('date')
    
    stats = {
        'total_expense': float(total_expense),
        'expense_count': expenses.count(),
        'category_stats': list(category_stats),
        'daily_trend': list(daily_trend),
        'period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    }
    
    return JsonResponse(stats)


@login_required
def budget_status(request):
    """Byudjet holati API"""
    budgets = Budget.objects.filter(user=request.user, is_active=True)
    
    budget_status = []
    for budget in budgets:
        budget_status.append({
            'id': str(budget.id),
            'category': budget.category.name,
            'category_color': budget.category.color,
            'budget_amount': float(budget.amount),
            'spent_amount': float(budget.spent_amount),
            'remaining_amount': float(budget.remaining_amount),
            'usage_percentage': float(budget.usage_percentage),
            'is_over_budget': budget.is_over_budget(),
            'should_alert': budget.should_alert(),
            'period': budget.get_period_display(),
        })
    
    return JsonResponse({'budgets': budget_status})


# ==================== Export Views ====================

@login_required
def export_expenses_csv(request):
    """Chiqimlarni CSV formatda eksport qilish"""
    expenses = Expense.objects.filter(user=request.user)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Category', 'Amount', 'Currency', 'Description', 'Payment Method', 'Location'])
    
    for expense in expenses:
        writer.writerow([
            expense.date,
            expense.category.name if expense.category else '',
            expense.amount,
            expense.currency,
            expense.description,
            expense.get_payment_method_display(),
            expense.location or ''
        ])
    
    return response


@login_required
def export_expenses_excel(request):
    """Chiqimlarni Excel formatda eksport qilish"""
    expenses = Expense.objects.filter(user=request.user)
    
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="expenses.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Expenses')
    
    # Sarlavhalar
    row_num = 0
    columns = ['Date', 'Category', 'Amount', 'Currency', 'Description', 'Payment Method', 'Location']
    
    for col_num, column_title in enumerate(columns):
        ws.write(row_num, col_num, column_title)
    
    # Ma'lumotlar
    for expense in expenses:
        row_num += 1
        ws.write(row_num, 0, str(expense.date))
        ws.write(row_num, 1, expense.category.name if expense.category else '')
        ws.write(row_num, 2, float(expense.amount))
        ws.write(row_num, 3, expense.currency)
        ws.write(row_num, 4, expense.description)
        ws.write(row_num, 5, expense.get_payment_method_display())
        ws.write(row_num, 6, expense.location or '')
    
    wb.save(response)
    return response


# ==================== Dashboard Views ====================

# ==================== Dashboard Views ====================

@login_required
def dashboard_summary(request):
    """Dashboard uchun umumiy ma'lumotlar - Valyuta bilan"""
    currency = request.GET.get('currency', 'UZS')
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # Valyuta kurslari (1 USD = 12500 UZS, 1 EUR = 13500 UZS, 1 CNY = 1740 UZS)
    exchange_rates = {
        'UZS': 1,
        'USD': 12500,
        'EUR': 13500,
        'CNY': 1740,
        'RUB': 130,
    }
    rate = exchange_rates.get(currency, 1)
    
    # Kirim statistikasi - har doim valyutada saqlanadi, UZS ga konvertatsiya qilish kerak
    incomes = Income.objects.filter(
        user=request.user,
        status='received'
    ).values('amount', 'currency')
    
    total_income_uzs = Decimal('0')
    for inc in incomes:
        amount = Decimal(str(inc['amount']))
        inc_currency = inc['currency']
        inc_rate = exchange_rates.get(inc_currency, 1)
        total_income_uzs += amount * inc_rate
    
    total_income_uzs = float(total_income_uzs)
    
    # Chiqim statistikasi (UZS da saqlangan)
    total_expense_uzs = Expense.objects.filter(
        user=request.user
    ).aggregate(total=Sum('amount_in_uzs'))['total'] or Decimal('0')
    total_expense_uzs = float(total_expense_uzs)
    
    # Balansi hisoblash (kirim - chiqim) UZS da
    current_balance_uzs = total_income_uzs - total_expense_uzs
    
    # O'tgan oy bilan taqqoslash
    if month_start.month == 1:
        prev_month_start = month_start.replace(year=month_start.year - 1, month=12)
    else:
        prev_month_start = month_start.replace(month=month_start.month - 1)
    
    prev_month_end = month_start - timedelta(days=1)
    
    # O'tgan oy kirim UZS
    prev_incomes = Income.objects.filter(
        user=request.user,
        date__gte=prev_month_start,
        date__lte=prev_month_end,
        status='received'
    ).values('amount', 'currency')
    
    prev_income_uzs = Decimal('0')
    for inc in prev_incomes:
        amount = Decimal(str(inc['amount']))
        inc_currency = inc['currency']
        inc_rate = exchange_rates.get(inc_currency, 1)
        prev_income_uzs += amount * inc_rate
    
    prev_income_uzs = float(prev_income_uzs)
    
    # O'tgan oy chiqim UZS
    prev_expense_uzs = Expense.objects.filter(
        user=request.user,
        date__gte=prev_month_start,
        date__lte=prev_month_end
    ).aggregate(total=Sum('amount_in_uzs'))['total'] or Decimal('0')
    prev_expense_uzs = float(prev_expense_uzs)
    
    # O'zgarish foizini hisoblash
    if prev_income_uzs > 0:
        income_change = ((total_income_uzs - prev_income_uzs) / prev_income_uzs) * 100
    else:
        income_change = 0 if total_income_uzs == 0 else 100
    
    if prev_expense_uzs > 0:
        expense_change = ((total_expense_uzs - prev_expense_uzs) / prev_expense_uzs) * 100
    else:
        expense_change = 0 if total_expense_uzs == 0 else 100
    
    if (prev_income_uzs - prev_expense_uzs) > 0:
        balance_change = ((current_balance_uzs - (prev_income_uzs - prev_expense_uzs)) / (prev_income_uzs - prev_expense_uzs)) * 100
    else:
        balance_change = 0 if current_balance_uzs == 0 else 100
    
    # Oxirgi tranzaksiyalar
    recent_transactions = []
    
    # Oxirgi kirim
    income_list = Income.objects.filter(
        user=request.user,
        status='received'
    ).select_related('category').values(
        'uuid', 'amount', 'currency', 'category__name', 'category__icon', 'date', 'description'
    ).order_by('-date')[:5]
    
    for income in income_list:
        # Income o'z valyutasida saqlanadi, UZS ga o'girish kerak
        amount_original = float(income['amount'])
        inc_currency = income['currency']
        inc_rate = exchange_rates.get(inc_currency, 1)
        amount_uzs = amount_original * inc_rate
        amount_converted = amount_uzs / rate
        
        recent_transactions.append({
            'id': str(income['uuid']),
            'type': 'income',
            'amount': amount_converted,
            'currency': income['currency'],
            'category_name': income['category__name'],
            'category_icon': income['category__icon'] or 'fas fa-money-bill',
            'date': income['date'].isoformat(),
            'description': income['description'] or '',
        })
    
    # Oxirgi chiqim
    expense_list = Expense.objects.filter(
        user=request.user
    ).select_related('category').values(
        'id', 'amount', 'amount_in_uzs', 'currency', 'category__name', 'category__icon', 'date', 'description'
    ).order_by('-date')[:5]
    
    for expense in expense_list:
        # Expense amount_in_uzs da saqlanadi, shuning uchun konvertatsiya kerak
        amount_uzs = float(expense['amount_in_uzs'])
        amount_converted = amount_uzs / rate
        
        recent_transactions.append({
            'id': str(expense['id']),
            'type': 'expense',
            'amount': amount_converted,
            'currency': expense['currency'],
            'category_name': expense['category__name'],
            'category_icon': expense['category__icon'] or 'fas fa-shopping-cart',
            'date': expense['date'].isoformat(),
            'description': expense['description'] or '',
        })
    
    # Sana bo'yicha saralash
    recent_transactions.sort(key=lambda x: x['date'], reverse=True)
    recent_transactions = recent_transactions[:5]
    
    # Valyutaga konvertatsiya qilish
    return JsonResponse({
        'total_income': total_income_uzs / rate,
        'total_expense': total_expense_uzs / rate,
        'current_balance': current_balance_uzs / rate,
        'income_change': income_change,
        'expense_change': expense_change,
        'balance_change': balance_change,
        'currency': currency,
        'recent_transactions': recent_transactions,
    })



@login_required
def dashboard_chart_data(request):
    """Chart uchun ma'lumotlar"""
    period = int(request.GET.get('period', 30))
    currency = request.GET.get('currency', 'UZS')
    
    # Valyuta kurslari (1 USD = 12500 UZS, 1 EUR = 13500 UZS, 1 CNY = 1740 UZS)
    exchange_rates = {
        'UZS': 1,
        'USD': 12500,
        'EUR': 13500,
        'CNY': 1740,
        'RUB': 130,
    }
    rate = exchange_rates.get(currency, 1)
    
    today = timezone.now().date()
    start_date = today - timedelta(days=period)
    
    # Kirim ma'lumotlari (valyutada saqlanadi)
    incomes = Income.objects.filter(
        user=request.user,
        date__gte=start_date,
        status='received'
    ).values('date', 'amount', 'currency').order_by('date')
    
    # Chiqim ma'lumotlari (UZS da saqlanadi)
    expenses = Expense.objects.filter(
        user=request.user,
        date__gte=start_date
    ).values('date', 'amount_in_uzs').order_by('date')
    
    # Dictionary-ga saqlash - UZS da
    income_dict = {}
    for item in incomes:
        date_str = str(item['date'])
        amount = float(item['amount'])
        inc_currency = item['currency']
        inc_rate = exchange_rates.get(inc_currency, 1)
        amount_uzs = amount * inc_rate
        
        if date_str not in income_dict:
            income_dict[date_str] = 0
        income_dict[date_str] += amount_uzs
    
    expense_dict = {}
    for item in expenses:
        date_str = str(item['date'])
        amount_uzs = float(item['amount_in_uzs'] or 0)
        
        if date_str not in expense_dict:
            expense_dict[date_str] = 0
        expense_dict[date_str] += amount_uzs
    
    # Sana diapazoni
    income_data = []
    expense_data = []
    labels = []
    
    current = start_date
    while current <= today:
        date_str = str(current)
        labels.append(current.strftime('%m-%d'))
        
        # UZS-dan tanlangan valyutaga konvertatsiya
        income_uzs = income_dict.get(date_str, 0)
        expense_uzs = expense_dict.get(date_str, 0)
        
        income_data.append(income_uzs / rate if rate > 0 else 0)
        expense_data.append(expense_uzs / rate if rate > 0 else 0)
        
        current += timedelta(days=1)
    
    return JsonResponse({
        'labels': labels,
        'income_data': income_data,
        'expense_data': expense_data,
        'currency': currency,
    })


@login_required
def dashboard_category_stats(request):
    """Kategoriyalar bo'yicha statistika"""
    period = request.GET.get('period', 'month')
    currency = request.GET.get('currency', 'UZS')
    
    # Valyuta kurslari (1 USD = 12500 UZS, 1 EUR = 13500 UZS)
    exchange_rates = {
        'UZS': 1,
        'USD': 12500,
        'EUR': 13500,
    }
    rate = exchange_rates.get(currency, 1)
    
    today = timezone.now().date()
    
    # Davr tanlash
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
    elif period == 'month':
        start_date = today.replace(day=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
    else:
        start_date = today.replace(day=1)
    
    # Kategoriyalar bo'yicha chiqim (UZS da saqlanadi)
    category_stats = Expense.objects.filter(
        user=request.user,
        date__gte=start_date
    ).values('category__id', 'category__name', 'category__icon', 'category__color').annotate(
        total=Sum('amount_in_uzs'),
        count=Count('id')
    ).order_by('-total')
    
    # Jami chiqim (UZS da)
    total_expense_uzs = 0
    for cat in category_stats:
        amount = cat['total'] or 0
        if isinstance(amount, Decimal):
            amount = float(amount)
        total_expense_uzs += amount
    
    categories = []
    for cat in category_stats:
        amount_uzs = cat['total'] or 0
        if isinstance(amount_uzs, Decimal):
            amount_uzs = float(amount_uzs)
        
        amount_converted = amount_uzs / rate if rate > 0 else 0
        percentage = (amount_uzs / total_expense_uzs * 100) if total_expense_uzs > 0 else 0
        
        categories.append({
            'id': str(cat['category__id']),
            'name': cat['category__name'],
            'icon': cat['category__icon'] or 'fas fa-folder',
            'color': cat['category__color'],
            'total': round(amount_converted, 2),
            'count': cat['count'],
            'percentage': round(percentage, 1),
        })
    
    return JsonResponse(categories, safe=False)

@login_required
def dashboard_view(request):
    """Dashboard asosiy sahifasi"""
    from income.models import IncomeCategory
    
    context = {
        'expense_categories': ExpenseCategory.objects.filter(
            user=request.user, is_active=True
        ),
        'income_categories': IncomeCategory.objects.filter(
            user=request.user
        ).filter(Q(is_default=True) | Q(user=request.user)),
    }
    
    return render(request, 'dashboard.html', context)