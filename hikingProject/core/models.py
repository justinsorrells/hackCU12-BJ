from django.contrib.auth.models import AbstractUser
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


