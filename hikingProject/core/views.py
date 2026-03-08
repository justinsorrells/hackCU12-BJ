from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import *
from .forms import *

# Create your views here.
@login_required
def home(request):

    events = HikingEvent.objects.filter(
            Q(organizer=request.user) |
            Q(join_requests__user=request.user,
              join_requests__status="approved")
            ).distinct()

    return render(request, "home.html", {"events": events})

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})

@login_required
def search_view(request):
    form = SearchForm(request.GET or None)

    query = ""
    tab = "hikes"
    hikes = HikingEvent.objects.none()
    users = User.objects.none()

    if form.is_valid():
        query = form.cleaned_data.get("q", "")
        tab = form.cleaned_data.get("tab") or "hikes"

        if query:
            hikes = HikingEvent.objects.filter(
                Q(location__icontains=query) |
                Q(description__icontains=query) |
                Q(title__icontains=query)
            ).distinct()

            users = User.objects.filter(
                Q(username__icontains=query) |
                Q(name__icontains=query) |
                Q(location__icontains=query)
            ).exclude(id=request.user.id).distinct()

    return render(request, "search.html", {
        "form": form,
        "query": query,
        "tab": tab,
        "hikes": hikes,
        "users": users,
    })

@login_required
def profile_view(request):
    return render(request, "profile.html")

@login_required
def create_event(request):
    if request.method == "POST":
        form = HikingEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            return redirect("home")
    else:
        form = HikingEventForm()
    return render(request, "create_event.html", {"form": form})

@login_required
def edit_hike(request, hike_id):
    hike = get_object_or_404(HikingEvent, id=hike_id)
    if hike.organizer != request.user:
        return HttpResponseForbidden("You are not allowed to edit this hike.")
    if request.method == "POST":
        form = HikingEventForm(request.POST, instance=hike)
        if form.is_valid():
            updated_hike = form.save(commit=False)
            updated_hike.organizer = request.user
            updated_hike.save()
            return redirect("detail_hike", hike_id=hike_id)
    else:
        form = HikingEventForm(instance=hike)

    return render(request, "edit_event.html", {
        "form": form,
        "hike": hike,
        })

@login_required
def detail_hike(request, hike_id):
    hike = get_object_or_404(HikingEvent, id=hike_id)
    has_pending_request = False
    has_been_rejected = False
    is_participant = False
    has_pending_request = EventJoinRequest.objects.filter(
        event=hike,
        user=request.user,
        status="pending",
    ).exists()
    is_participant = EventJoinRequest.objects.filter(
        event=hike,
        user=request.user,
        status="approved",
    ).exists()
    has_been_rejected = EventJoinRequest.objects.filter(
            event=hike,
            user=request.user,
            status="rejected",
    ).exists()
    return render(request, "detail_hike.html", {"hike": hike, "has_pending_request": has_pending_request, "is_participant": is_participant, "has_been_rejected": has_been_rejected})

@login_required
def edit_profile(request):
    if request.method == "POST":
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("detail_user", user_id=request.user.id)
    else:
        form = EditProfileForm(instance=request.user)

    return render(request, "edit_profile.html", {
        "form": form,
        })

@login_required
def request_to_join_hike(request, hike_id):
    hike = get_object_or_404(HikingEvent, id=hike_id)
    if hike.organizer == request.user:
        return redirect("detail_hike", hike_id=hike.id)
    join_request, created = EventJoinRequest.objects.get_or_create(
            event=hike,
            user=request.user,
            defaults={"status": "pending"}
    )
    return redirect("detail_hike", hike_id=hike.id)

@login_required
def approve_join_request(request, request_id):
    join_request = get_object_or_404(EventJoinRequest, id=request_id)
    if join_request.event.organizer != request.user:
        return redirect("detail_hike", join_request.event.id)
    join_request.status = "approved"
    join_request.save()
    return redirect("detail_hike", hike_id=join_request.event.id)

@login_required
def reject_join_request(request, request_id):
    join_request = get_object_or_404(EventJoinRequest, id=request_id)

    if join_request.event.organizer != request.user:
        return redirect("detail_hike", hike_id=join_request.event.id)

    join_request.status = "rejected"
    join_request.save()

    return redirect("detail_hike", hike_id=join_request.event.id)

@login_required
def detail_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    return render(request, "detail_user.html", {"profile_user": user})

@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        return redirect("register")

    return redirect("edit_profile")
