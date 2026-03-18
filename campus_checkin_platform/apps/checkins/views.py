"""
打卡视图层 - 校园打卡平台（最终优化版）
对应论文第4章 4.2.3 核心打卡模块实现
已集成：连续打卡计算、积分发放、防重复、位置验证、照片上传、SweetAlert
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction

from .models import CheckIn, CheckInPhoto, PointRecord
from .forms import CheckInForm
from .utils import verify_location, calculate_continuous_days, award_points
from apps.activities.models import Activity, ActivityRegistration

from rest_framework import viewsets, permissions
from .serializers import CheckInSerializer


# ====================== 主打卡页面视图 ======================
@login_required
def checkin_view(request):
    """打卡提交主视图（支持模板表单 + AJAX/SweetAlert）"""
    registrations = ActivityRegistration.objects.filter(
        user=request.user,
        status='registered'
    ).select_related('activity')

    if request.method == 'POST':
        form = CheckInForm(user=request.user, data=request.POST, files=request.FILES)

        if form.is_valid():
            activity = form.cleaned_data['activity']

            # 位置验证
            lat = form.cleaned_data.get('latitude')
            lng = form.cleaned_data.get('longitude')
            if activity.location_lat and activity.location_lng and lat and lng:
                is_valid, msg = verify_location(lat, lng, activity.location_lat, activity.location_lng, activity.checkin_radius)
                if not is_valid:
                    messages.error(request, f'位置验证失败：{msg}')
                    return render(request, 'checkins/checkin.html', {'form': form, 'registrations': registrations})

            # 防重复打卡
            today = timezone.now().date()
            if CheckIn.objects.filter(user=request.user, activity=activity, created_at__date=today).exists():
                messages.warning(request, '您今天已经打过卡了！')
                return redirect('checkins:history')

            registration = get_object_or_404(ActivityRegistration, user=request.user, activity=activity)

            with transaction.atomic():
                checkin = form.save(commit=False)
                checkin.user = request.user
                checkin.activity = activity
                checkin.registration = registration
                checkin.status = 'approved'  # 直接设为已通过
                checkin.save()

                # 保存照片
                photos = request.FILES.getlist('photos')
                for photo in photos:
                    CheckInPhoto.objects.create(checkin=checkin, image=photo)

                # 连续打卡 + 积分发放（论文核心）
                streak = calculate_continuous_days(request.user, activity)
                points = award_points(request.user, activity, streak)

                PointRecord.objects.create(
                    user=request.user,
                    points=points,
                    reason=f'打卡奖励 - {activity.title}',
                    related_checkin=checkin
                )

                # 更新报名状态为已完成
                registration.status = 'completed'
                registration.checked_in_at = timezone.now()
                registration.save()

            messages.success(request, f'打卡成功！+{points}积分，连续打卡 {streak} 天！🎉')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'打卡成功！获得 {points} 积分',
                    'streak': streak,
                    'points': points
                })

            return redirect('checkins:history')

        else:
            messages.error(request, '表单验证失败，请检查内容')

    else:
        form = CheckInForm(user=request.user)

    return render(request, 'checkins/checkin.html', {
        'form': form,
        'registrations': registrations
    })


# ====================== 打卡历史 ======================
@login_required
def checkin_history(request):
    """个人打卡历史（分页）"""
    checkins = CheckIn.objects.filter(user=request.user).select_related('activity').order_by('-created_at')
    paginator = Paginator(checkins, 10)
    page = request.GET.get('page')
    checkins_page = paginator.get_page(page)

    return render(request, 'checkins/history.html', {'checkins': checkins_page})


# ====================== 打卡详情 ======================
@login_required
def checkin_detail(request, pk):
    """单条打卡详情"""
    checkin = get_object_or_404(CheckIn, pk=pk, user=request.user)
    return render(request, 'checkins/detail.html', {'checkin': checkin})


# ====================== 位置验证API ======================
@login_required
@require_POST
def verify_location_api(request):
    """实时位置验证API"""
    try:
        activity_id = int(request.POST.get('activity_id'))
        lat = float(request.POST.get('latitude'))
        lng = float(request.POST.get('longitude'))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': '参数错误'})

    activity = get_object_or_404(Activity, id=activity_id)
    if not activity.location_lat or not activity.location_lng:
        return JsonResponse({'success': True, 'message': '活动未设置位置限制'})

    is_valid, message = verify_location(lat, lng, activity.location_lat, activity.location_lng, activity.checkin_radius)
    return JsonResponse({'success': is_valid, 'message': message})


# ====================== 管理员审核 ======================
@login_required
def pending_checkins(request):
    """待审核列表（管理员）"""
    if not request.user.is_staff:
        messages.error(request, '无权限')
        return redirect('index')
    checkins = CheckIn.objects.filter(status='pending').select_related('activity', 'user').order_by('-created_at')
    return render(request, 'checkins/pending.html', {'checkins': checkins})


@login_required
@require_POST
def approve_checkin(request, pk):
    """通过审核"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': '无权限'})
    checkin = get_object_or_404(CheckIn, pk=pk)
    checkin.status = 'approved'
    checkin.reviewer = request.user
    checkin.review_note = request.POST.get('note', '')
    checkin.reviewed_at = timezone.now()
    checkin.save()
    return JsonResponse({'success': True, 'message': '审核通过'})


@login_required
@require_POST
def reject_checkin(request, pk):
    """拒绝审核"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': '无权限'})
    checkin = get_object_or_404(CheckIn, pk=pk)
    checkin.status = 'rejected'
    checkin.reviewer = request.user
    checkin.review_note = request.POST.get('note', '')
    checkin.reviewed_at = timezone.now()
    checkin.save()
    return JsonResponse({'success': True, 'message': '已拒绝'})


# ====================== DRF API ======================
class CheckInViewSet(viewsets.ModelViewSet):
    """DRF打卡接口（前后端分离备用）"""
    serializer_class = CheckInSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CheckIn.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)