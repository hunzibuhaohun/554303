"""
打卡表单 - 校园打卡平台
"""
from django import forms
from django.utils import timezone

from .models import CheckIn
from apps.activities.models import ActivityRegistration


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

        if user:
            registrations = ActivityRegistration.objects.filter(
                user=user,
                status__in=['registered', 'checked_in']
            ).select_related('activity')

            self.fields['activity'].choices = [('', '请选择要打卡的活动')] + [
                (reg.activity.id, f"{reg.activity.title} ({reg.activity.start_time.strftime('%m月%d日')})")
                for reg in registrations
            ]

        self.fields['activity'].required = True
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
        self.fields['accuracy'].required = False
        self.fields['location_name'].required = False
        self.fields['remark'].required = False

    def clean(self):
        cleaned_data = super().clean()
        activity = cleaned_data.get('activity')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')

        if not activity:
            raise forms.ValidationError('请选择活动')

        # 经纬度只允许“都为空”或“都存在”
        if (latitude in [None, ''] and longitude not in [None, '']) or \
           (longitude in [None, ''] and latitude not in [None, '']):
            raise forms.ValidationError('位置信息不完整，请同时提供经纬度，或直接跳过定位')

        # 验证用户是否报名了该活动
        try:
            registration = ActivityRegistration.objects.get(
                user=self.user,
                activity=activity,
                status__in=['registered', 'checked_in']
            )
            cleaned_data['registration'] = registration
        except ActivityRegistration.DoesNotExist:
            raise forms.ValidationError('您没有报名此活动或当前状态不可打卡')

        today = timezone.localdate()

        # 只拦截“待审核 / 已通过”
        # 已拒绝 rejected、已撤销 revoked 允许当天重新提交
        existing_checkin = CheckIn.objects.filter(
            user=self.user,
            activity=activity,
            check_in_date=today,
            status__in=['pending', 'approved']
        ).first()

        if existing_checkin:
            if existing_checkin.status == 'pending':
                raise forms.ValidationError('您今天对该活动的打卡已提交，正在审核中，请勿重复提交')
            if existing_checkin.status == 'approved':
                raise forms.ValidationError('您今天对该活动的打卡已审核通过，不能重复打卡')

        return cleaned_data

    def save(self, commit=True):
        checkin = super().save(commit=False)
        checkin.user = self.user
        checkin.registration = self.cleaned_data['registration']

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