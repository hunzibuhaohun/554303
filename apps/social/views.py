
"""
社交视图 - 校园打卡平台
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import permissions, viewsets

from .forms import MomentCommentForm, MomentForm
from .models import Message, Moment, MomentComment, MomentImage
from .serializers import MomentSerializer


def moments_list(request):
    moments = (
        Moment.objects.select_related('user', 'activity')
        .prefetch_related('images', 'likes', 'comments')
        .order_by('-created_at')
    )
    moments = Paginator(moments, 10).get_page(request.GET.get('page'))
    form = MomentForm(user=request.user) if request.user.is_authenticated else None
    return render(request, 'social/moments.html', {'moments': moments, 'form': form})


@login_required
def publish_moment(request):
    if request.method == 'POST':
        form = MomentForm(user=request.user, data=request.POST, files=request.FILES)
        if form.is_valid():
            moment = form.save(commit=False)
            moment.user = request.user
            moment.save()

            for idx, image in enumerate(request.FILES.getlist('images')):
                MomentImage.objects.create(moment=moment, image=image, order=idx)

            messages.success(request, '动态发布成功！')
            return redirect('social:moments')
        messages.error(request, f'发布失败：{form.errors.as_text()}')
    return redirect('social:moments')


@login_required
@require_POST
def like_moment(request, moment_id):
    moment = get_object_or_404(Moment, id=moment_id)

    if request.user in moment.likes.all():
        moment.likes.remove(request.user)
        liked = False
    else:
        moment.likes.add(request.user)
        liked = True
        if moment.user != request.user:
            Message.objects.create(
                recipient=moment.user,
                sender=request.user,
                message_type='like',
                title='有人赞了你的动态',
                content=f'{request.user.username} 赞了你的动态',
                related_moment=moment,
            )

    return JsonResponse({'success': True, 'liked': liked, 'likes_count': moment.likes.count()})


@login_required
@require_POST
def comment_moment(request, moment_id):
    moment = get_object_or_404(Moment, id=moment_id)
    form = MomentCommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.moment = moment
        comment.user = request.user
        comment.save()

        if moment.user != request.user:
            Message.objects.create(
                recipient=moment.user,
                sender=request.user,
                message_type='comment',
                title='有人评论了你的动态',
                content=f'{request.user.username} 评论：{comment.content}',
                related_moment=moment,
            )

        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'user': comment.user.username,
                'content': comment.content,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
            },
        })

    return JsonResponse({'success': False, 'message': '评论失败'})


@login_required
def delete_moment(request, moment_id):
    moment = get_object_or_404(Moment, id=moment_id)
    is_platform_admin = getattr(request.user, 'role', '') == 'admin'
    if moment.user != request.user and not is_platform_admin:
        messages.error(request, '您没有权限删除此动态。')
        return redirect('social:moments')

    moment.delete()
    messages.success(request, '动态已删除。')
    return redirect('social:moments')


@login_required
def messages_list(request):
    filter_type = request.GET.get('type', 'all')
    keyword = request.GET.get('q', '').strip()

    messages_qs = (
        Message.objects.filter(recipient=request.user)
        .select_related('sender', 'related_activity', 'related_moment')
        .order_by('-created_at')
    )

    if filter_type == 'unread':
        messages_qs = messages_qs.filter(is_read=False)
    elif filter_type == 'activity':
        messages_qs = messages_qs.filter(message_type='activity')
    elif filter_type == 'social':
        messages_qs = messages_qs.filter(message_type__in=['like', 'comment', 'follow'])
    elif filter_type == 'system':
        messages_qs = messages_qs.filter(message_type='system')

    if keyword:
        messages_qs = messages_qs.filter(title__icontains=keyword) | messages_qs.filter(content__icontains=keyword)

    messages_page = Paginator(messages_qs, 12).get_page(request.GET.get('page'))

    return render(request, 'social/messages.html', {
        'messages_page': messages_page,
        'filter_type': filter_type,
        'keyword': keyword,
        'unread_total': Message.objects.filter(recipient=request.user, is_read=False).count(),
        'all_total': Message.objects.filter(recipient=request.user).count(),
        'activity_total': Message.objects.filter(recipient=request.user, message_type='activity').count(),
        'social_total': Message.objects.filter(recipient=request.user, message_type__in=['like', 'comment', 'follow']).count(),
        'system_total': Message.objects.filter(recipient=request.user, message_type='system').count(),
    })


@login_required
def unread_count(request):
    return JsonResponse({'count': Message.objects.filter(recipient=request.user, is_read=False).count()})


@login_required
@require_POST
def mark_all_read(request):
    Message.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_message_read(request, message_id):
    msg = get_object_or_404(Message, id=message_id, recipient=request.user)
    if not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=['is_read'])
    return JsonResponse({'success': True})


@login_required
@require_POST
def delete_message(request, message_id):
    msg = get_object_or_404(Message, id=message_id, recipient=request.user)
    msg.delete()
    return JsonResponse({'success': True})


class MomentViewSet(viewsets.ModelViewSet):
    queryset = Moment.objects.all()
    serializer_class = MomentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Moment.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
