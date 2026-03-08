from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("create_event/", views.create_event, name="create_event"), 
    path("hike/<int:hike_id>/edit/", views.edit_hike, name="edit_hike"), 
    path("hike/<int:hike_id>/", views.detail_hike, name="detail_hike"),
    path("search/", views.search_view, name="search"),
    path("edit_profile/", views.edit_profile, name="edit_profile"),
]
