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

        # 必填字段
        self.fields['activity'].required = True

        # 位置改为可选
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
        self.fields['accuracy'].required = False
        self.fields['location_name'].required = False

    def clean(self):
        cleaned_data = super().clean()
        activity = cleaned_data.get('activity')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')

        if not activity:
            raise forms.ValidationError('请选择活动')

        # 位置可选：只有在只填了一半时才报错
        if (latitude is None and longitude is not None) or (latitude is not None and longitude is None):
            raise forms.ValidationError('位置信息不完整，请同时提供经纬度，或直接跳过定位')

        # 验证用户是否报名了该活动
        try:
            registration = ActivityRegistration.objects.get(
                user=self.user,
                activity=activity,
                status='registered'
            )
            cleaned_data['registration'] = registration
        except ActivityRegistration.DoesNotExist:
            raise forms.ValidationError('您没有报名此活动或已打卡')

        # 检查今天是否已打卡
        from django.utils import timezone
        if CheckIn.objects.filter(
            user=self.user,
            activity=activity,
            created_at__date=timezone.now().date()
        ).exists():
            raise forms.ValidationError('您今天已经打过卡了')

        return cleaned_data

    def save(self, commit=True):
        checkin = super().save(commit=False)
        checkin.user = self.user
        checkin.registration = self.cleaned_data['registration']

        # 如果前端跳过定位，给默认值
        if checkin.latitude in [None, '']:
            checkin.latitude = 0
        if checkin.longitude in [None, '']:
            checkin.longitude = 0
        if not checkin.accuracy:
            checkin.accuracy = 9999
        if not checkin.location_name:
            checkin.location_name = '未获取位置'

        if commit:
            checkin.save()

        return checkin