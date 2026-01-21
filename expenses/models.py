
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import uuid


class ExpenseCategory(models.Model):
    """Chiqimlar kategoriyasi"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(_("Nomi"), max_length=100)
    icon = models.CharField(_("Ikon"), max_length=50, default='fas fa-shopping-cart')
    color = models.CharField(_("Rang"), max_length=20, default='#3b82f6')
    description = models.TextField(_("Tavsif"), blank=True)
    is_active = models.BooleanField(_("Faol"), default=True)
    created_at = models.DateTimeField(_("Yaratilgan sana"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Yangilangan sana"), auto_now=True)

    class Meta:
        verbose_name = _("Chiqim kategoriyasi")
        verbose_name_plural = _("Chiqim kategoriyalari")
        ordering = ['name']
        unique_together = ['user', 'name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Chiqim modeli"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='expenses', verbose_name=_("Kategoriya"))
    
    # Asosiy maydonlar
    amount = models.DecimalField(_("Summa"), max_digits=15, decimal_places=2)
    currency = models.CharField(_("Valyuta"), max_length=10, default='UZS')
    description = models.TextField(_("Izoh"), blank=True)
    date = models.DateField(_("Sana"), default=timezone.now)
    time = models.TimeField(_("Vaqt"), auto_now_add=True)
    
    # Valyuta kursi maydonlari
    exchange_rate = models.DecimalField(_("Valyuta kursi"), max_digits=10, decimal_places=4, default=1.0)
    amount_in_uzs = models.DecimalField(_("Summa (UZS)"), max_digits=15, decimal_places=2, default=0)
    
    # Qo'shimcha maydonlar
    payment_method = models.CharField(_("To'lov usuli"), max_length=50, choices=[
        ('cash', _("Naqd pul")),
        ('card', _("Bank kartasi")),
        ('transfer', _("O'tkazma")),
        ('online', _("Onlayn to'lov")),
        ('other', _("Boshqa")),
    ], default='cash')
    
    location = models.CharField(_("Manzil"), max_length=255, blank=True)
    receipt_image = models.ImageField(_("Chek rasmi"), upload_to='expense_receipts/', null=True, blank=True)
    is_recurring = models.BooleanField(_("Takrorlanuvchi"), default=False)
    recurrence_interval = models.CharField(_("Takrorlanish oralig'i"), max_length=20, blank=True, choices=[
        ('daily', _("Har kuni")),
        ('weekly', _("Har hafta")),
        ('monthly', _("Har oy")),
        ('yearly', _("Har yil")),
    ])
    
    # Status va teglar
    tags = models.ManyToManyField('ExpenseTag', blank=True, verbose_name=_("Teglar"))
    is_verified = models.BooleanField(_("Tasdiqlangan"), default=False)
    needs_review = models.BooleanField(_("Ko'rib chiqish kerak"), default=False)
    
    # Metadata
    created_at = models.DateTimeField(_("Yaratilgan sana"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Yangilangan sana"), auto_now=True)

    class Meta:
        verbose_name = _("Chiqim")
        verbose_name_plural = _("Chiqimlar")
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['date']),
            models.Index(fields=['currency']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency} - {self.date}"

    def save(self, *args, **kwargs):
        # Valyuta kursi bilan hisoblash
        from django.utils import timezone
        if not self.amount_in_uzs or self.amount_in_uzs == 0:
            self.amount_in_uzs = Decimal(str(self.amount)) * Decimal(str(self.exchange_rate))
        
        # Agar sana kiritilmagan bo'lsa, joriy sanani qo'yish
        if not self.date:
            self.date = timezone.now().date()
            
        super().save(*args, **kwargs)

    def get_formatted_amount(self):
        """Formatlangan summani qaytarish"""
        return f"{self.amount:,.2f} {self.currency}"

    def get_absolute_url(self):
        return reverse('expenses:detail', kwargs={'pk': self.pk})


class ExpenseTag(models.Model):
    """Chiqimlar uchun teglar"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expense_tags')
    name = models.CharField(_("Nomi"), max_length=50)
    color = models.CharField(_("Rang"), max_length=20, default='#6b7280')
    created_at = models.DateTimeField(_("Yaratilgan sana"), auto_now_add=True)

    class Meta:
        verbose_name = _("Chiqim tegi")
        verbose_name_plural = _("Chiqim teglari")
        ordering = ['name']
        unique_together = ['user', 'name']

    def __str__(self):
        return self.name


class Budget(models.Model):
    """Byudjet modeli"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='budgets', 
                                verbose_name=_("Kategoriya"))
    
    amount = models.DecimalField(_("Byudjet miqdori"), max_digits=15, decimal_places=2)
    currency = models.CharField(_("Valyuta"), max_length=10, default='UZS')
    period = models.CharField(_("Davr"), max_length=20, choices=[
        ('daily', _("Kunlik")),
        ('weekly', _("Haftalik")),
        ('monthly', _("Oylik")),
        ('yearly', _("Yillik")),
    ], default='monthly')
    
    start_date = models.DateField(_("Boshlanish sanasi"))
    end_date = models.DateField(_("Tugash sanasi"), null=True, blank=True)
    is_active = models.BooleanField(_("Faol"), default=True)
    
    # Ogohlantirishlar
    alert_threshold = models.IntegerField(_("Ogohlantirish chegirasi (%)"), default=80)
    send_alerts = models.BooleanField(_("Ogohlantirish yuborish"), default=True)
    
    created_at = models.DateTimeField(_("Yaratilgan sana"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Yangilangan sana"), auto_now=True)

    class Meta:
        verbose_name = _("Byudjet")
        verbose_name_plural = _("Byudjetlar")
        ordering = ['-created_at']
        unique_together = ['user', 'category', 'period']

    def __str__(self):
        return f"{self.category.name} - {self.amount} {self.currency} ({self.get_period_display()})"

    @property
    def spent_amount(self):
        """Sarflangan summa"""
        from django.db.models import Sum
        from django.utils import timezone
        
        # Davrga qarab filtr
        filters = {
            'user': self.user,
            'category': self.category,
            'date__gte': self.start_date,
        }
        
        if self.end_date:
            filters['date__lte'] = self.end_date
        
        spent = Expense.objects.filter(**filters).aggregate(
            total=Sum('amount_in_uzs')
        )['total'] or 0
        
        return spent

    @property
    def remaining_amount(self):
        """Qolgan summa"""
        return self.amount - self.spent_amount

    @property
    def usage_percentage(self):
        """Foydalanish foizi"""
        if self.amount == 0:
            return 0
        return (self.spent_amount / self.amount) * 100

    def is_over_budget(self):
        """Byudjetdan oshib ketganmi?"""
        return self.usage_percentage >= 100

    def should_alert(self):
        """Ogohlantirish kerakmi?"""
        return self.send_alerts and self.usage_percentage >= self.alert_threshold