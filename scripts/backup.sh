#!/usr/bin/env bash
# scatterbooks backup script
# Safely backs up the SQLite database and image uploads, then uploads to
# a Backblaze B2 bucket via rclone.
#
# Usage:
#   ./scripts/backup.sh [--env /path/to/backup.env]
#
# Set up:
#   1. cp scripts/backup.env.example scripts/backup.env
#   2. Fill in your B2 credentials in scripts/backup.env
#   3. Run once manually to confirm it works
#   4. Add to cron: 0 3 * * * /path/to/scatterbooks/scripts/backup.sh --env /path/to/scatterbooks/scripts/backup.env
#
# Requirements: docker, rclone (installed automatically if missing), sqlite3

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
ENV_FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env) ENV_FILE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# Load env file if provided
if [[ -n "$ENV_FILE" ]]; then
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: env file not found: $ENV_FILE" >&2
    exit 1
  fi
  # shellcheck source=/dev/null
  source "$ENV_FILE"
fi

# ---------------------------------------------------------------------------
# Configuration (all overridable via env file or environment)
# ---------------------------------------------------------------------------
CONTAINER_NAME="${CONTAINER_NAME:-scatterbooks-scatterbooks-1}"
LOCAL_BACKUP_DIR="${LOCAL_BACKUP_DIR:-/var/backups/scatterbooks}"
KEEP_LOCAL_DAYS="${KEEP_LOCAL_DAYS:-7}"

# B2 credentials — must be set in env file or environment
: "${B2_KEY_ID:?B2_KEY_ID is required}"
: "${B2_APPLICATION_KEY:?B2_APPLICATION_KEY is required}"
: "${B2_BUCKET:?B2_BUCKET is required}"
B2_PATH="${B2_PATH:-scatterbooks}"  # prefix within the bucket

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

require_rclone() {
  if ! command -v rclone &>/dev/null; then
    log "rclone not found -- installing via apt..."
    apt-get install -y -q rclone
  fi
}

require_sqlite3() {
  if ! command -v sqlite3 &>/dev/null; then
    log "sqlite3 not found -- installing via apt..."
    apt-get install -y -q sqlite3
  fi
}

cleanup() {
  if [[ -n "${WORK_DIR:-}" && -d "$WORK_DIR" ]]; then
    rm -rf "$WORK_DIR"
  fi
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
require_rclone
require_sqlite3

TIMESTAMP=$(date '+%Y-%m-%dT%H-%M-%S')
WORK_DIR=$(mktemp -d)
mkdir -p "$LOCAL_BACKUP_DIR"

log "Starting backup (timestamp: $TIMESTAMP)"

# --- Database ---------------------------------------------------------------
log "Backing up database..."
DB_BACKUP="scatterbooks-${TIMESTAMP}.db"

# sqlite3 .backup is safe under concurrent writes (uses the online backup API)
docker exec "$CONTAINER_NAME" \
  sqlite3 /data/scatterbooks.db ".backup /data/${DB_BACKUP}"

docker cp "${CONTAINER_NAME}:/data/${DB_BACKUP}" "${WORK_DIR}/${DB_BACKUP}"

# Remove the temp file from inside the container
docker exec "$CONTAINER_NAME" rm "/data/${DB_BACKUP}"

log "Database backup: ${WORK_DIR}/${DB_BACKUP} ($(du -sh "${WORK_DIR}/${DB_BACKUP}" | cut -f1))"

# --- Images -----------------------------------------------------------------
log "Backing up images..."
IMAGES_ARCHIVE="scatterbooks-images-${TIMESTAMP}.tar.gz"

# Tar the images directory directly from inside the container
docker exec "$CONTAINER_NAME" \
  tar -czf "/data/${IMAGES_ARCHIVE}" -C /data images/

docker cp "${CONTAINER_NAME}:/data/${IMAGES_ARCHIVE}" "${WORK_DIR}/${IMAGES_ARCHIVE}"
docker exec "$CONTAINER_NAME" rm "/data/${IMAGES_ARCHIVE}"

log "Images backup: ${WORK_DIR}/${IMAGES_ARCHIVE} ($(du -sh "${WORK_DIR}/${IMAGES_ARCHIVE}" | cut -f1))"

# --- Upload to B2 -----------------------------------------------------------
log "Uploading to B2 bucket: ${B2_BUCKET}/${B2_PATH}/"

# Pass credentials via environment variables so nothing hits the filesystem
RCLONE_CONFIG_B2_TYPE=b2 \
RCLONE_CONFIG_B2_ACCOUNT="$B2_KEY_ID" \
RCLONE_CONFIG_B2_KEY="$B2_APPLICATION_KEY" \
  rclone copy "$WORK_DIR/" "b2:${B2_BUCKET}/${B2_PATH}/" \
    --progress \
    --transfers 2

log "Upload complete"

# --- Copy to local archive (optional local retention) -----------------------
cp "${WORK_DIR}/${DB_BACKUP}" "$LOCAL_BACKUP_DIR/"
cp "${WORK_DIR}/${IMAGES_ARCHIVE}" "$LOCAL_BACKUP_DIR/"

# --- Prune old local backups ------------------------------------------------
if [[ "$KEEP_LOCAL_DAYS" -gt 0 ]]; then
  log "Pruning local backups older than ${KEEP_LOCAL_DAYS} days..."
  find "$LOCAL_BACKUP_DIR" -name "scatterbooks-*.db"      -mtime +"$KEEP_LOCAL_DAYS" -delete
  find "$LOCAL_BACKUP_DIR" -name "scatterbooks-images-*.tar.gz" -mtime +"$KEEP_LOCAL_DAYS" -delete
fi

log "Backup finished successfully"
log "  DB:     ${LOCAL_BACKUP_DIR}/${DB_BACKUP}"
log "  Images: ${LOCAL_BACKUP_DIR}/${IMAGES_ARCHIVE}"
log "  B2:     b2://${B2_BUCKET}/${B2_PATH}/"
