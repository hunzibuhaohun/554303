"""
主URL配置 - 校园打卡平台
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # 管理后台
    path('admin/', admin.site.urls),

    # 首页
    path('', TemplateView.as_view(template_name='index.html'), name='index'),

    # 用户模块
    path('users/', include('apps.users.urls', namespace='users')),

    # 活动模块
    path('activities/', include('apps.activities.urls', namespace='activities')),

    # 打卡模块
    path('checkins/', include('apps.checkins.urls', namespace='checkins')),

    # 社交模块
    path('social/', include('apps.social.urls', namespace='social')),

    # 数据看板
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),

    # API模块
    path('api/', include('apps.api.urls', namespace='api')),
]

# 开发环境下提供静态文件和媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
