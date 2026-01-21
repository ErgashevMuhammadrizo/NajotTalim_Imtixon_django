from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import ExpenseCategory, Expense, ExpenseTag, Budget


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'icon', 'color', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'user__username')
    list_per_page = 20


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'amount', 'currency', 'date', 'payment_method', 'created_at')
    list_filter = ('category', 'currency', 'payment_method', 'date', 'created_at')
    search_fields = ('description', 'user__username', 'category__name')
    date_hierarchy = 'date'
    list_per_page = 30
    fieldsets = (
        (_("Asosiy ma'lumotlar"), {
            'fields': ('user', 'category', 'amount', 'currency', 'description')
        }),
        (_("Sana va vaqt"), {
            'fields': ('date', 'time')
        }),
        (_("To'lov ma'lumotlari"), {
            'fields': ('payment_method', 'location', 'receipt_image')
        }),
        (_("Valyuta kursi"), {
            'fields': ('exchange_rate', 'amount_in_uzs')
        }),
        (_("Qo'shimcha"), {
            'fields': ('is_recurring', 'recurrence_interval', 'tags', 
                      'is_verified', 'needs_review')
        }),
    )


@admin.register(ExpenseTag)
class ExpenseTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'color', 'created_at')
    search_fields = ('name', 'user__username')
    list_per_page = 20


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'amount', 'currency', 'period', 
                   'start_date', 'is_active', 'usage_percentage_display')
    list_filter = ('period', 'is_active', 'start_date')
    search_fields = ('category__name', 'user__username')
    list_per_page = 20
    
    def usage_percentage_display(self, obj):
        return f"{obj.usage_percentage:.1f}%"
    usage_percentage_display.short_description = _("Foydalanish foizi")