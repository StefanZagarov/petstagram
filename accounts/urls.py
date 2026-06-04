from django.urls import include, path

from accounts import views

urlpatterns = [
    path("register", views.AppUsersRegisterView.as_view(), name="register"),
    path("login", views.AppUserLoginView.as_view(), name="login"),
    path("logout", views.AppUserLogoutView.as_view(), name="logout"),
    path(
        "profile/<int:pk>/",
        include(
            [
                path("", views.AppUserDetailsView.as_view(), name="profile-details"),
                path("edit/", views.ProfileEditView.as_view(), name="profile-edit"),
                path(
                    "delete", views.AppUserDeleteView.as_view(), name="profile-delete"
                ),
            ]
        ),
    ),
]
