"""
活动模块URL配置
"""
from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    # 活动列表和详情
    path('', views.activity_list, name='list'),
    path('<int:pk>/', views.activity_detail, name='detail'),
    
    # 活动管理
    path('create/', views.activity_create, name='create'),
    path('<int:pk>/edit/', views.activity_edit, name='edit'),
    path('<int:pk>/delete/', views.activity_delete, name='delete'),
    path('<int:pk>/close/', views.close_activity, name='close'),
    
    # 报名相关
    path('<int:pk>/join/', views.join_activity, name='join'),
    path('<int:pk>/cancel/', views.cancel_registration, name='cancel'),
    
    # 评论
    path('<int:pk>/comment/', views.add_comment, name='comment'),
    
    # 我的活动
    path('my/', views.my_activities, name='my'),
]
