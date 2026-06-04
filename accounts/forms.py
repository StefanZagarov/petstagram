from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)

from accounts.models import Profile

UserModel = get_user_model()


class AppUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = UserModel


class AppUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = UserModel
        fields = ("email",)


class AppUserLoginForm(AuthenticationForm):
    # We set the username here, despite logging in with email, because the AuthenticationForm internally is looking for the username, meanwhile we made our app to require email. So we populate the username field instead of the email field from AuthenticationForm in order to satisfy it's requirement
    username = forms.EmailField(widget=forms.EmailInput(attrs={"autofocus": True}))
    # May be redundant since its defined under the hood already, but shows how its done
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["first_name", "last_name", "date_of_birth", "profile_picture"]
        labels = {
            "first_name": "First Name:",
            "last_name": "Last Name:",
            "date_of_birth": "Date of Birth:",
            "profile_picture": "Profile Picture:",
        }
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}
