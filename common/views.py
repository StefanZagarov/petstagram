from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import redirect, render, resolve_url
from django.views.generic import ListView
from pyperclip import copy

from common.forms import CommentForm, SearchForm
from common.models import Like
from photos.models import Photo


class HomePageView(ListView):
    model = Photo
    template_name = "common/home-page.html"
    context_object_name = "all_photos"
    paginate_by = 1

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comment_form"] = CommentForm()
        context["search_form"] = SearchForm(self.request.GET)
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        pet_name = self.request.GET.get("pet_name")
        if pet_name:
            self.request.session["pet_name"] = pet_name
        else:
            self.request.session.pop("pet_name", None)

        pet_name_session = self.request.session.get("pet_name")

        if pet_name:
            queryset = queryset.filter(tagged_pets__name__icontains=pet_name_session)

        return queryset


# def home(request):
#     all_photos = Photo.objects.all()
#     comment_form = CommentForm()
#     search_form = SearchForm(request.GET)
#
#     if request.method == "POST":
#         search_form = SearchForm(request.POST)
#         if search_form.is_valid():
#             all_photos = all_photos.filter(
#                 tagged_pets__name__icontains=search_form.cleaned_data["pet_name"]
#             )
#
#     photos_per_page = 1
#     paginator = Paginator(all_photos, photos_per_page)
#     page = request.GET.get("page")
#
#     try:
#         all_photos = paginator.page(page)
#     except PageNotAnInteger:
#         all_photos = paginator.page(1)
#     except EmptyPage:
#         all_photos = paginator.page(paginator.num_pages)
#
#     if search_form.is_valid() and search_form.cleaned_data["pet_name"]:
#         all_photos = all_photos.filter(
#             tagged_pets__name__icontains=search_form.cleaned_data["pet_name"]
#         )
#
#     context = {
#         "comment_form": comment_form,
#         "all_photos": all_photos,
#         "search_form": search_form,
#     }
#
#     return render(request, template_name="common/home-page.html", context=context)


def like_functionality(request, photo_id):
    photo = Photo.objects.get(id=photo_id)
    liked_object = Like.objects.filter(to_photo_id=photo_id, user=request.user).first()

    if liked_object:
        liked_object.delete()
    else:
        like = Like(to_photo=photo, user=request.user)
        like.save()

    return redirect(request.META["HTTP_REFERER"] + f"#{photo_id}")


def copy_link_to_clipboard(request, photo_id):
    copy(request.META["HTTP_HOST"] + resolve_url("photo-details", photo_id))

    return redirect(request.META["HTTP_REFERER"] + f"#{photo_id}")


def add_comment(request, photo_id):
    if request.method == "POST":
        photo = Photo.objects.get(id=photo_id)
        form = CommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.to_photo = photo
            comment.user = request.user
            comment.save()

    return redirect(request.META["HTTP_REFERER"] + f"#{photo_id}")
