from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from .models import (
    Income, IncomeCategory, IncomeSource, IncomeTag, 
    IncomeTemplate, IncomeGoal
)


class IncomeCategoryForm(forms.ModelForm):
    """Kirim kategoriyasi formasi"""
    class Meta:
        model = IncomeCategory
        fields = ['name', 'icon', 'color', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Kategoriya nomi'),
                'autofocus': True
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('FontAwesome icon kodi (masalan: fas fa-money-bill-wave)'),
                'id': 'icon-input'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control form-control-color',
                'type': 'color',
                'id': 'color-picker'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Qisqacha tavsif (ixtiyoriy)'),
                'style': 'resize: none;'
            }),
        }
        labels = {
            'name': _('Kategoriya nomi'),
            'icon': _('Ikonka'),
            'color': _('Rang'),
            'description': _('Tavsif')
        }
    
    def clean_name(self):
        """Kategoriya nomini tozalash"""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 2:
                raise ValidationError(_("Kategoriya nomi kamida 2 belgidan iborat bo'lishi kerak"))
        return name


class IncomeSourceForm(forms.ModelForm):
    """Kirim manbasi formasi"""
    class Meta:
        model = IncomeSource
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Manba nomi (masalan: Kompaniya XYZ)')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Qo\'shimcha ma\'lumot (ixtiyoriy)')
            }),
        }
        labels = {
            'name': _('Manba nomi'),
            'description': _('Tavsif')
        }


class IncomeTagForm(forms.ModelForm):
    """Kirim tegi formasi"""
    class Meta:
        model = IncomeTag
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Teg nomi')
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control form-control-color',
                'type': 'color',
                'value': '#3b82f6'
            }),
        }
        labels = {
            'name': _('Teg nomi'),
            'color': _('Rang')
        }


class IncomeForm(forms.ModelForm):
    """Kirim qo'shish/tahrirlash formasi"""
    class Meta:
        model = Income
        fields = [
            'amount', 'currency', 'category', 'source',
            'source_obj', 'payment_method', 'date', 'time',
            'status', 'description', 'attachment',
            'is_recurring', 'recurrence_pattern', 'next_occurrence',
            'tags', 'is_taxable', 'tax_amount'
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': _('Kategoriya tanlang')
            }),
            'source': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Kirim manbasi (masalan: Ish haqi)'),
                'list': 'source-suggestions'
            }),
            'source_obj': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': _('Manba tanlang yoki yangisini yozing')
            }),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'max': timezone.now().date().isoformat()
            }),
            'time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Qo\'shimcha ma\'lumot (ixtiyoriy)'),
                'style': 'resize: none;'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx'
            }),
            'is_recurring': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-bs-toggle': 'collapse',
                'data-bs-target': '#recurringOptions'
            }),
            'next_occurrence': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'form-control select2-multiple',
                'data-placeholder': _('Teglarni tanlang')
            }),
            'is_taxable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tax_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
                'readonly': True
            }),
        }
        labels = {
            'amount': _('Miqdor'),
            'currency': _('Valyuta'),
            'category': _('Kategoriya'),
            'source': _('Manba'),
            'source_obj': _('Manba obyekti'),
            'payment_method': _('To\'lov usuli'),
            'date': _('Sana'),
            'time': _('Vaqt'),
            'status': _('Holat'),
            'description': _('Tavsif'),
            'attachment': _('Fayl biriktirish'),
            'is_recurring': _('Takrorlanuvchi kirim'),
            'next_occurrence': _('Keyingi takrorlanish'),
            'tags': _('Teglar'),
            'is_taxable': _('Soliqqa tortiladigan'),
            'tax_amount': _('Soliq miqdori'),
        }
        help_texts = {
            'source': _('Kirim qayerdan kelgani'),
            'attachment': _('Chek, shartnoma yoki boshqa hujjat (maksimal 5MB)'),
            'tags': _('Bir nechta teg tanlash uchun Ctrl (Windows) yoki Cmd (Mac) tugmasini bosib turib tanlang'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Faqat foydalanuvchiga tegishli kategoriyalar
            self.fields['category'].queryset = IncomeCategory.objects.filter(
                Q(user=self.user) | Q(is_default=True)
            ).order_by('name')
            
            # Faqat foydalanuvchiga tegishli manbalar
            self.fields['source_obj'].queryset = IncomeSource.objects.filter(
                user=self.user, 
                is_active=True
            ).order_by('name')
            
            # Faqat foydalanuvchiga tegishli teglar
            self.fields['tags'].queryset = IncomeTag.objects.filter(
                user=self.user
            ).order_by('name')
        
        # Boshlang'ich qiymatlar
        if not self.instance.pk:
            self.initial['date'] = timezone.now().date()
            self.initial['time'] = timezone.now().time().strftime('%H:%M')
        
        # Takrorlanish patterni uchun maxsus maydon
        self.fields['recurrence_type'] = forms.ChoiceField(
            choices=[
                ('daily', _('Har kuni')),
                ('weekly', _('Har hafta')),
                ('monthly', _('Har oy')),
                ('yearly', _('Har yil')),
            ],
            required=False,
            widget=forms.Select(attrs={'class': 'form-control'})
        )
        
        self.fields['recurrence_interval'] = forms.IntegerField(
            min_value=1,
            initial=1,
            required=False,
            widget=forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            })
        )
    
    def clean_amount(self):
        """Miqdor validatsiyasi"""
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise ValidationError(_("Miqdor 0 dan katta bo'lishi kerak"))
        return amount
    
    def clean_tax_amount(self):
        """Soliq miqdori validatsiyasi"""
        tax_amount = self.cleaned_data.get('tax_amount') or 0
        amount = self.cleaned_data.get('amount') or 0
        
        if tax_amount >= amount:
            raise ValidationError(_("Soliq miqdori kirim miqdoridan kichik bo'lishi kerak"))
        
        return tax_amount
    
    def clean_date(self):
        """Sana validatsiyasi"""
        date = self.cleaned_data.get('date')
        if date > timezone.now().date():
            raise ValidationError(_("Kelajakdagi sana kiritish mumkin emas"))
        return date
    
    def clean(self):
        """Umumiy validatsiya"""
        cleaned_data = super().clean()
        
        # Agar is_taxable False bo'lsa, tax_amount ni 0 qilish
        if not cleaned_data.get('is_taxable'):
            cleaned_data['tax_amount'] = 0
        
        # Agar source_obj tanlangan bo'lsa, source ni avtomatik to'ldirish
        source_obj = cleaned_data.get('source_obj')
        if source_obj and not cleaned_data.get('source'):
            cleaned_data['source'] = source_obj.name
        
        # Takrorlanish patternini yaratish
        if cleaned_data.get('is_recurring'):
            recurrence_type = cleaned_data.get('recurrence_type')
            recurrence_interval = cleaned_data.get('recurrence_interval') or 1
            
            if recurrence_type:
                cleaned_data['recurrence_pattern'] = {
                    'type': recurrence_type,
                    'interval': recurrence_interval,
                    'created_at': timezone.now().isoformat()
                }
        
        return cleaned_data


