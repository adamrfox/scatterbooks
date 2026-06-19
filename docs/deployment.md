# Deployment

scatterbooks ships as a single Docker container: FastAPI serves both the
`/api/*` routes and the built React SPA (with a fallback to `index.html` for
client-side routes). There is no TLS inside the container — it always speaks
plain HTTP on port 8000, and is meant to sit behind an nginx reverse proxy
(hosted on a different machine/host than this container) that terminates
TLS.

## Build and run

```sh
docker build -t scatterbooks .

docker run -d --name scatterbooks \
  -e INITIAL_ADMIN_USERNAME=admin \
  -e INITIAL_ADMIN_PASSWORD=<choose-a-strong-password> \
  -v scatterbooks_data:/data \
  -p 8000:8000 \
  scatterbooks
```

Or with the included `docker-compose.yml`:

```sh
INITIAL_ADMIN_PASSWORD=<choose-a-strong-password> docker compose up -d --build
```

That inline `VAR=value` form only lasts for that one command — it doesn't
persist across reboots, server restarts, or the next time you happen to run
`docker compose up` from a fresh shell. To make environment variables stick
permanently, put them in a **`.env` file next to `docker-compose.yml`**
(copy `.env.example` to `.env` and fill it in). Docker Compose reads that
file automatically on every `docker compose` invocation — no need to
`export` anything or pass `-e` flags by hand:

```sh
cp .env.example .env
# edit .env: set INITIAL_ADMIN_PASSWORD, etc.
docker compose up -d --build
```

`.env` is git-ignored on purpose (it holds the admin password) — keep it on
the host only, not in version control. This is unrelated to the app's own
`pydantic-settings` `.env`-file support (which only matters if you run
`uvicorn` directly on bare metal from `backend/`); in the Docker/Compose
path, Compose's `.env` file is what actually injects these as container
environment variables.

If you're running `docker run` directly instead of Compose, the equivalent
is `--env-file path/to/.env`, or just keep using explicit `-e` flags in
whatever script/systemd unit launches the container.

On first startup (when the `users` table is empty), the app creates the
initial admin account from `INITIAL_ADMIN_USERNAME`/`INITIAL_ADMIN_PASSWORD`.
On every startup, it also runs any pending Alembic migrations automatically
— there's no separate migration step to remember. If those env vars aren't
set and no users exist yet, the app logs a warning and starts anyway (you'd
be locked out until you set them and restart).

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `INITIAL_ADMIN_USERNAME` | Only for first run | _(none)_ | Username for the bootstrap admin account |
| `INITIAL_ADMIN_PASSWORD` | Only for first run | _(none)_ | Password for the bootstrap admin account |
| `DATA_DIR` | No | `/data` | Base directory for the SQLite DB and uploaded images |
| `SESSION_TTL_DAYS` | No | `14` | Sliding session expiry window |
| `SESSION_MAX_TTL_DAYS` | No | `90` | Absolute cap on session lifetime regardless of activity |
| `MAX_UPLOAD_MB` | No | `15` | Per-image upload size limit |
| `GOOGLE_BOOKS_API_KEY` | No | _(none)_ | Enables Google Books as a fallback for the "scan ISBN" lookup (see below) |

Once the admin account exists, `INITIAL_ADMIN_USERNAME`/`PASSWORD` are
ignored on subsequent restarts (the bootstrap only fires when there are zero
users) — they don't need to be removed, but they also won't reset the
account's password if you change them later. Use the in-app "Reset password"
action (as admin) or the self-service password change instead.

### ISBN lookup (scan-to-fill)

When adding a book, librarians can scan its ISBN barcode (or type it in) to
auto-fill the title/author fields. This always tries **Open Library** first
— free, no API key, no signup. It optionally falls back to **Google Books**
if `GOOGLE_BOOKS_API_KEY` is set; without a key, Google Books is skipped
entirely rather than attempted, because unauthenticated requests to that API
share a heavily-throttled anonymous quota that is, in practice, often
already exhausted (you'd just get failures, not a useful fallback). A free
key takes a few minutes to generate from the Google Cloud Console (enable
the "Books API" on a project, create an API key) and raises that fallback's
quota substantially. Neither provider is required for the rest of the app
to work — if both miss (or Google Books is unconfigured), the librarian
just types the title/author manually, same as before this feature existed.

## Data persistence

Everything that needs to survive a restart lives under `/data`:

```
/data/
  scatterbooks.db        (+ -wal / -shm files)
  images/{book_id}/{image_id}_full.jpg
  images/{book_id}/{image_id}_thumb.jpg
```

Mount a single volume at `/data` (as in the examples above). To back up,
stop the container (or at least pause writes) and copy the volume's
contents elsewhere — it's a plain SQLite file plus a directory of JPEGs, no
special export step needed.

## nginx reverse proxy contract

The container only needs to be reachable from your nginx host, not directly
from the internet. nginx is the only thing this app trusts to set forwarded
headers (`uvicorn` is started with `--proxy-headers --forwarded-allow-ips=*`
since the upstream is implicitly trusted), so don't expose port 8000
publicly alongside nginx.

```nginx
server {
    listen 443 ssl;
    server_name books.example.com;

    # ... ssl_certificate / ssl_certificate_key / TLS config ...

    location / {
        proxy_pass http://<container-host>:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host  $host;

        # Photo uploads (up to 5 per book) can be several MB each:
        client_max_body_size 20m;

        # Helpful on slower mobile uplinks when uploading from a phone:
        proxy_read_timeout 60s;
    }
}
```

`X-Forwarded-Proto` matters concretely here: the session cookie is only
marked `Secure` when the app sees the request as HTTPS. Without that header
forwarded correctly, login would either set a cookie browsers refuse to
send back over your real HTTPS site, or never mark it `Secure` at all. This
has been verified end-to-end with a local nginx in front of the container —
`X-Forwarded-Proto: https` results in `Set-Cookie: ...; Secure`, and the
plain-HTTP path (e.g. local dev without a proxy) does not set `Secure`.

## Upgrading

Rebuild the image from the new source and recreate the container against
the same `/data` volume — migrations run automatically on startup, so
there's no manual DB upgrade step.

```sh
docker compose up -d --build
```
