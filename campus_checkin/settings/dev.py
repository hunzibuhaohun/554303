"""
开发环境配置
"""
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# 允许通过本地地址和 ngrok 域名进行 CSRF 表单提交
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://0.0.0.0:8000',
    'https://*.ngrok-free.dev',
    'https://*.ngrok-free.app',
    'https://*.ngrok.app',
]

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

# 开发环境关闭某些安全限制
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# 日志级别
LOGGING['loggers']['django']['level'] = 'DEBUG'