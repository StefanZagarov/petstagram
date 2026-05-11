from django.urls import path

from photos import views

urlpatterns = (
    path("photo-add/", views.photo_add, name="photo-add"),
    path("<int:pk>/photo-edit/", views.edit, name="photo-edit"),
    path("<int:pk>/photo-details/", views.photo_details, name="photo-details"),
    path("<int:pk>/photo-delete/", views.photo_delete, name="photo-delete"),
)
