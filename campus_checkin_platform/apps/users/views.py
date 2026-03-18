"""
用户视图 - 校园打卡平台
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime, timedelta
import calendar

from .models import User, FollowRelation
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, UserSettingsForm


try:
    from apps.checkins.models import CheckIn
except ImportError:
    # 如果 checkins 应用不存在，使用 activities
    from apps.activities.models import CheckIn


def register_view(request):
    """用户注册视图"""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '注册成功！欢迎加入校园打卡平台！')
            return redirect('index')
        else:
            messages.error(request, '注册失败，请检查填写信息。')
    else:
        form = UserRegistrationForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    """用户登录视图"""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            # 尝试用学号登录
            if user is None:
                try:
                    user_by_student_id = User.objects.get(student_id=username)
                    user = authenticate(request, username=user_by_student_id.username, password=password)
                except User.DoesNotExist:
                    pass

            if user is not None:
                login(request, user)
                messages.success(request, f'欢迎回来，{user.get_full_name()}！')
                next_url = request.GET.get('next', 'index')
                return redirect(next_url)
            else:
                messages.error(request, '用户名或密码错误。')
        else:
            messages.error(request, '登录失败，请检查填写信息。')
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    """用户退出视图"""
    logout(request)
    messages.success(request, '已成功退出登录。')
    return redirect('index')


@login_required
def profile_view(request):
    """个人中心视图"""
    user = request.user

    # 获取统计数据
    context = {
        'profile_user': user,
        'streak_days': user.streak_days,
        'followers_count': user.followers.count(),
        'following_count': user.following.count(),
        'achievements': user.achievements.all()[:6],
        'recent_checkins': user.checkins.select_related('activity').order_by('-created_at')[:5],
        'created_activities': user.created_activities.order_by('-created_at')[:5],
    }
    return render(request, 'users/profile.html', context)


@login_required
def profile_detail_view(request, user_id):
    """他人资料视图"""
    profile_user = get_object_or_404(User, id=user_id)

    # 检查是否已关注
    is_following = FollowRelation.objects.filter(
        follower=request.user,
        following=profile_user
    ).exists()

    context = {
        'profile_user': profile_user,
        'is_following': is_following,
        'streak_days': profile_user.streak_days,
        'followers_count': profile_user.followers.count(),
        'following_count': profile_user.following.count(),
        'achievements': profile_user.achievements.all()[:6],
        'recent_checkins': profile_user.checkins.select_related('activity').order_by('-created_at')[:5],
    }
    return render(request, 'users/profile_detail.html', context)


@login_required
def profile_edit_view(request):
    """编辑个人资料视图"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '个人资料更新成功！')
            return redirect('users:profile')
        else:
            messages.error(request, '更新失败，请检查填写信息。')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'users/profile_edit.html', {'form': form})


@login_required
def settings_view(request):
    """用户设置视图"""
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '设置保存成功！')
            return redirect('users:settings')
        else:
            messages.error(request, '保存失败，请检查填写信息。')
    else:
        form = UserSettingsForm(instance=request.user)

    return render(request, 'users/settings.html', {'form': form})


@login_required
@require_POST
def follow_user(request, user_id):
    """关注用户"""
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        return JsonResponse({'success': False, 'message': '不能关注自己'})

    follow_relation, created = FollowRelation.objects.get_or_create(
        follower=request.user,
        following=target_user
    )

    if created:
        return JsonResponse({
            'success': True,
            'message': '关注成功',
            'followers_count': target_user.followers.count()
        })
    else:
        return JsonResponse({'success': False, 'message': '已经关注了'})


@login_required
@require_POST
def unfollow_user(request, user_id):
    """取消关注用户"""
    target_user = get_object_or_404(User, id=user_id)

    deleted, _ = FollowRelation.objects.filter(
        follower=request.user,
        following=target_user
    ).delete()

    if deleted:
        return JsonResponse({
            'success': True,
            'message': '取消关注成功',
            'followers_count': target_user.followers.count()
        })
    else:
        return JsonResponse({'success': False, 'message': '未关注该用户'})


@login_required
def followers_list(request):
    """粉丝列表"""
    followers = request.user.followers.all()
    return render(request, 'users/followers.html', {'users': followers, 'title': '我的粉丝'})


@login_required
def following_list(request):
    """关注列表"""
    following = request.user.following.all()
    return render(request, 'users/following.html', {'users': following, 'title': '我的关注'})


# ==================== 新增的统计详情视图 ====================

@login_required
def checkin_history_view(request):
    """打卡记录详情视图"""
    user = request.user
    filter_type = request.GET.get('filter', 'all')

    # 获取打卡记录
    from apps.checkins.models import CheckIn
    checkins = CheckIn.objects.filter(user=user).select_related('activity').order_by('-created_at')

    # 筛选
    today = timezone.now()
    if filter_type == 'month':
        checkins = checkins.filter(created_at__month=today.month, created_at__year=today.year)
    elif filter_type == 'week':
        week_ago = today - timedelta(days=7)
        checkins = checkins.filter(created_at__gte=week_ago)

    # 统计
    total_checkins = user.checkins.count()
    this_month = user.checkins.filter(created_at__month=today.month, created_at__year=today.year).count()
    total_points = sum(c.points for c in user.checkins.all()) if hasattr(user.checkins.first(), 'points') else total_checkins * 10

    context = {
        'checkins': checkins,
        'total_checkins': total_checkins,
        'this_month': this_month,
        'total_points': total_points,
        'current_filter': filter_type,
    }
    return render(request, 'users/checkin_history.html', context)


