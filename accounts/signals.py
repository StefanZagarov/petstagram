import threading

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

        # Send the welcome email in a BACKGROUND THREAD instead of inline.
        #
        # WHY: sending email talks to an external SMTP server (Gmail), which can
        # be slow or blocked — especially from a cloud host. If we sent it inline,
        # the whole registration request would wait on it. In production the web
        # server (gunicorn) kills any request that runs longer than its worker
        # timeout (~30s), returning a 500 to the user *even though the account was
        # already created*. A plain try/except does NOT help here: it only catches
        # an exception, not a hang — the worker is killed before except can run.
        #
        # WHAT THIS SOLVES: spawning a thread lets the request return immediately
        # (registration finishes in milliseconds). The email is attempted off to
        # the side, so a slow/blocked SMTP can no longer hang or 500 the request.
        # daemon=True means this thread won't keep the process alive on shutdown.
        #
        # NOTE — this is a WORKSHOP solution, not the production-standard one.
        # The real-world approach is a task queue (Celery / RQ / Django-Q): the
        # email job is handed to a separate worker process that retries on failure,
        # survives restarts, and doesn't spawn an untracked thread per signup.
        # A bare thread has no retries, no visibility, and is fine only at this scale.
        #
        # CAVEAT: this guarantees registration never breaks, but does NOT guarantee
        # the email is delivered — if the host blocks outbound SMTP, it silently fails.
        threading.Thread(
            target=send_welcome_email, args=(instance.email,), daemon=True
        ).start()
