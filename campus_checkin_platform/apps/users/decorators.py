from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def activity_manager_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '请先登录。')
            return redirect('users:login')

        if request.user.role not in ['teacher', 'admin']:
            messages.error(request, '只有活动管理员或平台管理员可以执行此操作。')
            return redirect('index')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '请先登录。')
            return redirect('users:login')

        if request.user.role != 'admin':
            messages.error(request, '只有平台管理员可以访问该页面。')
            return redirect('index')

        return view_func(request, *args, **kwargs)
    return _wrapped_view