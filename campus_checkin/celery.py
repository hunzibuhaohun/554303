"""
Celery配置 - 用于定时任务和异步任务
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_checkin.settings.dev')

app = Celery('campus_checkin')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
