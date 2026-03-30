"""
用户模块URL配置
"""
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/<int:user_id>/', views.profile_detail_view, name='profile_detail'),

    path('settings/', views.settings_view, name='settings'),
    path('settings/change-password/', views.change_password_view, name='change_password'),
    path('settings/bind-phone/', views.bind_phone_view, name='bind_phone'),

    path('follow/<int:user_id>/', views.follow_user, name='follow'),
    path('unfollow/<int:user_id>/', views.unfollow_user, name='unfollow'),
    path('followers/', views.followers_list, name='followers'),
    path('following/', views.following_list, name='following'),

    path('checkin-history/', views.checkin_history_view, name='checkin_history'),
    path('checkin-streak/', views.checkin_streak_view, name='checkin_streak'),
    path('points/', views.points_view, name='points'),
    path('data-center/', views.data_center_view, name='data_center'),

    path('admin/user-list/', views.admin_user_list_view, name='admin_user_list'),
]
