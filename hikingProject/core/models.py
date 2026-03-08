from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models

class User(AbstractUser):
    GENDER = [
        ("F", "Female"),
        ("M", "Male"),
        ("N", "Non-binary"),
    ]
    EXPERIENCE_LEVEL = [
        ("B", "Beginner"),
        ("I", "Intermediate"),
        ("A", "Advanced"),
    ]
    PACE = [
        ("S", "Slow"), 
        ("M", "Moderate"),
        ("F", "Fast"),
    ]
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)    
    gender = models.CharField(max_length=1, choices=GENDER)
    experience_level = models.CharField(max_length=1, choices=EXPERIENCE_LEVEL)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    pace = models.CharField(max_length=1, choices=PACE)
    age = models.IntegerField(null=True, blank=True)

class Friendship(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("blocked", "Blocked"),
    ]

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_friendships"
    )
    addressee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friendships"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~models.Q(requester=models.F("addressee")),
                name="prevent_self_friendship",
            ),
            models.UniqueConstraint(
                fields=["requester", "addressee"],
                name="unique_friend_request",
            ),
        ]

class HikingEvent(models.Model):

    EXPERIENCE_LEVELS = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    PACES = [
        ("slow", "Slow"),
        ("moderate", "Moderate"),
        ("fast", "Fast"),
    ]

    VISIBILITY = [
        ("public", "Public"),
        ("friends", "Friends Only"),
    ]

    title = models.CharField(max_length=200)

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_hikes"
    )

    location = models.CharField(max_length=255)
    gpx_file = models.FileField(upload_to="gpx/", blank=True, null=True)

    date = models.DateField()
    time = models.TimeField()

    pace = models.CharField(max_length=20, choices=PACES)

    recommended_experience = models.CharField(
        max_length=20,
        choices=EXPERIENCE_LEVELS
    )

    mileage = models.FloatField()

    elevation_gain = models.IntegerField()

    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY,
        default="public"
    )

    description = models.TextField(blank=True)

    max_participants = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

class EventJoinRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    event = models.ForeignKey(
        "HikingEvent",
        on_delete=models.CASCADE,
        related_name="join_requests"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_join_requests"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "user"],
                name="unique_event_join_request"
            )
        ]

    def __str__(self):
        return f"{self.user} -> {self.event} ({self.status})"

class HikeMessage(models.Model):
    event = models.ForeignKey(
        "HikingEvent",
        on_delete=models.CASCADE,
        related_name="messages"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hike_messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("friend_request", "Friend Request"),
        ("friend_accepted", "Friend Accepted"),
        ("hike_join_request", "Hike Join Request"),
        ("hike_join_approved", "Hike Join Approved"),
        ("hike_join_rejected", "Hike Join Rejected"),
        ("hike_message", "Hike Message"),
        ("participant_removed", "Participant Removed"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )

    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)

    message = models.CharField(max_length=255)

    is_read = models.BooleanField(default=False)

    hike = models.ForeignKey(
        "HikingEvent",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
class CarpoolOffer(models.Model):
    event = models.ForeignKey(
        HikingEvent,
        on_delete=models.CASCADE,
        related_name="carpool_offers"
    )

    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driving_offers"
    )

    contact_info = models.CharField(max_length=255)

    capacity = models.PositiveIntegerField()

    departure_location = models.CharField(max_length=255, blank=True)
    departure_time = models.TimeField(blank=True, null=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "driver"],
                name="unique_carpool_offer_per_event_driver"
            )
        ]

    def __str__(self):
        return f"{self.driver} driving for {self.event}"

    @property
    def approved_rider_count(self):
        return self.ride_requests.filter(status="approved").count()

    @property
    def seats_remaining(self):
        return self.capacity - self.approved_rider_count


class CarpoolRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    carpool_offer = models.ForeignKey(
        CarpoolOffer,
        on_delete=models.CASCADE,
        related_name="ride_requests"
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carpool_requests"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["carpool_offer", "rider"],
                name="unique_carpool_request_per_offer_rider"
            ),
        ]

    def __str__(self):
        return f"{self.rider} -> {self.carpool_offer} ({self.status})"
