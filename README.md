# AnoRank

Share an idea without putting your name on it. People can rate it on feasibility, impact, and originality, and see how it compares on the leaderboard.

Built with Django, SQLite, HTML, CSS, and a little JavaScript.

## What it does

- Submit and browse ideas without signing up.
- Search, filter by category, and sort ideas.
- Rate each idea from 1 to 5 on three criteria.
- Update a rating or save an idea for later.
- See the highest-rated ideas on the leaderboard.

The score is an average of the three criteria across all ratings. Saved ideas and ratings are linked to your browser session. Clearing cookies resets that connection, so this doesn't enforce one vote per person.

## Run it locally

From the project folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If you don't have a `.env` file yet, copy `.env.example` to `.env` and replace the sample `DJANGO_SECRET_KEY`. Generate a key with:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Then run:

```powershell
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/. The board starts empty; the design preview uses example ideas only.

## Tests and admin

Run `python manage.py test ideas` to check the main flows.

For admin access, run `python manage.py createsuperuser` and visit `/admin/`. You can manage ideas and ratings there.

The current settings are for local development. Public hosting still needs production settings and spam controls. Keep `.env`, `.venv`, and `db.sqlite3` out of Git.
