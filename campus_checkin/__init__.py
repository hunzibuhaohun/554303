"""
校园打卡平台 - Django项目配置
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
