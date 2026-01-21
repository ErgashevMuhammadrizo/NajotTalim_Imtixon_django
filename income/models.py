import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone


class CurrencyChoices(models.TextChoices):
    """Valyuta turlari"""
    UZS = 'UZS', _('So\'m')
    USD = 'USD', _('Dollar')
    EUR = 'EUR', _('Euro')
    RUB = 'RUB', _('Rubl')
    CNY = 'CNY', _('Yuan')


class IncomeCategory(models.Model):
    """Kirim manbalari kategoriyalari"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='income_categories'
    )
    name = models.CharField(max_length=100, verbose_name=_("Nomi"))
    icon = models.CharField(
        max_length=50, 
        default='fas fa-money-bill-wave',
        verbose_name=_("Ikonka")
    )
    color = models.CharField(
        max_length=20, 
        default='#3b82f6',
        verbose_name=_("Rang")
    )
    is_default = models.BooleanField(default=False, verbose_name=_("Standart kategoriya"))
    description = models.TextField(blank=True, verbose_name=_("Tavsif"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Kirim kategoriyasi")
        verbose_name_plural = _("Kirim kategoriyalari")
        ordering = ['name']
        unique_together = ['user', 'name']
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    def save(self, *args, **kwargs):
        # Nomni tozalash
        self.name = self.name.strip()
        super().save(*args, **kwargs)
    
    @property
    def income_count(self):
        """Bu kategoriyadagi kirimlar soni"""
        return self.incomes.count()
    
    @property
    def total_amount(self):
        """Bu kategoriyadagi jami kirim miqdori"""
        return self.incomes.aggregate(total=models.Sum('amount'))['total'] or 0
    
    def get_icon_display(self):
        """Icon ko'rinishi"""
        return f'<i class="{self.icon}"></i>'


