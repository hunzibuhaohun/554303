"""
开发环境配置
"""
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# 开发环境数据库（SQLite）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 开发环境邮件后端
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 调试工具
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']

# 关闭某些安全限制
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# 日志级别
LOGGING['loggers']['django']['level'] = 'DEBUG'
