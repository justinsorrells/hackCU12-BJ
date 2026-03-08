from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("create_event/", views.create_event, name="create_event"), 
    path("hike/<int:hike_id>/edit/", views.edit_hike, name="edit_hike"), 
    path("hike/<int:hike_id>/", views.detail_hike, name="detail_hike"),
    path("hike/<int:hike_id>/request-join/", views.request_to_join_hike, name="request_to_join_hike"),
    path("join-requests/<int:request_id>/approve/", views.approve_join_request, name="approve_join_request"),
    path("join-requests/<int:request_id>/reject/", views.reject_join_request, name="reject_join_request"),
    path("search/", views.search_view, name="search"),
    path("edit_profile/", views.edit_profile, name="edit_profile"),
    path("account/delete/", views.delete_account, name="delete_account"),
    path("user/<int:user_id>/", views.detail_user, name="detail_user"),
    path("password/change/", auth_views.PasswordChangeView.as_view(template_name="password_change.html"), name="password_change"),
    path("password/change/done/", auth_views.PasswordChangeDoneView.as_view(template_name="password_change_done.html"), name="password_change_done"),
    path("friends/request/<int:user_id>/", views.send_friend_request, name="send_friend_request"),
    path("friends/accept/<int:friendship_id>/", views.accept_friend_request, name="accept_friend_request"),
    path("friends/decline/<int:friendship_id>/", views.decline_friend_request, name="decline_friend_request"),
    path("friends/remove/<int:user_id>/", views.remove_friend, name="remove_friend"),
    path("delete_hike/<int:hike_id>/", views.delete_hike, name="delete_hike"),
    path("user/<int:user_id>/report/", views.report_user, name="report_user"),
]
