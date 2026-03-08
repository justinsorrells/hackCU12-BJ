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

    query = ""
    tab = "hikes"

    hikes = HikingEvent.objects.none()
    users = User.objects.none()

    if form.is_valid():
        query = form.cleaned_data.get("q", "").strip()
        tab = form.cleaned_data.get("tab") or "hikes"

        if tab == "hikes":
            hikes = HikingEvent.objects.filter(
                    Q(visibility="public") |
                    Q(visibility="friends", organizer_id__in=friend_ids) |
                    Q(organizer=request.user),
                    date__gte=timezone.now().date(),
                    ).order_by("date", "time").distinct()

            if query:
                hikes = hikes.filter(
                        Q(location__icontains=query) |
                        Q(description__icontains=query) |
                        Q(title__icontains=query)
                        )

            pace = form.cleaned_data.get("pace")
            experience = form.cleaned_data.get("experience")
            date = form.cleaned_data.get("date")
            max_mileage = form.cleaned_data.get("max_mileage")

            if pace:
                hikes = hikes.filter(pace=pace)

            if experience:
                hikes = hikes.filter(recommended_experience=experience)

            if date:
                hikes = hikes.filter(date=date)

            if max_mileage is not None:
                hikes = hikes.filter(mileage__lte=max_mileage)

            hikes = hikes[:10]

        else:
            users = User.objects.exclude(
                    Q(id=request.user.id) |
                    Q(id__in=friend_ids)
                    ).distinct()

            if query:
                users = users.filter(
                        Q(username__icontains=query) |
                        Q(name__icontains=query) |
                        Q(location__icontains=query)
                        )

            location = form.cleaned_data.get("location")
            gender = form.cleaned_data.get("gender")
            min_age = form.cleaned_data.get("min_age")
            max_age = form.cleaned_data.get("max_age")
            user_experience = form.cleaned_data.get("user_experience")
            user_pace = form.cleaned_data.get("user_pace")

            if location:
                users = users.filter(location__icontains=location)

            if gender:
                users = users.filter(gender=gender)

            if min_age is not None:
                users = users.filter(age__gte=min_age)

            if max_age is not None:
                users = users.filter(age__lte=max_age)

            if user_experience:
                users = users.filter(experience_level=user_experience)

            if user_pace:
                users = users.filter(pace=user_pace)

            users = users[:10]

    else:
        hikes = HikingEvent.objects.filter(
                Q(visibility="public") |
                Q(visibility="friends", organizer_id__in=friend_ids) |
                Q(organizer=request.user),
                date__gte=timezone.now().date(),
                ).order_by("date", "time").distinct()[:10]

        users = User.objects.exclude(
                Q(id=request.user.id) |
                Q(id__in=friend_ids)
                ).distinct()[:10]

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

            participants = User.objects.filter(
                    event_join_requests__event=hike,
                    event_join_requests__status="approved",
                    ).exclude(id=request.user.id)

            notifications = [
                    Notification(
                        recipient=participant,
                        sender=hike.organizer,
                        hike=hike,
                        message=f"{request.user.username} updated the hike '{hike.title}'.",
                        )
                    for participant in participants
                    ]
            Notification.objects.bulk_create(notifications)
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

    is_driver = CarpoolOffer.objects.filter(event=hike, driver=request.user).exists()

    has_pending_request = False
    has_been_rejected = False
    is_participant = False
    can_view_thread = False
    can_view_thread = (
            request.user == hike.organizer or
            EventJoinRequest.objects.filter(
                event=hike,
                user=request.user,
                status="approved"
                ).exists()
            )
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
    accepted_users = User.objects.filter(
            event_join_requests__event=hike,
            event_join_requests__status="approved",
            )
    return render(request, "detail_hike.html", {"can_view_thread": can_view_thread, "accepted_users": accepted_users, "hike": hike, "has_pending_request": has_pending_request, "is_participant": is_participant, "has_been_rejected": has_been_rejected, "qr_code": qr_base64, "is_driver": is_driver})

@login_required
def leave_hike(request, hike_id):
    hike = get_object_or_404(HikingEvent, id=hike_id)
    if hike.organizer == request.user:
        return redirect("detail_hike", hike_id=hike.id)
    join_request = EventJoinRequest.objects.filter(
            event=hike,
            user=request.user,
            status="approved",
            ).first()
    if join_request:
        join_request.delete()
        Notification.objects.create(
                recipient=hike.organizer,
                message=f"{request.user.username} left your hike '{hike.title}'.",
                )
    return redirect("detail_hike", hike_id=hike.id)

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
    if created:
        Notification.objects.create(
                recipient=hike.organizer,
                sender=request.user,
                hike=hike,
                message=f"{request.user.username} requested to join your hike '{hike.title}'.",
                )
    return redirect("detail_hike", hike_id=hike.id)

