"""
打卡表单 - 校园打卡平台
"""
from django import forms
from .models import CheckIn, CheckInPhoto
from apps.activities.models import Activity, ActivityRegistration


class CheckInForm(forms.ModelForm):
    """打卡表单"""

    class Meta:
        model = CheckIn
        fields = ['activity', 'latitude', 'longitude', 'accuracy', 'location_name', 'remark']
        widgets = {
            'activity': forms.Select(attrs={'class': 'form-select'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'accuracy': forms.HiddenInput(),
            'location_name': forms.HiddenInput(),
            'remark': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '添加打卡备注（可选）'
            }),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # 动态设置活动选项
        if user:
            registrations = ActivityRegistration.objects.filter(
                user=user,
                status='registered'
            ).select_related('activity')

            self.fields['activity'].choices = [
                (reg.activity.id, f"{reg.activity.title} ({reg.activity.start_time.strftime('%m月%d日')})")
                for reg in registrations
            ]

        # 设置必填字段
        self.fields['activity'].required = True
        self.fields['latitude'].required = True
        self.fields['longitude'].required = True

    def clean(self):
        cleaned_data = super().clean()
        activity_id = cleaned_data.get('activity')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')

        if not activity_id:
            raise forms.ValidationError('请选择活动')

        if not latitude or not longitude:
            raise forms.ValidationError('请允许获取位置信息')

        # 验证用户是否报名了该活动
        try:
            registration = ActivityRegistration.objects.get(
                user=self.user,
                activity_id=activity_id,
                status='registered'
            )
            cleaned_data['registration'] = registration
        except ActivityRegistration.DoesNotExist:
            raise forms.ValidationError('您没有报名此活动或已打卡')

        # 检查今天是否已打卡
        from django.utils import timezone
        if CheckIn.objects.filter(
            user=self.user,
            activity_id=activity_id,
            created_at__date=timezone.now().date()
        ).exists():
            raise forms.ValidationError('您今天已经打过卡了')

        return cleaned_data

    def save(self, commit=True):
        checkin = super().save(commit=False)
        checkin.user = self.user
        checkin.registration = self.cleaned_data['registration']

        if commit:
            checkin.save()

        return checkin