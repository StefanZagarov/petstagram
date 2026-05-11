from django.shortcuts import render

def register(request):
    return render(request, template_name="accounts/register-page.html")

def login(request):
    return None

def show_profile_details(request):
    return None

def edit_profile(request):
    return None

def delete_profile(request):
    return None
