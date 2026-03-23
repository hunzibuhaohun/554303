"""社交表单 - 校园打卡平台"""
from django import forms
from .models import Moment, MomentComment


# ═══════════════════════════════════════════════════
# 直接在本文件定义自定义 Widget（不依赖外部文件）
# ═══════════════════════════════════════════════════
class MultipleFileInput(forms.ClearableFileInput):
    """支持多文件上传的自定义 Widget"""
    allow_multiple_selected = True


class MomentForm(forms.ModelForm):
    """发布动态表单"""
    images = forms.FileField(
        label='图片',
        required=False,
        widget=MultipleFileInput(attrs={      # ← 使用上面定义的 MultipleFileInput
            'class': 'form-control',
            'accept': 'image/*',
            'multiple': True
        })
    )

    class Meta:
        model = Moment
        fields = ['content', 'activity']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '分享你的校园生活...'
            }),
            'activity': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['activity'].required = False
        if user:
            from apps.activities.models import ActivityRegistration
            participated_activities = ActivityRegistration.objects.filter(
                user=user
            ).select_related('activity')
            self.fields['activity'].choices = [('', '不关联活动')] + [
                (reg.activity.id, reg.activity.title)
                for reg in participated_activities
            ]


class MomentCommentForm(forms.ModelForm):
    """动态评论表单"""
    class Meta:
        model = MomentComment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '发表评论...'
            }),
        }