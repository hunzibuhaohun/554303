from django import forms
from .models import Moment, MomentComment
from apps.activities.models import Activity, ActivityRegistration


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if not data:
            return []

        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]

        return [single_file_clean(data, initial)]


class MomentForm(forms.ModelForm):
    images = MultipleFileField(
        label='图片',
        required=False,
        widget=MultipleFileInput(attrs={
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
            'activity': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['activity'].required = False
        self.fields['activity'].empty_label = '不关联活动'

        if user:
            activity_ids = ActivityRegistration.objects.filter(
                user=user
            ).values_list('activity_id', flat=True)

            self.fields['activity'].queryset = Activity.objects.filter(
                id__in=activity_ids
            ).distinct()
        else:
            self.fields['activity'].queryset = Activity.objects.none()


class MomentCommentForm(forms.ModelForm):
    class Meta:
        model = MomentComment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '发表评论...'
            }),
        }