class IncomeTemplateForm(forms.ModelForm):
    """Kirim shabloni formasi"""
    class Meta:
        model = IncomeTemplate
        fields = ['name', 'amount', 'currency', 'category', 
                 'source', 'payment_method', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Shablon nomi (masalan: Oylik maosh)')
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'source': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Manba nomi')
            }),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Tavsif (ixtiyoriy)'),
                'style': 'resize: none;'
            }),
        }
        labels = {
            'name': _('Shablon nomi'),
            'amount': _('Miqdor'),
            'currency': _('Valyuta'),
            'category': _('Kategoriya'),
            'source': _('Manba'),
            'payment_method': _('To\'lov usuli'),
            'description': _('Tavsif')
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['category'].queryset = IncomeCategory.objects.filter(
                Q(user=self.user) | Q(is_default=True)
            ).order_by('name')


class IncomeGoalForm(forms.ModelForm):
    """Kirim maqsadi formasi"""
    class Meta:
        model = IncomeGoal
        fields = ['name', 'goal_type', 'target_amount', 'currency',
                 'start_date', 'end_date', 'categories', 'description',
                 'notification_enabled']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Maqsad nomi (masalan: Yillik daromad)')
            }),
            'goal_type': forms.Select(attrs={'class': 'form-control'}),
            'target_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'categories': forms.SelectMultiple(attrs={
                'class': 'form-control select2-multiple',
                'data-placeholder': _('Kategoriyalarni tanlang')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Maqsad haqida qo\'shimcha ma\'lumot'),
                'style': 'resize: none;'
            }),
            'notification_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'name': _('Maqsad nomi'),
            'goal_type': _('Maqsad turi'),
            'target_amount': _('Maqsad miqdori'),
            'currency': _('Valyuta'),
            'start_date': _('Boshlanish sanasi'),
            'end_date': _('Tugash sanasi'),
            'categories': _('Kategoriyalar'),
            'description': _('Tavsif'),
            'notification_enabled': _('Bildirishnomalarni yoqish'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['categories'].queryset = IncomeCategory.objects.filter(
                Q(user=self.user) | Q(is_default=True)
            ).order_by('name')
        
        # Boshlang'ich qiymatlar
        if not self.instance.pk:
            today = timezone.now().date()
            self.initial['start_date'] = today
            self.initial['end_date'] = today.replace(month=12, day=31)  # Yil oxiri
    
    def clean(self):
        """Umumiy validatsiya"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError(_("Boshlanish sanasi tugash sanasidan oldin bo'lishi kerak"))
            
            if (end_date - start_date).days > 366:
                raise ValidationError(_("Maqsad muddati 1 yildan oshmasligi kerak"))
        
        return cleaned_data


class IncomeFilterForm(forms.Form):
    """Kirimlarni filtrlash formasi"""
    DATE_RANGE_CHOICES = [
        ('today', _('Bugun')),
        ('yesterday', _('Kecha')),
        ('this_week', _('Bu hafta')),
        ('last_week', _('O\'tgan hafta')),
        ('this_month', _('Bu oy')),
        ('last_month', _('O\'tgan oy')),
        ('this_year', _('Bu yil')),
        ('last_year', _('O\'tgan yil')),
        ('custom', _('Maxsus')),
    ]
    
    date_range = forms.ChoiceField(
        choices=[('', _('Barcha vaqt'))] + DATE_RANGE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': _('Dan')
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': _('Gacha')
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=IncomeCategory.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': _('Barcha kategoriyalar')
        })
    )
    
    source = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Manba bo\'yicha qidirish...')
        })
    )
    
    min_amount = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Min miqdor'),
            'step': '0.01'
        })
    )
    
    max_amount = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Maks miqdor'),
            'step': '0.01'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', _('Barcha holatlar'))] + list(Income.StatusChoices.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    payment_method = forms.ChoiceField(
        choices=[('', _('Barcha to\'lov usullari'))] + list(Income.PaymentMethodChoices.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_recurring = forms.ChoiceField(
        choices=[('', _('Barcha')), ('true', _('Ha')), ('false', _('Yo\'q'))],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_taxable = forms.ChoiceField(
        choices=[('', _('Barcha')), ('true', _('Ha')), ('false', _('Yo\'q'))],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    tags = forms.ModelMultipleChoiceField(
        queryset=IncomeTag.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2-multiple',
            'data-placeholder': _('Teglar bo\'yicha filtrlash')
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Manba, tavsif yoki ID bo\'yicha qidirish...')
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['category'].queryset = IncomeCategory.objects.filter(
                Q(user=self.user) | Q(is_default=True)
            ).order_by('name')
            
            self.fields['tags'].queryset = IncomeTag.objects.filter(
                user=self.user
            ).order_by('name')
    
    def get_date_range(self):
        """Tanlangan vaqt oralig'ini olish"""
        date_range = self.cleaned_data.get('date_range')
        date_from = self.cleaned_data.get('date_from')
        date_to = self.cleaned_data.get('date_to')
        
        if date_range == 'custom' and date_from and date_to:
            return date_from, date_to
        
        today = timezone.now().date()
        
        if date_range == 'today':
            return today, today
        
        elif date_range == 'yesterday':
            yesterday = today - timezone.timedelta(days=1)
            return yesterday, yesterday
        
        elif date_range == 'this_week':
            start = today - timezone.timedelta(days=today.weekday())
            return start, today
        
        elif date_range == 'last_week':
            start = today - timezone.timedelta(days=today.weekday() + 7)
            end = start + timezone.timedelta(days=6)
            return start, end
        
        elif date_range == 'this_month':
            start = today.replace(day=1)
            return start, today
        
        elif date_range == 'last_month':
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timezone.timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)
            return first_day_last_month, last_day_last_month
        
        elif date_range == 'this_year':
            start = today.replace(month=1, day=1)
            return start, today
        
        elif date_range == 'last_year':
            start = today.replace(year=today.year-1, month=1, day=1)
            end = today.replace(year=today.year-1, month=12, day=31)
            return start, end
        
        return None, None


class QuickIncomeForm(forms.Form):
    """Tez kirim qo'shish formasi"""
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'placeholder': '0.00',
            'autofocus': True
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=IncomeCategory.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    source = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Manba (ixtiyoriy)')
        }),
        required=False
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': _('Tavsif (ixtiyoriy)')
        }),
        required=False,
        max_length=500
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['category'].queryset = IncomeCategory.objects.filter(
                Q(user=self.user) | Q(is_default=True)
            ).order_by('name')