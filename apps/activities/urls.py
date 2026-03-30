
"""
活动模块URL配置
"""
from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    path('', views.activity_list, name='list'),

    path('applications/', views.activity_application_list, name='application_list'),
    path('applications/submit/', views.submit_activity_application, name='application_submit'),
    path('applications/<int:application_id>/approve/', views.approve_activity_application, name='application_approve'),
    path('applications/<int:application_id>/reject/', views.reject_activity_application, name='application_reject'),

    path('create/', views.activity_create, name='create'),
    path('my/', views.my_activities, name='my'),

    path('<int:pk>/', views.activity_detail, name='detail'),
    path('<int:pk>/edit/', views.activity_edit, name='edit'),
    path('<int:pk>/delete/', views.activity_delete, name='delete'),
    path('<int:pk>/close/', views.close_activity, name='close'),

    path('<int:pk>/join/', views.join_activity, name='join'),
    path('<int:pk>/cancel/', views.cancel_registration, name='cancel'),

    path('<int:pk>/registrations/<int:registration_id>/cancel/', views.manage_registration_cancel, name='manage_registration_cancel'),
    path('<int:pk>/registrations/<int:registration_id>/complete/', views.manage_registration_complete, name='manage_registration_complete'),

    path('<int:pk>/moments/<int:moment_id>/delete/', views.manage_moment_delete, name='manage_moment_delete'),
    path('<int:pk>/comments/<int:comment_id>/delete/', views.manage_activity_comment_delete, name='manage_activity_comment_delete'),

    path('<int:pk>/checkins/<int:checkin_id>/approve/', views.manage_checkin_approve, name='manage_checkin_approve'),
    path('<int:pk>/checkins/<int:checkin_id>/reject/', views.manage_checkin_reject, name='manage_checkin_reject'),
    path('<int:pk>/checkins/<int:checkin_id>/revoke/', views.manage_checkin_revoke, name='manage_checkin_revoke'),

    path('<int:pk>/export/participants/', views.export_activity_participants_csv, name='export_activity_participants_csv'),
    path('<int:pk>/export/checkins/', views.export_activity_checkins_csv, name='export_activity_checkins_csv'),
    path('<int:pk>/export/moments/', views.export_activity_moments_csv, name='export_activity_moments_csv'),

    path('<int:pk>/export/participants/excel/', views.export_activity_participants_excel, name='export_activity_participants_excel'),
    path('<int:pk>/export/checkins/excel/', views.export_activity_checkins_excel, name='export_activity_checkins_excel'),
    path('<int:pk>/export/moments/excel/', views.export_activity_moments_excel, name='export_activity_moments_excel'),

    path('<int:pk>/comment/', views.add_comment, name='comment'),
]
