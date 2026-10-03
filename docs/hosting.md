# Hosting and data

The website has two parts: the Django server and its database. Visitors use the site in a browser, but their submissions and votes are saved by Django in the database.

On your computer, that database is `db.sqlite3`. It holds ideas, ratings, accounts, sessions, award rounds, and ballots. Account passwords are stored as Django password hashes, not plain text. Cookies let Django recognise the signed-in account or browser session.

Putting the code on GitHub does not publish the Django server or move the database. A static host such as GitHub Pages cannot run this backend.

## An online database

For a community vote, use a persistent PostgreSQL database and turn on backups. Django supports PostgreSQL, and SQLite has limitations when several users write at once: https://docs.djangoproject.com/en/5.2/ref/databases/

The hosting service gives you a database connection URL. Save it as `DATABASE_URL` in the server's environment settings, keeping it out of Git. Install the PostgreSQL driver with:

```powershell
python -m pip install -r requirements-postgres.txt
```

Set these on the server:

```text
DJANGO_SECRET_KEY=<a new private key for the hosted site>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=<your website's hostname>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<your website's hostname>
DATABASE_URL=<the private PostgreSQL connection URL>
```

Then run `python manage.py migrate` on the server to create the tables. That creates the structure; it does not copy local ideas or votes. If you want to transfer local records, plan and verify a separate data export and import, excluding local sessions.

The site must also have a production application server, HTTPS, static-file serving, and the hosting provider's proxy configuration. Those steps depend on the host. The PostgreSQL connection defaults to TLS (`sslmode=require`); follow the provider's certificate guidance if it requires `verify-full`.

PostgreSQL connections are supported in settings, but a hosted database has not been created or connected yet.

## Keeping SQLite online

If you keep SQLite, its file must live on a persistent disk. Set `SQLITE_PATH` to that file's absolute path. An ordinary temporary deployment folder can be replaced when the server restarts or a new version is released. Don't use separate SQLite files behind multiple app servers; they would hold different records.

## Keeping a vote trustworthy

The app counts one ballot per account per round and refuses changes outside the voting window. Vote totals and tie rules are public. Ordinary Django admin screens cannot edit ballots, remove award entries, or change a round's rules after its first entry.

People with direct database access still control the underlying records. Keep that access limited, keep backups, and use an agreed process for any moderation or corrections. Open sign-up does not verify a unique person; multiple accounts are still possible. Add membership verification before relying on the result for an award where that matters.

The site displays the winning entry after the deadline. It does not make a payment or deliver a physical award.
