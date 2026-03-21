"""
用户模块URL配置
"""
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # 认证相关
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # 个人中心
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/<int:user_id>/', views.profile_detail_view, name='profile_detail'),
    
    # 设置
    path('settings/', views.settings_view, name='settings'),
    
    # 社交关系
    path('follow/<int:user_id>/', views.follow_user, name='follow'),
    path('unfollow/<int:user_id>/', views.unfollow_user, name='unfollow'),
    path('followers/', views.followers_list, name='followers'),
    path('following/', views.following_list, name='following'),

    # 统计详情页面 - 新增
    path('checkin-history/', views.checkin_history_view, name='checkin_history'),
    path('checkin-streak/', views.checkin_streak_view, name='checkin_streak'),
    path('points/', views.points_view, name='points'),

    # 其他

    path('data-center/', views.data_center_view, name='data_center'),
]
