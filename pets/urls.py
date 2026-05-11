from django.urls import path

from pets import views

# NOTE:.as_view() is a method provided by class-based views to convert it to a function-based view. This is to make the CBV compatible with Django's URL routing system which expects FBV
urlpatterns = [
    path("add", views.AddPetView.as_view(), name="pet-add"),
    path(
        "<str:username>/<slug:pet_slug>/details",
        views.PetDetailsView.as_view(),
        name="pet-details",
    ),
    path(
        "<str:username>/<slug:pet_slug>/edit",
        views.EditPetView.as_view(),
        name="pet-edit",
    ),
    path(
        "<str:username>/<slug:pet_slug>/delete",
        views.DeletePetView.as_view(),
        name="pet-delete",
    ),
]
