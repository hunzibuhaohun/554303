
"""
用户视图 - 校园打卡平台
"""
import calendar
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import permissions, viewsets

from apps.activities.models import Activity
from apps.checkins.models import CheckIn, PointRecord
from .forms import (
    AvatarUploadForm,
    CustomPasswordChangeForm,
    PhoneBindForm,
    UserLoginForm,
    UserProfileForm,
    UserRegistrationForm,
    UserSettingsForm,
)
from .decorators import admin_required
from .models import FollowRelation, User
from .serializers import UserSerializer


def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '注册成功！欢迎加入校园打卡平台。')
            return redirect('index')
        messages.error(request, '注册失败，请检查填写信息。')
    else:
        form = UserRegistrationForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is None:
                try:
                    user_by_student_id = User.objects.get(student_id=username)
                    user = authenticate(
                        request,
                        username=user_by_student_id.username,
                        password=password,
                    )
                except User.DoesNotExist:
                    pass

            if user is not None:
                login(request, user)
                messages.success(request, f'欢迎回来，{user.get_full_name()}！')
                return redirect(request.GET.get('next', 'index'))

            messages.error(request, '用户名或密码错误。')
        else:
            messages.error(request, '登录失败，请检查填写信息。')
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form})


@login_required
@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, '已成功退出登录。')
    return redirect('index')


@login_required
def profile_view(request):
    user = request.user
    context = {
        'profile_user': user,
        'streak_days': user.streak_days,
        'followers_count': user.followers_count,
        'following_count': user.following_count,
        'achievements': user.achievements.all()[:6],
        'recent_checkins': user.checkins.select_related('activity').order_by('-created_at')[:5],
        'created_activities': user.created_activities.order_by('-created_at')[:5],
    }
    return render(request, 'users/profile.html', context)


@login_required
def profile_detail_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    is_following = FollowRelation.objects.filter(
        follower=request.user,
        following=profile_user,
    ).exists()

    context = {
        'profile_user': profile_user,
        'is_following': is_following,
        'streak_days': profile_user.streak_days,
        'followers_count': profile_user.followers_count,
        'following_count': profile_user.following_count,
        'achievements': profile_user.achievements.all()[:6],
        'recent_checkins': profile_user.checkins.select_related('activity').order_by('-created_at')[:5],
    }
    return render(request, 'users/profile_detail.html', context)


@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '个人资料更新成功！')
            return redirect('users:profile')
        messages.error(request, '更新失败，请检查填写信息。')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'users/profile_edit.html', {'form': form})


@login_required
def settings_view(request):
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '设置保存成功！')
            return redirect('users:settings')
        messages.error(request, '保存失败，请检查填写信息。')
    else:
        form = UserSettingsForm(instance=request.user)

    return render(request, 'users/settings.html', {'form': form})


@login_required
@require_POST
def follow_user(request, user_id):
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        return JsonResponse({'success': False, 'message': '不能关注自己'})

    _, created = FollowRelation.objects.get_or_create(
        follower=request.user,
        following=target_user,
    )
    if created:
        return JsonResponse({
            'success': True,
            'message': '关注成功',
            'followers_count': target_user.followers_count,
        })
    return JsonResponse({'success': False, 'message': '已经关注了'})


