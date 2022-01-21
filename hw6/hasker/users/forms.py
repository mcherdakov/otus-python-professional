from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import User


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'avatar',
            'password1',
            'password2',
        )


class SettingsForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            'email',
            'avatar',
        )
