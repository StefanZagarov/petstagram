from django import template

# Register it with the Django template library. The register object is what Django scans for when it loads your custom_filters.py. The @register.filter decorator says "make this function available as a |placeholder filter in templates."

register = template.Library()


# Define filter
@register.filter
def placeholder(value, token):
    value.field.widget.attrs["placeholder"] = token
    return value


@register.filter
def is_liked_by(photo, user):
    if not user.is_authenticated:
        return False
    exists = photo.like_set.filter(user=user).exists()
    return exists