class IncomeSource(models.Model):
    """Kirim manbalari (source)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='income_sources'
    )
    name = models.CharField(max_length=200, verbose_name=_("Nomi"))
    description = models.TextField(blank=True, verbose_name=_("Tavsif"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Kirim manbasi")
        verbose_name_plural = _("Kirim manbalari")
        ordering = ['name']
        unique_together = ['user', 'name']
    
    def __str__(self):
        return self.name
    
    @property
    def total_income(self):
        """Bu manbadan kelgan jami kirim"""
        return Income.objects.filter(
            source_obj=self,
            user=self.user
        ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def last_income_date(self):
        """Oxirgi kirim sanasi"""
        last = Income.objects.filter(
            source_obj=self,
            user=self.user
        ).order_by('-date').first()
        return last.date if last else None


class IncomeTag(models.Model):
    """Kirimlar uchun teglar"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='income_tags'
    )
    name = models.CharField(max_length=50, verbose_name=_("Nomi"))
    color = models.CharField(
        max_length=20, 
        default='#3b82f6',
        verbose_name=_("Rang")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Kirim tegi")
        verbose_name_plural = _("Kirim teglari")
        ordering = ['name']
        unique_together = ['user', 'name']
        indexes = [
            models.Index(fields=['user', 'name']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def usage_count(self):
        """Teg ishlatilgan soni"""
        return self.incomes.count()


class Income(models.Model):
    """Kirim operatsiyalari"""
    
    class StatusChoices(models.TextChoices):
        RECEIVED = 'received', _('Qabul qilindi')
        PENDING = 'pending', _('Kutilmoqda')
        CANCELLED = 'cancelled', _('Bekor qilindi')
    
    class PaymentMethodChoices(models.TextChoices):
        CASH = 'cash', _('Naqd pul')
        CARD = 'card', _('Bank kartasi')
        TRANSFER = 'transfer', _('Bank o\'tkazmasi')
        DIGITAL = 'digital', _('Digital to\'lov')
        OTHER = 'other', _('Boshqa')
    
    # Identifikatsiya
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='incomes'
    )
    
    # Asosiy ma'lumotlar
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name=_("Miqdor")
    )
    currency = models.CharField(
        max_length=3, 
        choices=CurrencyChoices.choices,
        default=CurrencyChoices.UZS,
        verbose_name=_("Valyuta")
    )
    category = models.ForeignKey(
        IncomeCategory,
        on_delete=models.PROTECT,
        related_name='incomes',
        verbose_name=_("Kategoriya")
    )
    
    # Manba va to'lov usuli
    source = models.CharField(max_length=200, verbose_name=_("Manba"))
    source_obj = models.ForeignKey(
        IncomeSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incomes',
        verbose_name=_("Manba obyekti")
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethodChoices.choices,
        default=PaymentMethodChoices.CASH,
        verbose_name=_("To'lov usuli")
    )
    
    # Vaqt
    date = models.DateField(default=timezone.now, verbose_name=_("Sana"))
    time = models.TimeField(blank=True, null=True, verbose_name=_("Vaqt"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Holat va izoh
    status = models.CharField(
        max_length=20, 
        choices=StatusChoices.choices,
        default=StatusChoices.RECEIVED,
        verbose_name=_("Holat")
    )
    description = models.TextField(blank=True, verbose_name=_("Tavsif"))
    attachment = models.FileField(
        upload_to='income_attachments/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_("Fayl"),
        help_text=_("Chek, shartnoma yoki boshqa hujjat")
    )
    
    # Takrorlanish
    is_recurring = models.BooleanField(default=False, verbose_name=_("Takrorlanuvchi"))
    recurrence_pattern = models.JSONField(
        blank=True, 
        null=True, 
        verbose_name=_("Takrorlanish qoidasi"),
        help_text=_('JSON formatida: {"type": "monthly", "interval": 1, "end_date": "2024-12-31"}')
    )
    next_occurrence = models.DateField(blank=True, null=True, verbose_name=_("Keyingi takrorlanish"))
    
    # Meta
    tags = models.ManyToManyField(IncomeTag, blank=True, related_name='incomes')
    is_transfer = models.BooleanField(default=False, verbose_name=_("Hisoblar orasidagi o'tkazma"))
    is_taxable = models.BooleanField(default=False, verbose_name=_("Soliqqa tortiladigan"))
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Soliq miqdori")
    )
    
    class Meta:
        verbose_name = _("Kirim")
        verbose_name_plural = _("Kirimlar")
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'is_recurring']),
            models.Index(fields=['user', 'payment_method']),
            models.Index(fields=['user', 'source']),
            models.Index(fields=['created_at']),
        ]
        permissions = [
            ('export_income', 'Kirimlarni export qilish'),
            ('view_statistics', 'Statistikalarni ko\'rish'),
        ]
    
    def __str__(self):
        return f"{self.amount} {self.get_currency_display()} - {self.source} ({self.date})"
    
    def save(self, *args, **kwargs):
        # Agar source_obj berilgan bo'lsa, source ni avtomatik to'ldirish
        if self.source_obj and not self.source:
            self.source = self.source_obj.name
        
        # Agar takrorlanuvchi bo'lsa va next_occurrence berilmagan bo'lsa
        if self.is_recurring and not self.next_occurrence:
            self.next_occurrence = self.date
        
        super().save(*args, **kwargs)
    
    @property
    def net_amount(self):
        """Soliq chegirilgandan keyingi miqdor"""
        return self.amount - self.tax_amount
    
    @property
    def formatted_amount(self):
        """Formatlangan miqdor"""
        return f"{self.amount:,.2f}"
    
    @property
    def formatted_net_amount(self):
        """Formatlangan net miqdor"""
        return f"{self.net_amount:,.2f}"
    
    @property
    def full_datetime(self):
        """To'liq sana va vaqt"""
        if self.time:
            return f"{self.date} {self.time.strftime('%H:%M')}"
        return str(self.date)
    
    @property
    def month_year(self):
        """Oy va yil"""
        return self.date.strftime('%B %Y')
    
    @property
    def has_attachment(self):
        """Fayl biriktirilganmi?"""
        return bool(self.attachment)
    
    @property
    def attachment_name(self):
        """Fayl nomi"""
        if self.attachment:
            return self.attachment.name.split('/')[-1]
        return None
    
    @classmethod
    def get_monthly_summary(cls, user, year=None, month=None):
        """Oylik xulosani olish"""
        queryset = cls.objects.filter(user=user)
        
        if year:
            queryset = queryset.filter(date__year=year)
        if month:
            queryset = queryset.filter(date__month=month)
        
        return queryset.aggregate(
            total_amount=models.Sum('amount'),
            total_count=models.Count('id'),
            avg_amount=models.Avg('amount'),
            total_tax=models.Sum('tax_amount')
        )
    
    @classmethod
    def get_yearly_summary(cls, user, year=None):
        """Yillik xulosani olish"""
        if not year:
            year = timezone.now().year
        
        monthly_data = []
        for month in range(1, 13):
            month_data = cls.get_monthly_summary(user, year, month)
            monthly_data.append({
                'month': month,
                'total_amount': month_data['total_amount'] or 0,
                'total_count': month_data['total_count'] or 0,
            })
        
        return monthly_data