@login_required
def points_view(request):
    """积分详情视图"""
    user = request.user

    # 模拟积分记录（实际应从 PointRecord 模型查询）
    from apps.checkins.models import CheckIn
    point_history = []
    checkins = CheckIn.objects.filter(user=user).order_by('-created_at')[:10]
    for checkin in checkins:
        point_history.append({
            'description': f'打卡：{checkin.activity.title}',
            'amount': getattr(checkin, 'points', 10),
            'created_at': checkin.created_at
        })

    # 添加连续打卡奖励记录（模拟）
    if user.streak_days >= 3:
        point_history.append({
            'description': f'连续{user.streak_days}天打卡奖励',
            'amount': 20,
            'created_at': timezone.now() - timedelta(days=1)
        })

    # 等级进度
    current_points = getattr(user, 'points', 0) or 0
    next_level_threshold = ((current_points // 100) + 1) * 100
    next_level_points = max(0, next_level_threshold - current_points)
    progress_percent = min(100, (current_points % 100))
    current_level = (current_points // 100) + 1
    next_level = current_level + 1

    context = {
        'user': user,
        'point_history': point_history,
        'next_level_points': next_level_points,
        'progress_percent': progress_percent,
        'current_level': f'Lv.{current_level}',
        'next_level': f'Lv.{next_level}',
    }
    return render(request, 'users/points.html', context)


@login_required
def checkin_streak_view(request):
    """连续打卡详情视图"""
    user = request.user

    # 获取连续打卡数据
    streak_days = getattr(user, 'streak_days', 0)
    longest_streak = getattr(user, 'longest_streak', streak_days)

    # 生成本月日历
    today = timezone.now()
    current_year = today.year
    current_month = today.month

    _, last_day = calendar.monthrange(current_year, current_month)

    # 获取本月打卡记录
    from apps.checkins.models import CheckIn
    checkin_dates = set()
    checkins = CheckIn.objects.filter(
        user=user,
        created_at__year=current_year,
        created_at__month=current_month
    )
    for c in checkins:
        checkin_dates.add(c.created_at.day)

    # 生成日历数据
    calendar_days = []
    first_weekday, _ = calendar.monthrange(current_year, current_month)

    # 上月填充
    prev_month_last_day = (today.replace(day=1) - timedelta(days=1)).day
    for i in range(first_weekday):
        calendar_days.append({
            'date': prev_month_last_day - first_weekday + i + 1,
            'checked': False,
            'is_today': False,
            'other_month': True
        })

    # 本月日期
    for day in range(1, last_day + 1):
        calendar_days.append({
            'date': day,
            'checked': day in checkin_dates,
            'is_today': day == today.day,
            'other_month': False
        })

    # 下月填充（补齐网格）
    remaining = (7 - (len(calendar_days) % 7)) % 7
    for day in range(1, remaining + 1):
        calendar_days.append({
            'date': day,
            'checked': False,
            'is_today': False,
            'other_month': True
        })

    this_month_count = len(checkin_dates)
    total_checkins = CheckIn.objects.filter(user=user).count()

    context = {
        'streak_days': streak_days,
        'longest_streak': longest_streak,
        'this_month_count': this_month_count,
        'total_checkins': total_checkins,
        'current_year': current_year,
        'current_month': current_month,
        'calendar_days': calendar_days,
    }
    return render(request, 'users/checkin_streak.html', context)


# ==================== DRF API 视图 ====================

from rest_framework import viewsets, permissions
from .serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """用户API视图集"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户"""
        return User.objects.filter(id=self.request.user.id)

    def get_object(self):
        """获取当前用户"""
        return self.request.user

from .forms import (
    CustomPasswordChangeForm,
    PhoneBindForm,
    PasswordResetRequestForm,
    AvatarUploadForm
)

@login_required
def change_password_view(request):
    """修改密码"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '密码修改成功，请重新登录')
            return redirect('users:login')
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, 'users/change_password.html', {'form': form})

@login_required
def bind_phone_view(request):
    """绑定手机号"""
    if request.method == 'POST':
        form = PhoneBindForm(request.POST)
        if form.is_valid():
            request.user.phone = form.cleaned_data['phone']
            request.user.save()
            messages.success(request, '手机号绑定成功')
            return redirect('users:settings')
    else:
        form = PhoneBindForm()
    return render(request, 'users/bind_phone.html', {'form': form})


@login_required
def data_center_view(request):
    """数据中心视图"""
    user = request.user

    # 获取用户的统计数据
    from apps.activities.models import Activity
    from apps.checkins.models import CheckIn

    # 打卡统计
    
    checkin_stats = {
        'total': user.total_checkins,
        'this_month': CheckIn.objects.filter(
            user=user,
            created_at__month=timezone.now().month
        ).count(),
        'this_week': CheckIn.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count(),
    }

    # 活动统计
    activity_stats = {
        'joined': user.activities_joined,
        'created': user.activities_created,
        'ongoing': Activity.objects.filter(
            participants=user,
            status='ongoing'
        ).count(),
    }

    # 积分趋势（最近7天）
    point_trend = []
    for i in range(6, -1, -1):
        date = timezone.now() - timedelta(days=i)
        points_earned = CheckIn.objects.filter(
            user=user,
            created_at__date=date.date()
        ).count() * 10  # 假设每次打卡10分
        point_trend.append({
            'date': date.strftime('%m-%d'),
            'points': points_earned
        })

    context = {
        'user': user,
        'checkin_stats': checkin_stats,
        'activity_stats': activity_stats,
        'point_trend': point_trend,
        'level_progress': user.get_level_progress() if hasattr(user, 'get_level_progress') else 0,
    }
    return render(request, 'users/data_center.html', context)