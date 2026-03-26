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

    # 管理员操作：参与者
    path(
        '<int:pk>/registrations/<int:registration_id>/cancel/',
        views.manage_registration_cancel,
        name='manage_registration_cancel'
    ),
    path(
        '<int:pk>/registrations/<int:registration_id>/complete/',
        views.manage_registration_complete,
        name='manage_registration_complete'
    ),

    # 管理员操作：打卡审核
    path(
        '<int:pk>/checkins/<int:checkin_id>/approve/',
        views.manage_checkin_approve,
        name='manage_checkin_approve'
    ),
    path(
        '<int:pk>/checkins/<int:checkin_id>/reject/',
        views.manage_checkin_reject,
        name='manage_checkin_reject'
    ),
    path(
        '<int:pk>/checkins/<int:checkin_id>/revoke/',
        views.manage_checkin_revoke,
        name='manage_checkin_revoke'
    ),

    # 导出
    path(
        '<int:pk>/export/participants/',
        views.export_activity_participants_csv,
        name='export_activity_participants_csv'
    ),
    path(
        '<int:pk>/export/checkins/',
        views.export_activity_checkins_csv,
        name='export_activity_checkins_csv'
    ),
    path(
        '<int:pk>/export/moments/',
        views.export_activity_moments_csv,
        name='export_activity_moments_csv'
    ),

    # 评论
    path('<int:pk>/comment/', views.add_comment, name='comment'),

    # 我的活动
    path('my/', views.my_activities, name='my'),
]