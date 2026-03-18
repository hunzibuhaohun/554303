"""
ASGI配置 - 用于WebSocket和异步支持
"""
import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_checkin.settings.prod')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    # WebSocket配置将在后续添加
    # "websocket": AuthMiddlewareStack(
    #     URLRouter(
    #         # 路由配置
    #     )
    # ),
})
