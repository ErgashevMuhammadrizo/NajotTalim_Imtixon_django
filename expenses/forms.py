from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Expense, ExpenseCategory, ExpenseTag, Budget


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'icon', 'color', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _("Kategoriya nomi")
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'fas fa-shopping-cart'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'style': 'height: 38px;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _("Kategoriya tavsifi...")
            }),
        }


class ExpenseForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=ExpenseTag.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'multiple': 'multiple'}),
        required=False,
        label=_("Teglar")
    )
    
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'currency', 'description', 'date', 
                 'payment_method', 'location', 'receipt_image', 'tags']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'currency': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('UZS', 'UZS - O\'zbek so\'mi'),
                ('USD', 'USD - AQSh dollari'),
                ('EUR', 'EUR - Yevro'),
                ('RUB', 'RUB - Rossiya rubli'),
            ]),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _("Chiqim izohi...")
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'value': timezone.now().date()
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _("Manzil (ixtiyoriy)")
            }),
            'receipt_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Faqat foydalanuvchining kategoriyalari
            self.fields['category'].queryset = ExpenseCategory.objects.filter(
                user=self.user, is_active=True
            )
            # Faqat foydalanuvchining teglari
            self.fields['tags'].queryset = ExpenseTag.objects.filter(user=self.user)
        
        # Valyuta kursini olish uchun yashirin maydon
        self.fields['exchange_rate'] = forms.DecimalField(
            required=False,
            widget=forms.HiddenInput(),
            initial=1.0
        )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError(_("Summa 0 dan katta bo'lishi kerak"))
        return amount
    
    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date > timezone.now().date():
            raise forms.ValidationError(_("Kelajak sanasini kiritish mumkin emas"))
        return date


class QuickExpenseForm(forms.ModelForm):
    """Tez chiqim qo'shish uchun form"""
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'description']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _("Summa"),
                'step': '0.01',
                'min': '0'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _("Qisqa izoh (ixtiyoriy)")
            }),
        }


class ExpenseTagForm(forms.ModelForm):
    class Meta:
        model = ExpenseTag
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _("Teg nomi")
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'style': 'height: 38px;'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if self.user and ExpenseTag.objects.filter(user=self.user, name=name).exists():
            raise forms.ValidationError(_("Bu nom bilan teg allaqachon mavjud"))
        return name


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount', 'currency', 'period', 
                 'start_date', 'end_date', 'alert_threshold', 'send_alerts']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'period': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'alert_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100'
            }),
            'send_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['category'].queryset = ExpenseCategory.objects.filter(
                user=self.user, is_active=True
            )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if end_date and start_date and end_date < start_date:
            raise forms.ValidationError(_("Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas"))
        
        return cleaned_data