from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import HikingEvent
from random import choice, randint
from datetime import date, time

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with sample users and hikes"

    def handle(self, *args, **kwargs):

        users = []

        # create users
        for i in range(10):
            user = User.objects.create_user(
                username=f"user{i}",
                password="password",
                name=f"User {i}",
                location="Boulder",
                gender=choice(["M", "F", "N"]),
                experience_level=choice(["B", "I", "A"]),
                pace=choice(["S", "M", "F"]),
            )
            users.append(user)

        # create hikes
        for i in range(20):
            HikingEvent.objects.create(
                title=f"Hike {i}",
                organizer=choice(users),
                location="Flatirons",
                date=date.today(),
                time=time(8, 0),
                pace=choice(["S", "M", "F"]),
                recommended_experience=choice(["B", "I", "A"]),
                mileage=randint(3, 12),
                elevation_gain=randint(500, 3000),
                visibility="P",
                description="Fun hike!",
                max_participants=randint(4, 12),
            )

        self.stdout.write(self.style.SUCCESS("Database seeded!"))