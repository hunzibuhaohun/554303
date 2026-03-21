"""
打卡模块URL配置
"""
from django.urls import path
from . import views

app_name = 'checkins'

urlpatterns = [
    # 打卡页面
    path('', views.checkin_view, name='checkin'),
    path('history/', views.checkin_history, name='history'),
    path('<int:pk>/', views.checkin_detail, name='detail'),
    
    # API
    path('api/verify-location/', views.verify_location_api, name='verify_location'),



    # 审核（管理员）
    path('pending/', views.pending_checkins, name='pending'),
    path('<int:pk>/approve/', views.approve_checkin, name='approve'),
    path('<int:pk>/reject/', views.reject_checkin, name='reject'),
]
