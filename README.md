# AnoRank

AnoRank started with a problem in the BIC community: people liked an idea, but one leader could still reject it. This site gives the community a vote. The idea with the most votes in an award round wins.

There is also an open idea board where people can share ideas anonymously and rate feasibility, impact, and originality.

Built with Django, SQLite, HTML, CSS, and a little JavaScript.

## What it does

- Submit and browse ideas without signing up.
- Search, filter by category, and sort ideas.
- Rate each idea from 1 to 5 on three criteria.
- Update a rating or save an idea for later.
- See the highest-rated ideas on the leaderboard.
- Join an award round with a private account and submit an entry.
- Cast one vote per account per round, and change it until voting closes.
- See public vote totals and the winning idea after the deadline.

The score is an average of the three criteria across all ratings. Saved ideas and ratings are linked to your browser session. Clearing cookies resets that connection, so this doesn't enforce one vote per person.

Award voting is separate: the highest vote count wins, and tied top entries share the result. No votes means no winner. Anyone can create an account and vote. Email ownership and BIC membership are not verified, so accounts aren't a guarantee of unique people. Entrant accounts and emails stay private so organisers can arrange the award.

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

Create award rounds in **Award rounds** in admin. Set the award, submission opening time, voting start, and voting deadline. Times are shown in Nepal time. Submissions close when voting starts. Dates and rules are locked in admin after the first entry, and award entries and ballots cannot be edited or deleted there. The site announces the result; organisers arrange the actual award.

## Where the data goes

Locally, ideas, ratings, accounts, award rounds, and ballots live in `db.sqlite3` in the project folder. Django sessions are in that database too. The browser only keeps a session cookie.

On the internet, Django saves the data to the database connected to the hosted server. GitHub stores code, not the live database. A normal deploy starts with a new database unless you deliberately transfer the existing records.

Use a persistent database with backups for a real vote. This project can use hosted PostgreSQL through `DATABASE_URL`, or SQLite on a persistent server disk through `SQLITE_PATH`. See [hosting notes](docs/hosting.md) for the settings.

Keep `.env`, `.venv`, and `db.sqlite3` out of Git. The default settings are for local development.