class IncomeTemplate(models.Model):
    """Tez kirim qo'shish uchun shablonlar"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='income_templates'
    )
    name = models.CharField(max_length=100, verbose_name=_("Nomi"))
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name=_("Miqdor")
    )
    currency = models.CharField(
        max_length=3,
        choices=CurrencyChoices.choices,
        default=CurrencyChoices.UZS,
        verbose_name=_("Valyuta")
    )
    category = models.ForeignKey(
        IncomeCategory,
        on_delete=models.CASCADE,
        related_name='templates',
        verbose_name=_("Kategoriya")
    )
    source = models.CharField(max_length=200, verbose_name=_("Manba"))
    payment_method = models.CharField(
        max_length=20,
        choices=Income.PaymentMethodChoices.choices,
        default=Income.PaymentMethodChoices.CASH,
        verbose_name=_("To'lov usuli")
    )
    description = models.TextField(blank=True, verbose_name=_("Tavsif"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Kirim shabloni")
        verbose_name_plural = _("Kirim shablonlari")
        ordering = ['name']
        unique_together = ['user', 'name']
    
    def __str__(self):
        return self.name
    
    def create_income(self, date=None, **kwargs):
        """Shablon asosida kirim yaratish"""
        income_data = {
            'user': self.user,
            'amount': self.amount,
            'currency': self.currency,
            'category': self.category,
            'source': self.source,
            'payment_method': self.payment_method,
            'description': self.description,
            'date': date or timezone.now().date(),
        }
        
        # Qo'shimcha parametrlar
        income_data.update(kwargs)
        
        return Income.objects.create(**income_data)
    
    @property
    def usage_count(self):
        """Shablon ishlatilgan soni"""
        # Bu ma'lumotni yana bir model yoki signal orqali kuzatish mumkin
        # Hozircha 0 qaytaramiz
        return 0


class IncomeRecurrencePattern(models.Model):
    """Takrorlanish patternlari"""
    
    class RecurrenceType(models.TextChoices):
        DAILY = 'daily', _('Har kuni')
        WEEKLY = 'weekly', _('Har hafta')
        BIWEEKLY = 'biweekly', _('Har ikki haftada')
        MONTHLY = 'monthly', _('Har oy')
        QUARTERLY = 'quarterly', _('Har chorakda')
        YEARLY = 'yearly', _('Har yil')
        CUSTOM = 'custom', _('Maxsus')
    
    name = models.CharField(max_length=100, verbose_name=_("Nomi"))
    recurrence_type = models.CharField(
        max_length=20,
        choices=RecurrenceType.choices,
        verbose_name=_("Takrorlanish turi")
    )
    interval = models.PositiveIntegerField(default=1, verbose_name=_("Interval"))
    week_days = models.JSONField(
        blank=True, 
        null=True,
        verbose_name=_("Hafta kunlari"),
        help_text=_('JSON formatida: [1,3,5] (1-Dushanba, 7-Yakshanba)')
    )
    month_days = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Oy kunlari"),
        help_text=_('JSON formatida: [1,15,31]')
    )
    end_date = models.DateField(blank=True, null=True, verbose_name=_("Tugash sanasi"))
    max_occurrences = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_("Maksimal takrorlanishlar")
    )
    
    class Meta:
        verbose_name = _("Takrorlanish patterni")
        verbose_name_plural = _("Takrorlanish patternlari")
    
    def __str__(self):
        return self.name
    
    def get_next_date(self, from_date):
        """Berilgan sanadan keyingi takrorlanish sanasini hisoblash"""
        from datetime import datetime, timedelta
        
        if self.recurrence_type == self.RecurrenceType.DAILY:
            return from_date + timedelta(days=self.interval)
        
        elif self.recurrence_type == self.RecurrenceType.WEEKLY:
            return from_date + timedelta(weeks=self.interval)
        
        elif self.recurrence_type == self.RecurrenceType.BIWEEKLY:
            return from_date + timedelta(weeks=2 * self.interval)
        
        elif self.recurrence_type == self.RecurrenceType.MONTHLY:
            # Oyning oxirgi kuni uchun maxsus hisoblash
            try:
                year = from_date.year + (from_date.month + self.interval - 1) // 12
                month = (from_date.month + self.interval - 1) % 12 + 1
                day = min(from_date.day, [31,29,31,30,31,30,31,31,30,31,30,31][month-1])
                return from_date.replace(year=year, month=month, day=day)
            except ValueError:
                return None
        
        elif self.recurrence_type == self.RecurrenceType.QUARTERLY:
            months_to_add = self.interval * 3
            year = from_date.year + (from_date.month + months_to_add - 1) // 12
            month = (from_date.month + months_to_add - 1) % 12 + 1
            day = min(from_date.day, [31,29,31,30,31,30,31,31,30,31,30,31][month-1])
            return from_date.replace(year=year, month=month, day=day)
        
        elif self.recurrence_type == self.RecurrenceType.YEARLY:
            try:
                return from_date.replace(year=from_date.year + self.interval)
            except ValueError:  # 29-fevral holati
                return from_date.replace(year=from_date.year + self.interval, day=28)
        
        return None


class IncomeGoal(models.Model):
    """Kirim maqsadlari"""
    
    class GoalType(models.TextChoices):
        MONTHLY = 'monthly', _('Oylik')
        YEARLY = 'yearly', _('Yillik')
        CUSTOM = 'custom', _('Maxsus')
    
    class GoalStatus(models.TextChoices):
        ACTIVE = 'active', _('Faol')
        COMPLETED = 'completed', _('Yakunlangan')
        CANCELLED = 'cancelled', _('Bekor qilingan')
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='income_goals'
    )
    name = models.CharField(max_length=200, verbose_name=_("Nomi"))
    goal_type = models.CharField(
        max_length=20,
        choices=GoalType.choices,
        default=GoalType.MONTHLY,
        verbose_name=_("Maqsad turi")
    )
    target_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name=_("Maqsad miqdori")
    )
    currency = models.CharField(
        max_length=3,
        choices=CurrencyChoices.choices,
        default=CurrencyChoices.UZS,
        verbose_name=_("Valyuta")
    )
    start_date = models.DateField(verbose_name=_("Boshlanish sanasi"))
    end_date = models.DateField(verbose_name=_("Tugash sanasi"))
    categories = models.ManyToManyField(
        IncomeCategory,
        blank=True,
        related_name='goals',
        verbose_name=_("Kategoriyalar")
    )
    description = models.TextField(blank=True, verbose_name=_("Tavsif"))
    status = models.CharField(
        max_length=20,
        choices=GoalStatus.choices,
        default=GoalStatus.ACTIVE,
        verbose_name=_("Holat")
    )
    notification_enabled = models.BooleanField(default=True, verbose_name=_("Bildirishnomalar"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Kirim maqsadi")
        verbose_name_plural = _("Kirim maqsadlari")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'start_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.target_amount} {self.get_currency_display()}"
    
    @property
    def current_amount(self):
        """Joriy vaqtgacha yig'ilgan miqdor"""
        from django.db.models import Sum
        
        total = Income.objects.filter(
            user=self.user,
            date__range=[self.start_date, self.end_date],
            status='received'
        )
        
        if self.categories.exists():
            total = total.filter(category__in=self.categories.all())
        
        result = total.aggregate(total=Sum('amount'))['total']
        return result or 0
    
    @property
    def progress_percentage(self):
        """Maqsad bajarilish foizi"""
        if self.target_amount == 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)
    
    @property
    def remaining_amount(self):
        """Qolgan miqdor"""
        return max(0, self.target_amount - self.current_amount)
    
    @property
    def remaining_days(self):
        """Qolgan kunlar"""
        from datetime import date
        
        today = date.today()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days
    
    @property
    def is_on_track(self):
        """Maqsad yo'lidami?"""
        if self.remaining_days == 0:
            return self.current_amount >= self.target_amount
        
        daily_target = self.target_amount / ((self.end_date - self.start_date).days + 1)
        expected_amount = daily_target * ((date.today() - self.start_date).days + 1)
        
        return self.current_amount >= expected_amount
    
    def update_status(self):
        """Maqsad holatini yangilash"""
        if self.progress_percentage >= 100:
            self.status = self.GoalStatus.COMPLETED
        elif self.end_date < timezone.now().date():
            self.status = self.GoalStatus.CANCELLED
        
        self.save()