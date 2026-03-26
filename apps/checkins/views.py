"""
打卡视图层 - 校园打卡平台
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from .models import CheckIn, CheckInPhoto
from .forms import CheckInForm
from .utils import verify_location, calculate_continuous_days, award_points

from apps.activities.models import Activity, ActivityRegistration
from apps.social.models import Message

from rest_framework import viewsets, permissions
from .serializers import CheckInSerializer


def _is_platform_admin(user):
    return getattr(user, 'role', '') == 'admin'


def _can_manage_checkin(user, activity):
    if not user or not user.is_authenticated:
        return False
    return activity.can_edit(user) or activity.can_close(user)


@login_required
def checkin_view(request):
    """打卡提交主视图"""
    registrations = ActivityRegistration.objects.filter(
        user=request.user,
        status__in=['registered', 'checked_in']
    ).select_related('activity')

    if request.method == 'POST':
        form = CheckInForm(user=request.user, data=request.POST, files=request.FILES)

        if form.is_valid():
            activity = form.cleaned_data['activity']
            registration = form.cleaned_data['registration']

            lat = form.cleaned_data.get('latitude')
            lng = form.cleaned_data.get('longitude')
            accuracy = form.cleaned_data.get('accuracy')
            photos = request.FILES.getlist('photos')

            has_real_location = (
                lat is not None and lng is not None and
                not (float(lat) == 0 and float(lng) == 0)
            )

            today = timezone.now().date()

            existing_checkin = CheckIn.objects.filter(
                user=request.user,
                activity=activity,
                check_in_date=today
            ).first()

            if existing_checkin and existing_checkin.status != 'revoked':
                messages.warning(request, '您今天已经打过卡了！')
                return redirect('checkins:history')

            is_resubmitting_revoked = existing_checkin is not None and existing_checkin.status == 'revoked'

            review_mode = getattr(activity, 'checkin_review_mode', 'auto')
            needs_manual_review = (review_mode == 'manual')
            system_review_note = ''

            # 定位校验
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
                            messages.error(request, f'位置验证失败：{msg}')
                            return render(request, 'checkins/checkin.html', {
                                'form': form,
                                'registrations': registrations
                            })
                        needs_manual_review = True
                        system_review_note = f'系统标记：位置异常，{msg}'
                else:
                    if review_mode == 'auto':
                        messages.error(request, '未获取到有效定位，无法完成打卡。')
                        return render(request, 'checkins/checkin.html', {
                            'form': form,
                            'registrations': registrations
                        })
                    needs_manual_review = True
                    system_review_note = '系统标记：未获取到有效定位'

            # 异常审核模式
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

                    if needs_manual_review:
                        checkin.status = 'pending'
                    else:
                        checkin.status = 'approved'

                    checkin.save()

                    # 撤销后重新提交，先清空旧照片，再保存新照片
                    checkin.photos.all().delete()
                else:
                    checkin = form.save(commit=False)
                    checkin.user = request.user
                    checkin.activity = activity
                    checkin.registration = registration
                    checkin.check_in_date = today
                    checkin.points_earned = 0
                    checkin.reviewed_by = None
                    checkin.review_note = system_review_note

                    if needs_manual_review:
                        checkin.status = 'pending'
                    else:
                        checkin.status = 'approved'

                    checkin.save()

                for photo in photos:
                    CheckInPhoto.objects.create(checkin=checkin, image=photo)

                registration.checked_in_at = timezone.now()

                if needs_manual_review:
                    registration.status = 'checked_in'
                    registration.save(update_fields=['status', 'checked_in_at'])
                    messages.success(
                        request,
                        '打卡重新提交成功，等待活动管理员审核！' if is_resubmitting_revoked else '打卡提交成功，等待活动管理员审核！'
                    )
                else:
                    streak = calculate_continuous_days(request.user, activity)
                    points = award_points(
                        request.user,
                        activity=activity,
                        streak_days=streak,
                        related_checkin=checkin
                    )

                    checkin.points_earned = points
                    checkin.save(update_fields=['points_earned'])

                    registration.status = 'completed'
                    registration.save(update_fields=['status', 'checked_in_at'])

                    messages.success(
                        request,
                        (
                            f'打卡重新提交成功！+{points}积分，连续打卡 {streak} 天！🎉'
                            if is_resubmitting_revoked
                            else f'打卡成功！+{points}积分，连续打卡 {streak} 天！🎉'
                        )
                    )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if needs_manual_review:
                    return JsonResponse({
                        'success': True,
                        'message': '打卡提交成功，等待审核',
                        'status': 'pending'
                    })
                return JsonResponse({
                    'success': True,
                    'message': f'打卡成功！获得 {checkin.points_earned} 积分',
                    'status': 'approved',
                    'points': checkin.points_earned
                })

            return redirect('checkins:history')

        else:
            print("===== CheckInForm.errors =====")
            print(form.errors.as_json())
            print("===== CheckInForm.non_field_errors =====")
            print(form.non_field_errors())
            messages.error(request, f'表单验证失败：{form.errors.as_text()}')

    else:
        form = CheckInForm(user=request.user)

    return render(request, 'checkins/checkin.html', {
        'form': form,
        'registrations': registrations
    })


@login_required
def checkin_history(request):
    """个人打卡历史（分页）"""
    checkins = CheckIn.objects.filter(user=request.user).select_related('activity').order_by('-created_at')
    paginator = Paginator(checkins, 10)
    page = request.GET.get('page')
    checkins_page = paginator.get_page(page)

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
    user = request.user

    if _is_platform_admin(user):
        checkins = CheckIn.objects.filter(
            status='pending'
        ).select_related('activity', 'user').order_by('-created_at')
    elif getattr(user, 'role', '') == 'teacher':
        checkins = CheckIn.objects.filter(
            status='pending'
        ).filter(
            Q(activity__creator=user) | Q(activity__managers=user)
        ).select_related('activity', 'user').distinct().order_by('-created_at')
    else:
        messages.error(request, '无权限访问待审核打卡。')
        return redirect('index')

    return render(request, 'checkins/pending.html', {'checkins': checkins})


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

    with transaction.atomic():
        checkin.status = 'approved'
        checkin.reviewed_by = request.user
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
            sender=request.user,
            message_type='activity',
            title='打卡审核已通过',
            content=f'你在活动《{checkin.activity.title}》中的打卡已审核通过，获得 {points} 积分。备注：{review_note}',
            related_activity=checkin.activity
        )

    return JsonResponse({'success': True, 'message': '审核通过'})


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

    checkin.status = 'rejected'
    checkin.reviewed_by = request.user
    checkin.review_note = review_note
    checkin.save(update_fields=['status', 'reviewed_by', 'review_note'])

    checkin.registration.status = 'registered'
    checkin.registration.save(update_fields=['status'])

    Message.objects.create(
        recipient=checkin.user,
        sender=request.user,
        message_type='activity',
        title='打卡审核未通过',
        content=f'你在活动《{checkin.activity.title}》中的打卡未通过审核。原因：{review_note}',
        related_activity=checkin.activity
    )

    return JsonResponse({'success': True, 'message': '已拒绝'})


class CheckInViewSet(viewsets.ModelViewSet):
    """DRF打卡接口（前后端分离备用）"""
    serializer_class = CheckInSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CheckIn.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        activity = serializer.validated_data['activity']
        today = timezone.localdate()

        if CheckIn.objects.filter(
            user=self.request.user,
            activity=activity,
            check_in_date=today
        ).exists():
            from rest_framework.exceptions import ValidationError
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