from django import forms
from .models import Post, Comment


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,video/*',
            'multiple': True,
        }))

        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            result = [single_file_clean(file, initial) for file in data]
        else:
            result = single_file_clean(data, initial)

        return result


class PostForm(forms.ModelForm):
    media_files = MultipleFileField(required=False, label='Photos and videos')

    class Meta:
        model = Post
        fields = ['text']

        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': "What's on your mind?",
                'rows': 4,
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        text = cleaned_data.get('text')
        media_files = cleaned_data.get('media_files')

        if not text and not media_files and not self.instance.media.exists():
            raise forms.ValidationError('Please enter some text or attach photos or videos.')

        if media_files and len(media_files) > 10:
            raise forms.ValidationError('You can upload up to 10 files per post.')

        return cleaned_data

    def clean_media_files(self):
        media_files = self.cleaned_data.get('media_files')

        if not media_files:
            return media_files

        for media_file in media_files:
            content_type = media_file.content_type

            if content_type.startswith('image/'):
                if media_file.size > 5 * 1024 * 1024:
                    raise forms.ValidationError('Each image cannot exceed 5 MB.')

            elif content_type.startswith('video/'):
                if media_file.size > 50 * 1024 * 1024:
                    raise forms.ValidationError('Each video cannot exceed 50 MB.')

            else:
                raise forms.ValidationError('Only image and video files are allowed.')

        return media_files
    

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']

        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control comment-input',
                'placeholder': 'Write a comment...',
                'rows': 2,
            }),
        }


class RepostForm(forms.Form):
    text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Write something about this post...',
            'rows': 4,
        })
    )
    