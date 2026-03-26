"""
数据看板URL配置
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('statistics/', views.statistics_view, name='statistics'),
    path('personal/', views.personal_stats, name='personal'),
    path('api/chart-data/', views.get_chart_data, name='chart_data'),
]