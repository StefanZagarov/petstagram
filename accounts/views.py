from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import generic as views

from accounts.forms import AppUserCreationForm, AppUserLoginForm, ProfileEditForm
from accounts.models import Profile
from photos.models import Photo

UserModel = get_user_model()

# Superuser: war@gmail.com
# Pass: 1234
# User: warbeast@gmail.com
# Pass: 794613aa


class AppUsersRegisterView(views.CreateView):
    model = UserModel
    form_class = AppUserCreationForm
    template_name = "accounts/register-page.html"
    success_url = reverse_lazy("login")


class AppUserLoginView(auth_views.LoginView):
    form_class = AppUserLoginForm
    template_name = "accounts/login-page.html"

    # Creating relationship between AppUser and Profile through the login view is not the most accurate way. We can do this with Django signals.
    # This is why we will replace the form_valid method. Instead we will use a create_profile signal
    # def form_valid(self, form):
    #     super().form_valid(form)
    #     profile_instance, _ = Profile.objects.get_or_create(user=self.request.user)
    #     return HttpResponseRedirect(self.get_success_url())


class AppUserLogoutView(auth_views.LogoutView):
    pass


class AppUserDetailsView(views.DetailView):
    model = UserModel
    template_name = "accounts/profile-details-page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["total_likes_count"] = sum(
            p.like_set.count() for p in self.object.photo_set.all()
        )

        context["user_photos"] = Photo.objects.filter(user_id=self.object.pk).order_by(
            "-date_of_publication"
        )

        return context


class ProfileEditView(views.UpdateView):
    model = Profile
    form_class = ProfileEditForm
    template_name = "accounts/profile-edit-page.html"

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_success_url(self):
        return reverse_lazy("profile-details", kwargs={"pk": self.object.pk})


class AppUserDeleteView(views.DeleteView):
    model = UserModel
    template_name = "accounts/profile-delete-page.html"
    success_url = reverse_lazy("home")

    def get_object(self, queryset=None):
        return self.request.user

    # Redundant as this is done automatically already by the delete view, but keeping it as reference
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        user.delete()
        return redirect(self.get_success_url())
