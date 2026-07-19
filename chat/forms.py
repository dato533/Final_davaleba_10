from django import forms
from users.models import CustomUser
from .models import Conversation, Message


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['text', 'image', 'video', 'file']

        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control message-input',
                'placeholder': 'Write a message...',
                'rows': 2,
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'video': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*',
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        text = cleaned_data.get('text')
        image = cleaned_data.get('image')
        video = cleaned_data.get('video')
        file = cleaned_data.get('file')

        if not text and not image and not video and not file:
            raise forms.ValidationError('Please enter a message or attach an image, video, or file.')

        return cleaned_data

    def clean_image(self):
        image = self.cleaned_data.get('image')

        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('The image size cannot exceed 5 MB.')

        return image

    def clean_video(self):
        video = self.cleaned_data.get('video')

        if video and video.size > 50 * 1024 * 1024:
            raise forms.ValidationError('The video size cannot exceed 50 MB.')

        return video

    def clean_file(self):
        file = self.cleaned_data.get('file')

        if file and file.size > 20 * 1024 * 1024:
            raise forms.ValidationError('The file size cannot exceed 20 MB.')

        return file


class GroupConversationForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label='Participants'
    )

    class Meta:
        model = Conversation
        fields = ['name', 'image', 'participants']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Group name',
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['participants'].queryset = user.get_friends().exclude(id=user.id)

    def clean_participants(self):
        participants = self.cleaned_data.get('participants')

        if participants.count() < 1:
            raise forms.ValidationError('Select at least one participant.')

        return participants