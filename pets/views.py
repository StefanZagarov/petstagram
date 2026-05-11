from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from common.forms import CommentForm
from pets.forms import PetDeleteForm, PetForm
from pets.models import Pet


# --- Class Based View (CBV) ---
class AddPetView(CreateView):
    # Specifies the model that the view is associated with, in this case, the Pet model
    model = Pet
    # Specifies the form class to be used for handling input data. In this context, it's set to PetForm, the form class associated with the Pet model
    form_class = PetForm
    # Specifies the template file that will be used to render the HTML content for this view
    template_name = "pets/pet-add-page.html"
    # Specifies the URL to redirect to after a successful form submission. In this case, it uses reverse_lazy to dynamically generate the URL for the 'profile-details' view with a specific primary key (pk=1). The use of reverse_lazy allows for resolving the URL at runtime
    success_url = reverse_lazy("profile-details", kwargs={"pk": 1})


# CBV
class PetDetailsView(DetailView):
    model = Pet
    template_name = "pets/pet-details-page.html"
    # Assigns the name 'pet' to the object retrieved from the database, making it accessible in the templat
    context_object_name = "pet"
    # Captures the pet's slug from the URL and passes it as a keyword argument to the view
    slug_url_kwarg = "pet_slug"

    # The get_context_data method is overridden to enhance the context with additional data:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Retrieves all photos related to the pet using the reverse relation photo_set
        context["all_photos"] = self.object.photo_set.all()
        # Includes a new instance of the CommentForm to handle comments
        context["comment_form"] = CommentForm()
        return context


class EditPetView(UpdateView):
    model = Pet
    form_class = PetForm
    template_name = "pets/pet-edit-page.html"
    slug_url_kwarg = "pet_slug"
    context_object_name = "pet"

    # Method is overridden to customize the redirect URL
    def get_success_url(self):
        # reverse_lazy is used to dynamically generate the URL based on the pet-details URL pattern. The kwargs parameter allows you to pass dynamic values to the URL pattern. In this case, it constructs the URL using the username and pet_slug from the current instance's kwargs
        return reverse_lazy(
            "pet-details",
            kwargs={
                "username": self.kwargs["username"],
                "pet_slug": self.kwargs["pet_slug"],
            },
        )

# In the DeletePetView class-based view, several methods are overridden to customize the behavior of the view.
# Here's an explanation of each method:

class DeletePetView(DeleteView):
    model = Pet
    template_name = "pets/pet-delete-page.html"
    context_object_name = "pet"
    success_url = reverse_lazy("profile-details", kwargs={"pk": 1})

    # This method is used to return the queryset of objects that the DeleteView operates on
    # In the DeletePetView, it is overridden to filter the queryset based on the pet_slug from the URL parameters
    # This method helps define which set of objects can be deleted. In this case, it ensures that only the specific Pet object with the given slug can be deleted
    def get_object(self, queryset=None):
        return Pet.objects.get(slug=self.kwargs["pet_slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = PetDeleteForm(initial=self.object.__diuct__)
        return context

    # In the DeletePetView, it uses the get_object method to retrieve the specific Pet object to be deleted
    # After retrieving the object, it calls the delete method on the object to remove it from the database
    # Finally, it redirects the user to the specified success_url, which, in this case, is the 'profile-details' page
    def delete(self, request, *args, **kwargs):
        pet = self.get_object()
        pet.delete()
        return redirect(self.success_url)


# --- Function Based View (FBV) ---

# def add_pet(request):
#     form = PetForm(request.POST or None)
#     if form.is_valid():
#         form.save()
#         return redirect("profile-details", pk=1)
#     context = {"form": form}
#     return render(request, template_name="pets/pet-add-page.html", context=context)

# def details(request, username, pet_slug):
#     pet = Pet.objects.get(slug=pet_slug)
#     comment_form = CommentForm()
#
#     all_photos = pet.photo_set.all()
#     context = {"pet": pet, "comment_form": comment_form, "all_photos": all_photos}
#     return render(request, template_name="pets/pet-details-page.html", context=context)


# def edit(request, username, pet_slug):
#     pet = Pet.objects.get(slug=pet_slug)
#     if request.method == "GET":
#         form = PetForm(instance=pet, initial=pet.__dict__)
#     else:
#         form = PetForm(request.POST, instance=pet)
#         if form.is_valid():
#             form.save()
#             return redirect("pet-details", username, pet_slug)
#     context = {"form": form}
#     return render(request, template_name="pets/pet-edit-page.html", context=context)


# def delete(request, pet_slug):
#     pet = Pet.objects.get(slug=pet_slug)
#     if request.method == "POST":
#         pet.delete()
#         return redirect("profile-details", pk=1)
#     form = PetDeleteForm(initial=pet.__dict__)
#     context = {"form": form}
#
#     return render(request, template_name="pets/pet-delete-page.html", context=context)
