from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_welcome_email(email):
    # This runs inside a background thread (see accounts/signals.py), so the
    # try/except lives HERE rather than in the signal: a thread that raises just
    # dumps a traceback to the logs and dies, and the signal can't catch it from
    # the outside. Wrapping the whole body keeps any SMTP failure contained.
    #
    # The email is BEST-EFFORT: if Gmail is unreachable or the host blocks
    # outbound SMTP, we swallow the error and move on rather than letting a
    # failed "nice to have" email affect the user's registration in any way.
    #
    # (In a production task-queue setup this would instead RAISE, so the queue
    # could log it and retry. We pass here only because a bare thread can't retry.)
    try:
        username = email.split("@")[0]
        html_content = render_to_string("email-greeting.html", {"username": username})

        email_message = EmailMultiAlternatives(
            subject="Welcome to Petstagram!",
            body="Greetings from Petstagram!",
            to=[email],
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send()
    except Exception:
        pass
