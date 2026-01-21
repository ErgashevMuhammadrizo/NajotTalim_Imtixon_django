from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Income, IncomeCategory, IncomeSource, IncomeTag, 
    IncomeTemplate, IncomeRecurrencePattern, IncomeGoal
)


@admin.register(IncomeCategory)
class IncomeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'icon_display', 'color_display', 
                    'income_count', 'total_amount_display', 'is_default', 'created_at']
    list_filter = ['is_default', 'user', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_default']
    readonly_fields = ['created_at', 'updated_at']
    
    def icon_display(self, obj):
        return format_html('<i class="{}"></i> {}', obj.icon, obj.icon)
    icon_display.short_description = "Ikonka"
    
    def color_display(self, obj):
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; '
            'background-color: {}; border-radius: 3px;"></span> {}',
            obj.color, obj.color
        )
    color_display.short_description = "Rang"
    
    def income_count(self, obj):
        return obj.incomes.count()
    income_count.short_description = "Kirimlar soni"
    
    def total_amount_display(self, obj):
        return f"{obj.total_amount:,.2f}"
    total_amount_display.short_description = "Jami summa"


@admin.register(IncomeSource)
class IncomeSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'total_income_display', 
                    'last_income_date', 'created_at']
    list_filter = ['is_active', 'user', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    
    def total_income_display(self, obj):
        return f"{obj.total_income:,.2f}"
    total_income_display.short_description = "Jami kirim"
    
    def last_income_date(self, obj):
        return obj.last_income_date or "-"
    last_income_date.short_description = "Oxirgi kirim"


@admin.register(IncomeTag)
class IncomeTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'color_display', 'usage_count', 'created_at']
    list_filter = ['user', 'created_at']
    search_fields = ['name']
    
    def color_display(self, obj):
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; '
            'background-color: {}; border-radius: 3px;"></span> {}',
            obj.color, obj.color
        )
    color_display.short_description = "Rang"


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = [
        'uuid_short', 'user', 'date', 'source', 'category_display', 
        'amount_display', 'status_display', 'payment_method_display',
        'is_recurring', 'created_at'
    ]
    list_filter = [
        'status', 'currency', 'category', 'is_recurring', 
        'payment_method', 'date', 'user', 'created_at'
    ]
    search_fields = ['source', 'description', 'amount']
    readonly_fields = ['uuid', 'created_at', 'updated_at', 'user_link']
    date_hierarchy = 'date'
    filter_horizontal = ['tags']
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('user_link', 'amount', 'currency', 'category', 
                      'source', 'source_obj', 'payment_method')
        }),
        ('Vaqt', {
            'fields': ('date', 'time')
        }),
        ('Qo\'shimcha', {
            'fields': ('status', 'description', 'attachment', 
                      'is_taxable', 'tax_amount')
        }),
        ('Takrorlanish', {
            'fields': ('is_recurring', 'recurrence_pattern', 'next_occurrence')
        }),
        ('Meta', {
            'fields': ('tags', 'is_transfer', 'created_at', 'updated_at')
        }),
    )
    
    def uuid_short(self, obj):
        return str(obj.uuid)[:8]
    uuid_short.short_description = "ID"
    
    def amount_display(self, obj):
        return format_html(
            '<span class="text-success fw-bold">{:,.2f} {}</span>',
            obj.amount, obj.get_currency_display()
        )
    amount_display.short_description = "Miqdor"
    
    def status_display(self, obj):
        colors = {
            'received': 'success',
            'pending': 'warning',
            'cancelled': 'danger'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_display.short_description = "Holat"
    
    def category_display(self, obj):
        return format_html(
            '<span class="badge" style="background-color: {}20; color: {};">'
            '<i class="{} me-1"></i>{}</span>',
            obj.category.color, obj.category.color,
            obj.category.icon, obj.category.name
        )
    category_display.short_description = "Kategoriya"
    
    def payment_method_display(self, obj):
        icons = {
            'cash': 'fas fa-money-bill-wave',
            'card': 'fas fa-credit-card',
            'transfer': 'fas fa-exchange-alt',
            'digital': 'fas fa-mobile-alt',
            'other': 'fas fa-question-circle'
        }
        return format_html(
            '<i class="{} me-1"></i>{}',
            icons.get(obj.payment_method, 'fas fa-question-circle'),
            obj.get_payment_method_display()
        )
    payment_method_display.short_description = "To'lov usuli"
    
    def user_link(self, obj):
        url = reverse("admin:users_customuser_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "Foydalanuvchi"


@admin.register(IncomeTemplate)
class IncomeTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'amount_display', 'category', 
                    'source', 'payment_method_display', 'is_active']
    list_filter = ['is_active', 'user', 'category', 'payment_method']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    
    def amount_display(self, obj):
        return f"{obj.amount:,.2f} {obj.get_currency_display()}"
    amount_display.short_description = "Miqdor"
    
    def payment_method_display(self, obj):
        return obj.get_payment_method_display()
    payment_method_display.short_description = "To'lov usuli"


@admin.register(IncomeRecurrencePattern)
class IncomeRecurrencePatternAdmin(admin.ModelAdmin):
    list_display = ['name', 'recurrence_type', 'interval', 
                    'end_date', 'max_occurrences']
    list_filter = ['recurrence_type']
    search_fields = ['name']


@admin.register(IncomeGoal)
class IncomeGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'goal_type', 'target_amount_display',
                    'current_amount_display', 'progress_bar', 'status_display',
                    'start_date', 'end_date']
    list_filter = ['goal_type', 'status', 'user']
    search_fields = ['name', 'description']
    filter_horizontal = ['categories']
    readonly_fields = ['created_at', 'updated_at']
    
    def target_amount_display(self, obj):
        return f"{obj.target_amount:,.2f} {obj.get_currency_display()}"
    target_amount_display.short_description = "Maqsad miqdori"
    
    def current_amount_display(self, obj):
        return f"{obj.current_amount:,.2f}"
    current_amount_display.short_description = "Joriy miqdor"
    
    def progress_bar(self, obj):
        return format_html(
            '<div style="width: 100px; height: 20px; background-color: #e9ecef; '
            'border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; height: 100%; background-color: {}; '
            'transition: width 0.3s;"></div></div>',
            obj.progress_percentage,
            '#28a745' if obj.progress_percentage >= 100 else '#007bff'
        )
    progress_bar.short_description = "Progress"
    
    def status_display(self, obj):
        colors = {
            'active': 'info',
            'completed': 'success',
            'cancelled': 'secondary'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_display.short_description = "Holat"