@login_required
def approve_join_request(request, request_id):
    join_request = get_object_or_404(EventJoinRequest, id=request_id)
    if join_request.event.organizer != request.user:
        return redirect("detail_hike", join_request.event.id)
    join_request.status = "approved"
    join_request.save()
    Notification.objects.create(
            recipient=join_request.user,
            sender=request.user,
            hike=join_request.event,
            message=f"You were approved to join '{join_request.event.title}'.",
            )
    return redirect("detail_hike", hike_id=join_request.event.id)

@login_required
def reject_join_request(request, request_id):
    join_request = get_object_or_404(EventJoinRequest, id=request_id)

    if join_request.event.organizer != request.user:
        return redirect("detail_hike", hike_id=join_request.event.id)

    join_request.status = "rejected"
    join_request.save()

    Notification.objects.create(
            recipient=join_request.user,
            sender=request.user,
            hike=join_request.event,
            message=f"Your request to join '{join_request.event.title}' was rejected.",
            )
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
    user = request.user
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
        Notification.objects.create(
                recipient=other_user,
                sender=request.user,
                message=f"{request.user.username} sent you a friend request.",
                )
    return redirect("detail_user", user_id=user_id)

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
    Notification.objects.create(
            recipient=friendship.requester,
            sender=request.user,
            message=f"{request.user.username} accepted your friend request.",
            )
    return redirect("detail_user", user_id=request.user.id)


@login_required
def delete_hike(request, hike_id):
    hike = get_object_or_404(HikingEvent, id=hike_id)
    if hike.organizer != request.user:
        return redirect("detail_hike", hike_id=hike_id)
    if request.method == "POST":
        participants = User.objects.filter(
                event_join_requests__event=hike,
                event_join_requests__status="approved",
                ).exclude(id=request.user.id)

        notifications = [
                Notification(
                    recipient=participant,
                    message=f"The hike '{hike.title}' has been deleted by the organizer.",
                    )
                for participant in participants
                ]
        Notification.objects.bulk_create(notifications)
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

@login_required
def remove_participant(request, hike_id, user_id):
    if request.method != "POST":
        return redirect("detail_hike", hike_id=hike_id)

    hike = get_object_or_404(HikingEvent, id=hike_id)

    if hike.organizer != request.user:
        return redirect("detail_hike", hike_id=hike_id)

    participant = get_object_or_404(User, id=user_id)

    join_request = get_object_or_404(
            EventJoinRequest,
            event=hike,
            user=participant,
            status="approved",
            )
    Notification.objects.create(
            recipient=participant,
            sender=request.user,
            hike=hike,
            message=f"You have been removed from '{hike.title}'.",
            )
    join_request.delete()

    return redirect("detail_hike", hike_id=hike_id)

@login_required
def hike_thread(request, hike_id):
    hike = get_object_or_404(HikingEvent, id=hike_id)
    is_participant = EventJoinRequest.objects.filter(
            event=hike,
            user=request.user,
            status="approved"
            ).exists()
    if hike.organizer != request.user and not is_participant:
        return HttpResponseForbidden("You are not allowed to view this thread.")
    Notification.objects.filter(
            recipient=request.user,
            hike=hike,
            is_read=False,
            message=f"You have unread messages in '{hike.title}'.",
            ).update(is_read=True)
    messages = hike.messages.select_related("user").order_by("created_at")
    if request.method == "POST":
        form = HikeMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.event = hike
            message.user = request.user
            message.save()

            recipients = list(
                    User.objects.filter(
                        event_join_requests__event=hike,
                        event_join_requests__status="approved",
                        ).exclude(id=request.user.id)
                    )

            if hike.organizer != request.user and hike.organizer not in recipients:
                recipients.append(hike.organizer)

            for recipient in recipients:
                already_has_unread_notification = Notification.objects.filter(
                        recipient=recipient,
                        hike=hike,
                        is_read=False,
                        message=f"You have unread messages in '{hike.title}'.",
                        ).exists()

                if not already_has_unread_notification:
                    Notification.objects.create(
                            recipient=recipient,
                            hike=hike,
                            message=f"You have unread messages in '{hike.title}'.",
                            )

            return redirect("hike_thread", hike_id=hike.id)
    else:
        form = HikeMessageForm()

    return render(request, "hike_thread.html", {
        "hike": hike,
        "messages": messages,
        "form": form,
        })