@login_required
@require_POST
def unfollow_user(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    deleted, _ = FollowRelation.objects.filter(
        follower=request.user,
        following=target_user,
    ).delete()

    if deleted:
        return JsonResponse({
            'success': True,
            'message': '取消关注成功',
            'followers_count': target_user.followers_count,
        })
    return JsonResponse({'success': False, 'message': '未关注该用户'})


@login_required
def followers_list(request):
    followers = request.user.followers.all()
    return render(request, 'users/followers.html', {'users': followers, 'title': '我的粉丝'})


@login_required
def following_list(request):
    following = request.user.following.all()
    return render(request, 'users/following.html', {'users': following, 'title': '我的关注'})


@login_required
def checkin_history_view(request):
    user = request.user
    filter_type = request.GET.get('filter', 'all')
    checkins = CheckIn.objects.filter(user=user).select_related('activity').order_by('-created_at')

    today = timezone.now()
    if filter_type == 'month':
        checkins = checkins.filter(created_at__month=today.month, created_at__year=today.year)
    elif filter_type == 'week':
        week_ago = today - timedelta(days=7)
        checkins = checkins.filter(created_at__gte=week_ago)

    context = {
        'checkins': checkins,
        'total_checkins': user.checkins.count(),
        'this_month': user.checkins.filter(
            created_at__month=today.month,
            created_at__year=today.year,
        ).count(),
        'total_points': sum(c.points_earned for c in user.checkins.all()),
        'current_filter': filter_type,
    }
    return render(request, 'users/checkin_history.html', context)


@login_required
def points_view(request):
    point_history = PointRecord.objects.filter(user=request.user).order_by('-created_at')[:20]

    context = {
        'user': request.user,
        'point_history': point_history,
        'next_level_points': max(0, request.user.get_next_level_points() - request.user.points),
        'progress_percent': request.user.get_level_progress(),
        'current_level': f'Lv.{request.user.level}',
        'next_level': f'Lv.{min(request.user.level + 1, 10)}',
    }
    return render(request, 'users/points.html', context)


@login_required
def checkin_streak_view(request):
    user = request.user
    today = timezone.now()
    current_year = today.year
    current_month = today.month
    _, last_day = calendar.monthrange(current_year, current_month)

    checkin_dates = set(
        CheckIn.objects.filter(
            user=user,
            created_at__year=current_year,
            created_at__month=current_month,
            status='approved',
        ).values_list('created_at__day', flat=True)
    )

    calendar_days = []
    first_weekday, _ = calendar.monthrange(current_year, current_month)
    prev_month_last_day = (today.replace(day=1) - timedelta(days=1)).day
    for i in range(first_weekday):
        calendar_days.append({
            'date': prev_month_last_day - first_weekday + i + 1,
            'checked': False,
            'is_today': False,
            'other_month': True,
        })

    for day in range(1, last_day + 1):
        calendar_days.append({
            'date': day,
            'checked': day in checkin_dates,
            'is_today': day == today.day,
            'other_month': False,
        })

    remaining = (7 - (len(calendar_days) % 7)) % 7
    for day in range(1, remaining + 1):
        calendar_days.append({
            'date': day,
            'checked': False,
            'is_today': False,
            'other_month': True,
        })

    context = {
        'streak_days': user.streak_days,
        'longest_streak': user.longest_streak,
        'this_month_count': len(checkin_dates),
        'total_checkins': CheckIn.objects.filter(user=user, status='approved').count(),
        'current_year': current_year,
        'current_month': current_month,
        'calendar_days': calendar_days,
    }
    return render(request, 'users/checkin_streak.html', context)


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            logout(request)
            messages.success(request, '密码修改成功，请重新登录。')
            return redirect('users:login')
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, 'users/change_password.html', {'form': form})


@login_required
def bind_phone_view(request):
    if request.method == 'POST':
        form = PhoneBindForm(request.POST)
        if form.is_valid():
            request.user.phone = form.cleaned_data['phone']
            request.user.save(update_fields=['phone'])
            messages.success(request, '手机号绑定成功。')
            return redirect('users:settings')
    else:
        form = PhoneBindForm()
    return render(request, 'users/bind_phone.html', {'form': form})


@login_required
def data_center_view(request):
    user = request.user
    now = timezone.now()

    joined_qs = Activity.objects.filter(
        participants__user=user,
        participants__status__in=['registered', 'checked_in', 'completed'],
    ).distinct()
    created_qs = Activity.objects.filter(creator=user)

    point_trend = []
    for i in range(6, -1, -1):
        date = now - timedelta(days=i)
        points_earned = PointRecord.objects.filter(
            user=user,
            created_at__date=date.date(),
        ).aggregate(total=Count('id'))['total'] or 0
        point_trend.append({
            'date': date.strftime('%m-%d'),
            'points': points_earned,
        })

    context = {
        'user': user,
        'checkin_stats': {
            'total': CheckIn.objects.filter(user=user, status='approved').count(),
            'this_month': CheckIn.objects.filter(
                user=user,
                status='approved',
                created_at__month=now.month,
                created_at__year=now.year,
            ).count(),
            'this_week': CheckIn.objects.filter(
                user=user,
                status='approved',
                created_at__gte=now - timedelta(days=7),
            ).count(),
        },
        'activity_stats': {
            'joined': joined_qs.count(),
            'created': created_qs.count(),
            'ongoing': joined_qs.filter(status='ongoing').count(),
        },
        'point_trend': point_trend,
        'level_progress': user.get_level_progress(),
    }
    return render(request, 'users/data_center.html', context)


@admin_required
def admin_user_list_view(request):
    keyword = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    department = request.GET.get('department', '').strip()
    is_active = request.GET.get('is_active', '').strip()

    users = User.objects.all().order_by('-created_at')

    if keyword:
        users = users.filter(
            Q(username__icontains=keyword)
            | Q(real_name__icontains=keyword)
            | Q(student_id__icontains=keyword)
            | Q(phone__icontains=keyword)
            | Q(email__icontains=keyword)
        )

    if role:
        users = users.filter(role=role)

    if department:
        users = users.filter(department__icontains=department)

    if is_active in ['1', '0']:
        users = users.filter(is_active=(is_active == '1'))

    context = {
        'users': users,
        'filters': {
            'q': keyword,
            'role': role,
            'department': department,
            'is_active': is_active,
        },
        'role_choices': User.ROLE_CHOICES,
        'total_count': users.count(),
    }
    return render(request, 'users/admin_user_list.html', context)




class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    def get_object(self):
        return self.request.user
