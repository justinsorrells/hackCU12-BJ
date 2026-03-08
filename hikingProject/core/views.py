from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import HikingEvent
from .forms import RegisterForm, HikingEventForm

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

def search_hikes_view(request):
    query = request.GET.get("q", "")
    hikes = HikingEvent.objects.filter(
        Q(location__icontains=query) |
        Q(description__icontains=query)
    ).distinct()
    return render(request, "search_results.html", {"hikes": hikes, "query": query})

def search_friends_view(request):
    query = request.GET.get("q", "")
    friends = request.user.friends.filter(
        Q(username__icontains=query) |
        Q(location__icontains=query)
    ).distinct()
    return render(request, "friend_search_results.html", {"friends": friends, "query": query})

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