@login_required
def notifications(request):
    notification = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    notification.filter(is_read=False).update(is_read=True)
    return render(request, "notifications.html", {
        "notifications": notification,
        })

@login_required
def cancel_hike_request(request, hike_id):
    if request.method != "POST":
        return redirect("detail_hike", hike_id=hike_id)

    join_request = get_object_or_404(
            EventJoinRequest,
            event_id=hike_id,
            user=request.user,
            status="pending",
            )
    Notification.objects.create(
            recipient=join_request.event.organizer,
            sender=request.user,
            hike=join_request.event,
            notification_type="hike_join_request",
            message=f"{request.user.username} cancelled their request to join '{join_request.event.title}'.",
            )
    join_request.delete()
    return redirect("detail_hike", hike_id=hike_id)

@login_required
def cancel_friend_request(request, user_id):
    if request.method != "POST":
        return redirect("detail_user", user_id=user_id)

    friendship = get_object_or_404(
            Friendship,
            requester=request.user,
            addressee_id=user_id,
            status="pending",
            )
    friendship.delete()
    return redirect("detail_user", user_id=user_id)
def offer_carpool(request, hike_id):
    hike = get_object_or_404(HikingEvent, id=hike_id)

    is_participant_or_organizer = EventJoinRequest.objects.filter(
        event=hike,
        user=request.user,
        status="approved",
    ).exists() or hike.organizer == request.user

    is_already_offering = CarpoolOffer.objects.filter(
        event=hike,
        driver=request.user,
    ).exists()

    if not is_participant_or_organizer or is_already_offering:
        return redirect("detail_hike", hike_id=hike_id)

    if request.method == "POST":
        form = CarpoolOfferForm(request.POST)
        if form.is_valid():
            carpool_offer = form.save(commit=False)
            carpool_offer.event = hike
            carpool_offer.driver = request.user
            carpool_offer.save()
            return redirect("view_carpool_offers", hike_id=hike_id)
    else:
        form = CarpoolOfferForm()

    return render(request, "offer_carpool.html", {
        "form": form,
        "hike": hike,
    })

@login_required
def approve_carpool_request(request, request_id):
    carpool_request = get_object_or_404(CarpoolRequest, id=request_id)
    if carpool_request.carpool_offer.driver != request.user:
        return redirect("view_carpool_offers", hike_id=carpool_request.carpool_offer.event.id)

    if carpool_request.carpool_offer.seats_remaining <= 0:
        return redirect("view_carpool_offers", hike_id=carpool_request.carpool_offer.event.id)

    carpool_request.status = "approved"
    carpool_request.save()
    Notification.objects.create(
        recipient=carpool_request.rider,
        sender=request.user,
        hike=carpool_request.carpool_offer.event,
        notification_type="hike_message",  # or add "carpool_approved" if you want a new type
        message=f"Your carpool request for '{carpool_request.carpool_offer.event.title}' was approved.",
    )
    return redirect("view_carpool_offers", hike_id=carpool_request.carpool_offer.event.id)

@login_required
def reject_carpool_request(request, request_id):
    carpool_request = get_object_or_404(CarpoolRequest, id=request_id)
    if carpool_request.carpool_offer.driver != request.user:
        return redirect("view_carpool_offers", hike_id=carpool_request.carpool_offer.event.id)

    Notification.objects.create(
        recipient=carpool_request.rider,
        sender=request.user,
        hike=carpool_request.carpool_offer.event,
        notification_type="hike_message",  # or use a new type like "carpool_rejected"
        message=f"Your carpool request for '{carpool_request.carpool_offer.event.title}' was rejected.",
    )

    carpool_request.delete()
    return redirect("view_carpool_offers", hike_id=carpool_request.carpool_offer.event.id)

@login_required
def edit_carpool_offer(request, offer_id):
    offer = get_object_or_404(CarpoolOffer, id=offer_id)
    hike = offer.event

    if request.user != offer.driver:
        return redirect("view_carpool_offers", hike_id=hike.id)

    if request.method == "POST":
        form = CarpoolOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            riders = User.objects.filter(
                carpool_requests__carpool_offer=offer,
                carpool_requests__status="approved",
            ).exclude(id=request.user.id)

            notifications = [
                Notification(
                    recipient=rider,
                    sender=request.user,
                    hike=hike,
                    notification_type="carpool_approved",
                    message=f"{request.user.username} updated the carpool for '{hike.title}'.",
                )
                for rider in riders
            ]
            Notification.objects.bulk_create(notifications)
            return redirect("view_carpool_offers", hike_id=hike.id)
    else:
        form = CarpoolOfferForm(instance=offer)

    return render(request, "edit_carpool.html", {
        "form": form,
        "hike": hike,
        "offer": offer,
    })

