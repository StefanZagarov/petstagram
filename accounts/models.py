# Note: if you are building an app with user authentication, you should consider creating a custom user model at the beginning of the work process
from django.conf import settings
from django.contrib.auth import models as auth_models
from django.db import models

from accounts.managers import AppUserManager


# Creating a custom user model inheriting from the AbstractBaseUser. Its called AppUser because Django already has a User model
class AppUser(auth_models.AbstractUser):
    email = models.EmailField(null=False, blank=False, unique=True)
    username = None

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = AppUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True
    )

    first_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.URLField(null=True, blank=True)

    def get_profile_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name or self.last_name:
            return self.first_name or self.last_name
        else:
            return "Anonymus User"
