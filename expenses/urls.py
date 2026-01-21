from django.urls import path
from django.utils.translation import gettext_lazy as _
from . import views

app_name = 'expenses'

urlpatterns = [
    # Chiqimlar
    path('', views.ExpenseListView.as_view(), name='list'),
    path('create/', views.ExpenseCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.ExpenseDetailView.as_view(), name='detail'),
    path('<uuid:pk>/update/', views.ExpenseUpdateView.as_view(), name='update'),
    path('<uuid:pk>/delete/', views.ExpenseDeleteView.as_view(), name='delete'),
    path('quick-create/', views.quick_create_expense, name='quick_create'),
    
    # Kategoriyalar
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<uuid:pk>/update/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<uuid:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    
    # Byudjetlar
    path('budgets/', views.BudgetListView.as_view(), name='budget_list'),
    path('budgets/create/', views.BudgetCreateView.as_view(), name='budget_create'),
    path('budgets/<uuid:pk>/update/', views.BudgetUpdateView.as_view(), name='budget_update'),
    path('budgets/<uuid:pk>/delete/', views.BudgetDeleteView.as_view(), name='budget_delete'),
    
    # API endpoints
    # Dashboard endpointlari
    path('api/dashboard-summary/', views.dashboard_summary, name='dashboard_summary'),
    path('api/dashboard/summary/', views.dashboard_summary, name='api_dashboard_summary'),
    path('api/dashboard/chart-data/', views.dashboard_chart_data, name='api_dashboard_chart_data'),
    path('api/dashboard/category-stats/', views.dashboard_category_stats, name='api_dashboard_category_stats'),
    
    # Export
    path('export/csv/', views.export_expenses_csv, name='export_csv'),
    path('export/excel/', views.export_expenses_excel, name='export_excel'),
]