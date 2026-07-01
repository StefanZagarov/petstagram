from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_welcome_email(email):
    username = email.split("@")[0]
    html_content = render_to_string("email-greeting.html", {"username": username})

    email_message = EmailMultiAlternatives(
        subject="Welcome to Petstagram!",
        body="Greetings from Petstagram!",
        to=[email],
    )
    email_message.attach_alternative(html_content, "text/html")
    email_message.send()
