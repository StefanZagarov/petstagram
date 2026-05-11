from django.urls import path

from common import views

urlpatterns = [
    path("", views.HomePageView.as_view(), name="home"),
    path("<int:photo_id>/like", views.like_functionality, name="like"),
    path("<int:photo_id>/share", views.copy_link_to_clipboard, name="share"),
    path("<int:photo_id>/comment", views.add_comment, name="comment"),
]
