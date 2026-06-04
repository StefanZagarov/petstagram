from django.contrib import admin

from common.models import Comment, Like

admin.site.register(Comment)
admin.site.register(Like)
