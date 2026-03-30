
"""
活动表单 - 校园打卡平台
"""
from django import forms
from django.contrib.auth import get_user_model

from .models import Activity, ActivityApplication, ActivityComment, Category


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            'title', 'description', 'cover_image', 'category',
            'start_time', 'end_time', 'registration_deadline',
            'location', 'location_lat', 'location_lng',
            'max_participants', 'min_participants', 'points',
            'requirements', 'allow_checkin_before_start',
            'checkin_radius', 'checkin_review_mode', 'managers',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '请输入活动标题'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': '请详细描述活动内容'}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'registration_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'location': forms.TextInput(attrs={'placeholder': '请输入活动地点'}),
            'location_lat': forms.NumberInput(attrs={'placeholder': '纬度（可选）', 'step': 'any'}),
            'location_lng': forms.NumberInput(attrs={'placeholder': '经度（可选）', 'step': 'any'}),
            'max_participants': forms.NumberInput(attrs={'min': 1}),
            'min_participants': forms.NumberInput(attrs={'min': 1}),
            'points': forms.NumberInput(attrs={'min': 0}),
            'requirements': forms.Textarea(attrs={'rows': 3, 'placeholder': '参与要求（可选）'}),
            'allow_checkin_before_start': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'checkin_radius': forms.NumberInput(attrs={'min': 0, 'placeholder': '允许打卡的范围（米）'}),
            'managers': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'checkin_review_mode': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['category'].empty_label = '选择分类'

        User = get_user_model()
        manager_queryset = User.objects.filter(is_active=True).exclude(role='admin')
        if user and user.pk:
            manager_queryset = manager_queryset.exclude(pk=user.pk)
        self.fields['managers'].queryset = manager_queryset
        self.fields['managers'].required = False
        self.fields['managers'].label = '协同管理者（可选）'
        self.fields['checkin_review_mode'].label = '打卡审核模式'

        for field_name, field in self.fields.items():
            if field_name == 'allow_checkin_before_start':
                field.widget.attrs['class'] = 'form-check-input'
            elif field_name in ['category', 'managers', 'checkin_review_mode']:
                field.widget.attrs['class'] = 'form-select'
            elif field_name == 'cover_image':
                field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs.setdefault('class', '')
                field.widget.attrs['class'] += ' form-control'

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        registration_deadline = cleaned_data.get('registration_deadline')
        max_participants = cleaned_data.get('max_participants')
        min_participants = cleaned_data.get('min_participants')
        lat = cleaned_data.get('location_lat')
        lng = cleaned_data.get('location_lng')

        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('开始时间必须早于结束时间。')
        if registration_deadline and start_time and registration_deadline >= start_time:
            raise forms.ValidationError('报名截止时间必须早于活动开始时间。')
        if max_participants and min_participants and max_participants < min_participants:
            raise forms.ValidationError('最大参与人数不能小于最小参与人数。')
        if (lat and not lng) or (lng and not lat):
            raise forms.ValidationError('若使用定位校验，请同时填写经度和纬度。')
        return cleaned_data

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title and len(title) < 2:
            raise forms.ValidationError('标题至少需要2个字符。')
        return title

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description) < 10:
            raise forms.ValidationError('描述至少需要10个字符。')
        return description


class ActivityApplicationForm(forms.ModelForm):
    class Meta:
        model = ActivityApplication
        fields = [
            'title', 'description', 'apply_reason', 'cover_image', 'category',
            'start_time', 'end_time', 'registration_deadline',
            'location', 'location_lat', 'location_lng',
            'max_participants', 'min_participants', 'points',
            'requirements', 'checkin_radius', 'checkin_review_mode',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入拟申请活动标题'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': '请描述活动内容与目标'}),
            'apply_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '请说明为什么由你来组织该活动'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'registration_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入活动地点'}),
            'location_lat': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': '纬度（可选）'}),
            'location_lng': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': '经度（可选）'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'min_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '参与要求（可选）'}),
            'checkin_radius': forms.NumberInput(attrs={'class': 'form-control', 'min': 50}),
            'checkin_review_mode': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['category'].empty_label = '选择分类'

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        registration_deadline = cleaned_data.get('registration_deadline')
        max_participants = cleaned_data.get('max_participants')
        min_participants = cleaned_data.get('min_participants')
        lat = cleaned_data.get('location_lat')
        lng = cleaned_data.get('location_lng')

        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('开始时间必须早于结束时间。')
        if registration_deadline and start_time and registration_deadline >= start_time:
            raise forms.ValidationError('报名截止时间必须早于活动开始时间。')
        if max_participants and min_participants and max_participants < min_participants:
            raise forms.ValidationError('最大参与人数不能小于最小参与人数。')
        if (lat and not lng) or (lng and not lat):
            raise forms.ValidationError('若使用定位校验，请同时填写经度和纬度。')
        return cleaned_data


class ActivityCommentForm(forms.ModelForm):
    class Meta:
        model = ActivityComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': '发表评论...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].widget.attrs.update({'class': 'form-control'})
        self.fields['content'].required = True

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content and len(content.strip()) < 2:
            raise forms.ValidationError('评论内容至少需要2个字符。')
        return content
