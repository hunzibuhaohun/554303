"""
打卡视图层 - 校园打卡平台
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from rest_framework import viewsets, permissions
from rest_framework.exceptions import ValidationError

from .forms import CheckInForm
from .models import CheckIn, CheckInPhoto
from .serializers import CheckInSerializer
from .utils import verify_location, calculate_continuous_days, award_points

from apps.activities.models import Activity, ActivityRegistration
from apps.social.models import Message


# =========================
# 通用辅助函数
# =========================
def _is_platform_admin(user):
    return getattr(user, 'role', '') == 'admin'


def _can_manage_checkin(user, activity):
    if not user or not user.is_authenticated:
        return False
    return activity.can_edit(user) or activity.can_close(user)


def _get_checkin_page_context(user, form=None):
    registrations = ActivityRegistration.objects.filter(
        user=user,
        status__in=['registered', 'checked_in']
    ).select_related('activity')

    if form is None:
        form = CheckInForm(user=user)

    return {
        'form': form,
        'registrations': registrations
    }


def _has_real_location(lat, lng):
    return (
        lat is not None and
        lng is not None and
        not (float(lat) == 0 and float(lng) == 0)
    )


def _evaluate_checkin_review(activity, lat, lng, accuracy, photos):
    """
    返回：
    {
        'review_mode': str,
        'needs_manual_review': bool,
        'system_review_note': str,
        'blocking_error': str,
    }
    """
    review_mode = getattr(activity, 'checkin_review_mode', 'auto')
    needs_manual_review = (review_mode == 'manual')
    system_review_note = ''
    blocking_error = ''

    has_real_location = _has_real_location(lat, lng)

    # 位置校验
    if activity.location_lat is not None and activity.location_lng is not None:
        if has_real_location:
            is_valid, msg = verify_location(
                lat,
                lng,
                activity.location_lat,
                activity.location_lng,
                activity.checkin_radius
            )
            if not is_valid:
                if review_mode == 'auto':
                    blocking_error = f'位置验证失败：{msg}'
                else:
                    needs_manual_review = True
                    system_review_note = f'系统标记：位置异常，{msg}'
        else:
            if review_mode == 'auto':
                blocking_error = '未获取到有效定位，无法完成打卡。'
            else:
                needs_manual_review = True
                system_review_note = '系统标记：未获取到有效定位'

    # 风险审核模式
    if review_mode == 'risk':
        extra_notes = []

        if not photos:
            needs_manual_review = True
            extra_notes.append('未上传打卡照片')

        try:
            if accuracy and float(accuracy) > max(activity.checkin_radius * 1.5, 300):
                needs_manual_review = True
                extra_notes.append(f'定位精度较差（{accuracy}米）')
        except (TypeError, ValueError):
            pass

        if extra_notes:
            extra_text = '；'.join(extra_notes)
            if system_review_note:
                system_review_note = f'{system_review_note}；{extra_text}'
            else:
                system_review_note = f'系统标记：{extra_text}'

    return {
        'review_mode': review_mode,
        'needs_manual_review': needs_manual_review,
        'system_review_note': system_review_note,
        'blocking_error': blocking_error,
    }


def _save_checkin_submission(
    *,
    user,
    form,
    activity,
    registration,
    existing_checkin,
    today,
    photos,
    needs_manual_review,
    system_review_note
):
    """
    保存打卡提交。
    返回：
    {
        'checkin': checkin,
        'points': int,
        'streak': int,
        'is_resubmitting_revoked': bool,
        'needs_manual_review': bool,
    }
    """
    is_resubmitting_revoked = existing_checkin is not None and existing_checkin.status == 'revoked'

    with transaction.atomic():
        if is_resubmitting_revoked:
            checkin = existing_checkin
            checkin.remark = form.cleaned_data.get('remark', '')
            checkin.latitude = form.cleaned_data.get('latitude') or 0
            checkin.longitude = form.cleaned_data.get('longitude') or 0
            checkin.accuracy = form.cleaned_data.get('accuracy') or 9999
            checkin.location_name = form.cleaned_data.get('location_name') or '未获取位置'
            checkin.reviewed_by = None
            checkin.review_note = system_review_note
            checkin.points_earned = 0
            checkin.check_in_date = today
            checkin.status = 'pending' if needs_manual_review else 'approved'
            checkin.save()

            # 撤销后重新提交：清理旧照片
            checkin.photos.all().delete()
        else:
            checkin = form.save(commit=False)
            checkin.user = user
            checkin.activity = activity
            checkin.registration = registration
            checkin.check_in_date = today
            checkin.points_earned = 0
            checkin.reviewed_by = None
            checkin.review_note = system_review_note
            checkin.status = 'pending' if needs_manual_review else 'approved'
            checkin.save()

        for photo in photos:
            CheckInPhoto.objects.create(checkin=checkin, image=photo)

        registration.checked_in_at = timezone.now()

        if needs_manual_review:
            registration.status = 'checked_in'
            registration.save(update_fields=['status', 'checked_in_at'])
            points = 0
            streak = 0
        else:
            streak = calculate_continuous_days(user, activity)
            points = award_points(
                user,
                activity=activity,
                streak_days=streak,
                related_checkin=checkin
            )

            checkin.points_earned = points
            checkin.save(update_fields=['points_earned'])

            registration.status = 'completed'
            registration.save(update_fields=['status', 'checked_in_at'])

    return {
        'checkin': checkin,
        'points': points,
        'streak': streak,
        'is_resubmitting_revoked': is_resubmitting_revoked,
        'needs_manual_review': needs_manual_review,
    }


def _build_checkin_success_message(result):
    is_resubmitting_revoked = result['is_resubmitting_revoked']
    needs_manual_review = result['needs_manual_review']
    points = result['points']
    streak = result['streak']

    if needs_manual_review:
        return (
            '打卡重新提交成功，等待活动管理员审核！'
            if is_resubmitting_revoked
            else '打卡提交成功，等待活动管理员审核！'
        )

    return (
        f'打卡重新提交成功！+{points}积分，连续打卡 {streak} 天！🎉'
        if is_resubmitting_revoked
        else f'打卡成功！+{points}积分，连续打卡 {streak} 天！🎉'
    )


def _get_pending_checkins_for_user(user):
    if _is_platform_admin(user):
        return CheckIn.objects.filter(
            status='pending'
        ).select_related('activity', 'user').order_by('-created_at')

    if getattr(user, 'role', '') == 'teacher':
        return CheckIn.objects.filter(
            status='pending'
        ).filter(
            Q(activity__creator=user) | Q(activity__managers=user)
        ).select_related('activity', 'user').distinct().order_by('-created_at')

    return None


def _apply_checkin_review(*, checkin, reviewer, approved, review_note):
    """
    处理待审核打卡。
    返回：
    {
        'points': int,
        'message': str,
    }
    """
    with transaction.atomic():
        if approved:
            checkin.status = 'approved'
            checkin.reviewed_by = reviewer
            checkin.review_note = review_note
            checkin.save(update_fields=['status', 'reviewed_by', 'review_note'])

            streak = calculate_continuous_days(checkin.user, checkin.activity)
            points = award_points(
                checkin.user,
                activity=checkin.activity,
                streak_days=streak,
                related_checkin=checkin
            )

            checkin.points_earned = points
            checkin.save(update_fields=['points_earned'])

            checkin.registration.status = 'completed'
            checkin.registration.save(update_fields=['status'])

            Message.objects.create(
                recipient=checkin.user,
                sender=reviewer,
                message_type='activity',
                title='打卡审核已通过',
                content=f'你在活动《{checkin.activity.title}》中的打卡已审核通过，获得 {points} 积分。备注：{review_note}',
                related_activity=checkin.activity
            )

            return {
                'points': points,
                'message': '审核通过'
            }

        checkin.status = 'rejected'
        checkin.reviewed_by = reviewer
        checkin.review_note = review_note
        checkin.save(update_fields=['status', 'reviewed_by', 'review_note'])

        checkin.registration.status = 'registered'
        checkin.registration.save(update_fields=['status'])

        Message.objects.create(
            recipient=checkin.user,
            sender=reviewer,
            message_type='activity',
            title='打卡审核未通过',
            content=f'你在活动《{checkin.activity.title}》中的打卡未通过审核。原因：{review_note}',
            related_activity=checkin.activity
        )

        return {
            'points': 0,
            'message': '已拒绝'
        }


# =========================
# 页面视图
# =========================
@login_required
def checkin_view(request):
    """打卡提交主视图"""
    context = _get_checkin_page_context(request.user)

    if request.method == 'POST':
        form = CheckInForm(user=request.user, data=request.POST, files=request.FILES)
        context['form'] = form

        if form.is_valid():
            activity = form.cleaned_data['activity']
            registration = form.cleaned_data['registration']

            lat = form.cleaned_data.get('latitude')
            lng = form.cleaned_data.get('longitude')
            accuracy = form.cleaned_data.get('accuracy')
            photos = request.FILES.getlist('photos')
            today = timezone.now().date()

            existing_checkin = CheckIn.objects.filter(
                user=request.user,
                activity=activity,
                check_in_date=today
            ).first()

            if existing_checkin and existing_checkin.status != 'revoked':
                messages.warning(request, '您今天已经打过卡了！')
                return redirect('checkins:history')

            review_eval = _evaluate_checkin_review(
                activity=activity,
                lat=lat,
                lng=lng,
                accuracy=accuracy,
                photos=photos
            )

            if review_eval['blocking_error']:
                messages.error(request, review_eval['blocking_error'])
                return render(request, 'checkins/checkin.html', context)

            result = _save_checkin_submission(
                user=request.user,
                form=form,
                activity=activity,
                registration=registration,
                existing_checkin=existing_checkin,
                today=today,
                photos=photos,
                needs_manual_review=review_eval['needs_manual_review'],
                system_review_note=review_eval['system_review_note'],
            )

            success_message = _build_checkin_success_message(result)
            messages.success(request, success_message)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if result['needs_manual_review']:
                    return JsonResponse({
                        'success': True,
                        'message': '打卡提交成功，等待审核',
                        'status': 'pending'
                    })
                return JsonResponse({
                    'success': True,
                    'message': f'打卡成功！获得 {result["checkin"].points_earned} 积分',
                    'status': 'approved',
                    'points': result['checkin'].points_earned
                })

            return redirect('checkins:history')

        print("===== CheckInForm.errors =====")
        print(form.errors.as_json())
        print("===== CheckInForm.non_field_errors =====")
        print(form.non_field_errors())
        messages.error(request, f'表单验证失败：{form.errors.as_text()}')

    return render(request, 'checkins/checkin.html', context)


@login_required
def checkin_history(request):
    """个人打卡历史（分页）"""
    checkins = CheckIn.objects.filter(user=request.user).select_related('activity').order_by('-created_at')
    checkins_page = Paginator(checkins, 10).get_page(request.GET.get('page'))
    return render(request, 'checkins/history.html', {'checkins': checkins_page})


@login_required
def checkin_detail(request, pk):
    """单条打卡详情"""
    checkin = get_object_or_404(CheckIn, pk=pk, user=request.user)
    return render(request, 'checkins/detail.html', {'checkin': checkin})


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

    if activity.location_lat is None or activity.location_lng is None:
        return JsonResponse({'success': True, 'message': '活动未设置位置限制'})

    is_valid, message = verify_location(
        lat,
        lng,
        activity.location_lat,
        activity.location_lng,
        activity.checkin_radius
    )
    return JsonResponse({'success': is_valid, 'message': message})


@login_required
def pending_checkins(request):
    """待审核列表"""
    checkins = _get_pending_checkins_for_user(request.user)
    if checkins is None:
        messages.error(request, '无权限访问待审核打卡。')
        return redirect('index')

    return render(request, 'checkins/pending.html', {'checkins': checkins})


# =========================
# 审核动作
# =========================
@login_required
@require_POST
def approve_checkin(request, pk):
    """通过审核"""
    checkin = get_object_or_404(
        CheckIn.objects.select_related('activity', 'registration', 'user'),
        pk=pk
    )

    if not _can_manage_checkin(request.user, checkin.activity):
        return JsonResponse({'success': False, 'message': '无权限'}, status=403)

    if checkin.status != 'pending':
        return JsonResponse({'success': False, 'message': '该打卡不是待审核状态'}, status=400)

    review_note = request.POST.get('note', '').strip() or '管理员审核通过'
    result = _apply_checkin_review(
        checkin=checkin,
        reviewer=request.user,
        approved=True,
        review_note=review_note
    )

    return JsonResponse({
        'success': True,
        'message': result['message'],
        'points': result['points']
    })


@login_required
@require_POST
def reject_checkin(request, pk):
    """拒绝审核"""
    checkin = get_object_or_404(
        CheckIn.objects.select_related('activity', 'registration', 'user'),
        pk=pk
    )

    if not _can_manage_checkin(request.user, checkin.activity):
        return JsonResponse({'success': False, 'message': '无权限'}, status=403)

    if checkin.status != 'pending':
        return JsonResponse({'success': False, 'message': '该打卡不是待审核状态'}, status=400)

    review_note = request.POST.get('note', '').strip() or '管理员审核拒绝'
    result = _apply_checkin_review(
        checkin=checkin,
        reviewer=request.user,
        approved=False,
        review_note=review_note
    )

    return JsonResponse({
        'success': True,
        'message': result['message']
    })


# =========================
# DRF ViewSet
# =========================
class CheckInViewSet(viewsets.ModelViewSet):
    """DRF打卡接口（前后端分离备用）"""
    serializer_class = CheckInSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CheckIn.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        activity = serializer.validated_data['activity']
        today = timezone.localdate()

        existing_non_revoked = CheckIn.objects.filter(
            user=self.request.user,
            activity=activity,
            check_in_date=today
        ).exclude(status='revoked').exists()

        if existing_non_revoked:
            raise ValidationError({'detail': '今天已完成该活动打卡，请勿重复提交'})

        registration, _ = ActivityRegistration.objects.get_or_create(
            user=self.request.user,
            activity=activity,
            defaults={'status': 'registered'}
        )

        serializer.save(
            user=self.request.user,
            registration=registration,
            check_in_date=today,
            status='approved'
        )