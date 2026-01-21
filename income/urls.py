from django.urls import path
from . import views

app_name = 'income'

urlpatterns = [
    # ================ CRUD OPERATIONS ================
    path('', views.income_list, name='list'),
    path('add/', views.income_create, name='create'),
    path('<uuid:uuid>/', views.income_detail, name='detail'),
    path('<uuid:uuid>/edit/', views.income_update, name='update'),
    path('<uuid:uuid>/delete/', views.income_delete, name='delete'),
    
    # ================ CATEGORY MANAGEMENT ================
    path('categories/', views.category_list, name='categories'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # ================ SOURCE MANAGEMENT ================
    path('sources/', views.source_list, name='sources'),
    path('sources/add/', views.source_create, name='source_create'),
    
    # ================ STATISTICS & REPORTS ================
    path('stats/', views.income_stats, name='stats'),
    path('analytics/', views.income_analytics, name='analytics'),
    path('export/', views.income_export, name='export'),
    
    # ================ GOAL MANAGEMENT ================
    path('goals/', views.goal_list, name='goals'),
    path('goals/add/', views.goal_create, name='goal_create'),
    path('goals/<int:pk>/', views.goal_detail, name='goal_detail'),
    
    # ================ QUICK ACTIONS ================
    path('quick-add/', views.quick_add, name='quick_add'),
    path('bulk-delete/', views.bulk_delete, name='bulk_delete'),
    path('bulk-update-category/', views.bulk_update_category, name='bulk_update_category'),
    path('<uuid:uuid>/duplicate/', views.api_duplicate_income, name='duplicate'),
    
    # path('template/create/', views.template_create, name='template_create'),
    path('tag/create/', views.income_tag_create, name='tag_create'),
    # ================ API ENDPOINTS ================
    path('api/monthly-summary/', views.api_monthly_summary, name='monthly_summary'),
    path('api/category-stats/', views.api_category_stats, name='api_category_stats'),
    path('api/dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    path('api/autocomplete-sources/', views.get_autocomplete_sources, name='get_autocomplete_sources'),
    
]