# PeakPals (HackCU12)

TrailCircle is a Django web app for organizing hikes, connecting with friends, managing join requests, and coordinating carpools.

## Features

- Custom user profiles with hiking preferences (experience level, pace, location, profile image)
- Hike creation and editing with date, time, mileage, elevation, visibility, and optional GPX upload
- Join-request workflow (pending, approved, rejected) for hike participation
- Social features: friend requests, accept/decline, remove, and profile views
- Hike discussion thread for approved participants and organizers
- Notifications for social and hike events
- Carpool offers and rider request approval/rejection flow
- Password change and account management pages
- User reporting flow that sends an email to moderators
- QR code generation on hike detail pages for easy sharing

## Tech Stack

- Python 3.12
- Django 4.2
- SQLite (default local database)
- Pillow + qrcode for image/QR functionality

## Repository Layout

- `requirements.txt` - Python dependencies
- `hikingProject/manage.py` - Django management entrypoint
- `hikingProject/hikingProject/` - Project settings and root URL config
- `hikingProject/core/` - Main app (models, views, forms, templates, static assets)
- `hikingProject/media/` - Uploaded media (profiles, GPX files)

## Quick Start

Run commands from the repository root unless noted.

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Create `hikingProject/.env` with email credentials (used by report notifications).

```env
EMAIL_HOST_USER="your-email@example.com"
EMAIL_HOST_PASSWORD="your-app-password"
```

4. Run database migrations.

```powershell
cd hikingProject
python manage.py makemigrations
python manage.py makemigrations core
python manage.py migrate
```

5. (Optional) Seed demo data.

```powershell
python manage.py seed
```

6. Start the dev server.

```powershell
python manage.py runserver 0.0.0.0:8000
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Makefile Shortcuts

From `hikingProject/`:

- `make clean` - removes `core/migrations` and `db.sqlite3`
- `make migrate` - runs migrations
- `make seed` - seeds sample users and hikes
- `make run` - starts the dev server
- `make all` - clean + migrate + seed + run

## Seed Data Notes

The seed command creates:

- 10 users named `user0` ... `user9`
- 20 sample hikes
- Password for seeded users: `password`

## Important Notes

- Current settings are development-oriented (`DEBUG=True`, `ALLOWED_HOSTS=["*"]`).
- Do not commit real email credentials in `.env`.
- Uploaded files are stored locally under `hikingProject/media/`.
