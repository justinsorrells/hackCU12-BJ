from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models

# Create your models here.
class User(AbstractUser):
    GENDER = [
        ("F", "Female"),
        ("M", "Male"),
        ("N", "Non-binary"),
    ]
    EXPERIENCE_LEVEL = [
        ("B", "Beginner"),
        ("I", "Intermediate"),
        ("E", "Experienced"),
    ]
    PACE = [
        ("S", "Slow"), 
        ("A", "Average"),
        ("F", "Fast"),
    ]
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)    
    gender = models.CharField(max_length=1, choices=GENDER)
    experience_level = models.CharField(max_length=1, choices=EXPERIENCE_LEVEL)
    profile_picute = models.ImageField(upload_to="profiles/", blank=True, null=True)
    pace = models.CharField(max_length=1, choices=PACE)

class Friendship(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
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
