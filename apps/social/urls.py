"""
社交模块URL配置
"""
from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    # 动态广场
    path('moments/', views.moments_list, name='moments'),
    path('moments/publish/', views.publish_moment, name='publish'),
    path('moments/<int:moment_id>/like/', views.like_moment, name='like'),
    path('moments/<int:moment_id>/comment/', views.comment_moment, name='comment'),
    path('moments/<int:moment_id>/delete/', views.delete_moment, name='delete_moment'),

    # 消息中心
    path('messages/', views.messages_list, name='messages'),
    path('messages/unread-count/', views.unread_count, name='unread_count'),
    path('messages/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('messages/<int:message_id>/read/', views.mark_message_read, name='mark_message_read'),
    path('messages/<int:message_id>/delete/', views.delete_message, name='delete_message'),
]