@login_required
def leave_carpool(request, offer_id):
    offer = get_object_or_404(CarpoolOffer, id=offer_id)

    if request.user == offer.driver:
        return redirect("view_carpool_offers", hike_id=offer.event.id)

    carpool_request = CarpoolRequest.objects.filter(
        carpool_offer=offer,
        rider=request.user,
        status="approved",
    ).first()

    if carpool_request:
        Notification.objects.create(
            recipient=offer.driver,
            sender=request.user,
            hike=offer.event,
            notification_type="carpool_request",
            message=f"{request.user.username} left your carpool for '{offer.event.title}'.",
        )
        carpool_request.delete()

    return redirect("view_carpool_offers", hike_id=offer.event.id)

@login_required
def cancel_carpool_request(request, request_id):
    carpool_request = get_object_or_404(CarpoolRequest, id=request_id)

    if request.user != carpool_request.rider:
        return redirect("view_carpool_offers", hike_id=carpool_request.carpool_offer.event.id)

    if carpool_request.status == "approved":
        return redirect("view_carpool_offers", hike_id=carpool_request.carpool_offer.event.id)

    carpool_request.delete()
    return redirect("view_carpool_offers", hike_id=carpool_request.carpool_offer.event.id)

@login_required
def remove_carpool_participant(request, offer_id, user_id):
    offer = get_object_or_404(CarpoolOffer, id=offer_id)

    if request.user != offer.driver:
        return redirect("view_carpool_offers", hike_id=offer.event.id)

    participant = get_object_or_404(User, id=user_id)

    carpool_request = get_object_or_404(
        CarpoolRequest,
        carpool_offer=offer,
        rider=participant,
        status="approved",
    )

    Notification.objects.create(
        recipient=participant,
        sender=request.user,
        hike=offer.event,
        notification_type="participant_removed",
        message=f"You have been removed from the carpool for '{offer.event.title}'.",
    )
    carpool_request.delete()

    return redirect("view_carpool_offers", hike_id=offer.event.id)

@login_required
def view_carpool_offers(request, hike_id):
    hike = get_object_or_404(HikingEvent, id=hike_id)

    user_offer = CarpoolOffer.objects.filter(
        event=hike,
        driver=request.user
    ).first()

    carpool_offers = CarpoolOffer.objects.filter(
        event=hike
    ).select_related("driver").prefetch_related("ride_requests__rider")

    for offer in carpool_offers:
        offer.user_request = offer.ride_requests.filter(rider=request.user).first()

    return render(request, "carpool_offers.html", {
        "hike": hike,
        "carpool_offers": carpool_offers,
        "user_offer": user_offer,
    })

@login_required
def delete_carpool_offer(request, offer_id):
    offer = get_object_or_404(CarpoolOffer, id=offer_id)

    if offer.driver != request.user:
        return redirect("view_carpool_offers", hike_id=offer.event.id)

    if request.method == "POST":
        riders = User.objects.filter(
            carpool_requests__carpool_offer=offer,
            carpool_requests__status="approved",
        ).exclude(id=request.user.id)

        notifications = [
            Notification(
                recipient=rider,
                sender=request.user,
                hike=offer.event,
                notification_type="participant_removed",
                message=f"The carpool for '{offer.event.title}' has been cancelled.",
            )
            for rider in riders
        ]
        Notification.objects.bulk_create(notifications)
        offer.delete()

    return redirect("view_carpool_offers", hike_id=offer.event.id)

@login_required
def request_carpool(request, offer_id):
    offer = get_object_or_404(CarpoolOffer, id=offer_id)

    if offer.driver == request.user:
        return redirect("view_carpool_offers", hike_id=offer.event.id)

    is_participant = EventJoinRequest.objects.filter(
        event=offer.event,
        user=request.user,
        status="approved",
    ).exists()

    if not is_participant and offer.event.organizer != request.user:
        return redirect("view_carpool_offers", hike_id=offer.event.id)

    existing_request = CarpoolRequest.objects.filter(
        carpool_offer=offer,
        rider=request.user,
    ).first()

    if existing_request is None:
        CarpoolRequest.objects.create(
            carpool_offer=offer,
            rider=request.user,
            status="pending",
        )

        Notification.objects.create(
            recipient=offer.driver,
            sender=request.user,
            hike=offer.event,
            notification_type="carpool_request",
            message=f"{request.user.username} requested to join your carpool for '{offer.event.title}'.",
        )

    return redirect("view_carpool_offers", hike_id=offer.event.id)
