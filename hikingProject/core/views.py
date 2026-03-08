import base64
from django.utils import timezone
from io import BytesIO

from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import qrcode
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
    friendships = Friendship.objects.filter(
        Q(requester=request.user, status="accepted") |
        Q(addressee=request.user, status="accepted")
    )

    friend_ids = set()
    for friendship in friendships:
        if friendship.requester_id == request.user.id:
            friend_ids.add(friendship.addressee_id)
        else:
            friend_ids.add(friendship.requester_id)
            
    hikes = HikingEvent.objects.filter(
        Q(visibility="public") |
        Q(visibility="friends", organizer_id__in=friend_ids) |
        Q(organizer=request.user),
        date__gte=timezone.now().date(),
    ).order_by("date", "time").distinct()[:10]

    users = User.objects.exclude(
        Q(id=request.user.id) |
        Q(id__in=friend_ids)
    ).order_by("?")[:10]

    query = ""
    tab = "hikes"

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
def create_event(request):
    if request.method == "POST":
        form = HikingEventForm(request.POST, request.FILES)
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
        form = HikingEventForm(request.POST, request.FILES, instance=hike)
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

    url = request.build_absolute_uri(f"/hikes/{hike.id}/")
    qr = qrcode.make(url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

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
    return render(request, "detail_hike.html", {"hike": hike, "has_pending_request": has_pending_request, "is_participant": is_participant, "has_been_rejected": has_been_rejected, "qr_code": qr_base64})

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
    is_friend = False
    has_sent_request = False
    has_received_request = False
    context = { "profile_user": user}
    if request.user != user:
        is_friend = Friendship.objects.filter(
                Q(requester=request.user, addressee=user) |
                Q(requester=user, addressee=request.user),
                status="accepted",
                ).exists()

        has_sent_request = Friendship.objects.filter(
                requester=request.user,
                addressee=user,
                status="pending",
                ).exists()

        has_received_request = Friendship.objects.filter(
                requester=user,
                addressee=request.user,
                status="pending",
                ).exists()
        my_friendships = Friendship.objects.filter(
            Q(requester=request.user) | Q(addressee=request.user),
            status="accepted",
        )
        my_friend_ids = set()
        for friendship in my_friendships:
            if friendship.requester_id == request.user.id:
                my_friend_ids.add(friendship.addressee_id)
            else:
                my_friend_ids.add(friendship.requester_id)
        # friends of profile user
        profile_friendships = Friendship.objects.filter(
            Q(requester=user) | Q(addressee=user),
            status="accepted",
        )

        profile_friend_ids = set()
        for friendship in profile_friendships:
            if friendship.requester_id == user.id:
                profile_friend_ids.add(friendship.addressee_id)
            else:
                profile_friend_ids.add(friendship.requester_id)

        mutual_friend_ids = my_friend_ids & profile_friend_ids
        mutual_friends = User.objects.filter(id__in=mutual_friend_ids)
        context["mutual_friends"] = mutual_friends
        context["is_profile"] = False

    context["is_friend"] = is_friend
    context["has_sent_request"] = has_sent_request
    context["has_received_request"] = has_received_request

    if request.user == user:
        accepted_friendships = Friendship.objects.filter(
                Q(requester=request.user) | Q(addressee=request.user),
                status="accepted",
                )

        incoming_requests = Friendship.objects.filter(
                addressee=request.user,
                status="pending",
                )
        friends = []
        for friendship in accepted_friendships:
            if friendship.requester == request.user:
                friends.append(friendship.addressee)
            else:
                friends.append(friendship.requester)
        context["friends"] = friends
        context["incoming_requests"] = incoming_requests
        context["is_profile"] = True
    return render(request, "detail_user.html", context)

@login_required
def delete_account(request):
    if request.method == "POST":
        logout(request)
        user.delete()
        return redirect("register")
    return redirect("edit_profile")

@login_required
def send_friend_request(request, user_id):
    if request.method != "POST":
        return redirect("detail_user", user_id=user_id)
    other_user = get_object_or_404(User, id=user_id)
    if other_user == request.user:
        return redirect("detail_user", user_id=user_id)
    existing_friendship = Friendship.objects.filter(
            Q(requester=request.user, addressee=other_user) |
            Q(requester=other_user, addressee=request.user)
            ).first()
    if existing_friendship is None:
        Friendship.objects.create(
                requester=request.user,
                addressee=other_user,
                status="pending",
                )
    return redirect("detail_user", user_id=user_id)

@login_required
def accept_friend_request(request, friendship_id):
    if request.method != "POST":
        return redirect("detail_user", user_id=request.user.id)

    friendship = get_object_or_404(
            Friendship,
            id=friendship_id,
            addressee=request.user,
            status="pending",
            )

    friendship.status = "accepted"
    friendship.save()
    return redirect("detail_user", user_id=request.user.id)

@login_required
def decline_friend_request(request, friendship_id):
    if request.method != "POST":
        return redirect("detail_user", user_id=request.user.id)

    friendship = get_object_or_404(
            Friendship,
            id=friendship_id,
            addressee=request.user,
            status="pending",
            )
    friendship.status = "declined"
    friendship.save()
    return redirect("detail_user", user_id=request.user.id)

@login_required
def remove_friend(request, user_id):
    if request.method != "POST":
        return redirect("detail_user", user_id=user_id)
    other_user = get_object_or_404(User, id=user_id)
    friendship = Friendship.objects.filter(
            Q(requester=request.user, addressee=other_user) |
            Q(requester=other_user, addressee=request.user),
            status="accepted",
            ).first()

    if friendship:
        friendship.delete()
    return redirect("detail_user", user_id=user_id)

@login_required
def send_friend_request(request, user_id):
    if request.method != "POST":
        return redirect("detail_user", user_id=user_id)
    other_user = get_object_or_404(User, id=user_id)
    if other_user == request.user:
        return redirect("detail_user", user_id=user_id)
    existing_friendship = Friendship.objects.filter(
            Q(requester=request.user, addressee=other_user) |
            Q(requester=other_user, addressee=request.user)
            ).first()
    if existing_friendship is None:
        Friendship.objects.create(
                requester=request.user,
                addressee=other_user,
                status="pending",
                )
    return redirect("detail_user", user_id=user_id)

@login_required
def accept_friend_request(request, friendship_id):
    if request.method != "POST":
        return redirect("detail_user", user_id=request.user.id)

    friendship = get_object_or_404(
            Friendship,
            id=friendship_id,
            addressee=request.user,
            status="pending",
            )

    friendship.status = "accepted"
    friendship.save()
    return redirect("detail_user", user_id=request.user.id)

@login_required
def decline_friend_request(request, friendship_id):
    if request.method != "POST":
        return redirect("detail_user", user_id=request.user.id)

    friendship = get_object_or_404(
            Friendship,
            id=friendship_id,
            addressee=request.user,
            status="pending",
            )
    friendship.status = "declined"
    friendship.save()
    return redirect("detail_user", user_id=request.user.id)

@login_required
def remove_friend(request, user_id):
    if request.method != "POST":
        return redirect("detail_user", user_id=user_id)
    other_user = get_object_or_404(User, id=user_id)
    friendship = Friendship.objects.filter(
            Q(requester=request.user, addressee=other_user) |
            Q(requester=other_user, addressee=request.user),
            status="accepted",
            ).first()

    if friendship:
        friendship.delete()
    return redirect("detail_user", user_id=user_id)

@login_required
def delete_hike(request, hike_id):
    hike = get_object_or_404(HikingEvent, id=hike_id)
    if hike.organizer != request.user:
        return redirect("detail_hike", hike_id=hike.id)
    if request.method == "POST":
        hike.delete()
        return redirect("home")
    return redirect("detail_hike", hike_id=hike_id)

@login_required
def report_user(request, user_id):
    reported_user = get_object_or_404(User, id=user_id)
    if reported_user == request.user:
        return redirect("detail_user", user_id=user_id)

    if request.method == "POST":
        form = ReportUserForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data["reason"]
            details = form.cleaned_data["details"]

            subject = f"User Report: {reported_user.username}"
            message = (
                f"Reporter: {request.user.username} (id={request.user.id})\n"
                f"Reported user: {reported_user.username} (id={reported_user.id})\n"
                f"Reason: {reason}\n\n"
                f"Details:\n{details}"
            )

            send_mail(
                subject,
                message,
                None,  # uses DEFAULT_FROM_EMAIL
                ["justinwsorrells@gmail.com", "benjaminmst@gmail.com"],
                fail_silently=False,
            )

            return redirect("detail_user", user_id=user_id)
    else:
        form = ReportUserForm()

    return render(request, "report_user.html", {
        "form": form,
        "reported_user": reported_user,
    })

