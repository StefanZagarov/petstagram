from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Profile
from accounts.utils import send_welcome_email

UserModel = get_user_model()


@receiver(post_save, sender=UserModel)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        try:
            # Send an email to greet the new user
            send_welcome_email(instance.email)
        except Exception:
            pass  # a mail failure must not break registration
