#!/usr/bin/env bash
# scatterbooks restore script
# Restores the database and/or images from a backup, either from a local
# file or by downloading from B2.
#
# Usage:
#   # Restore both DB and images from B2 for a given date:
#   ./scripts/restore.sh --env scripts/backup.env --timestamp 2026-06-29T03-00-00
#
#   # Restore only the database from a local file:
#   ./scripts/restore.sh --db /var/backups/scatterbooks/scatterbooks-2026-06-29T03-00-00.db
#
#   # Restore both from local files:
#   ./scripts/restore.sh \
#     --db /var/backups/scatterbooks/scatterbooks-2026-06-29T03-00-00.db \
#     --images /var/backups/scatterbooks/scatterbooks-images-2026-06-29T03-00-00.tar.gz
#
# The container is stopped during restore and restarted afterward.

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
ENV_FILE=""
TIMESTAMP=""
LOCAL_DB=""
LOCAL_IMAGES=""
SKIP_IMAGES=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)       ENV_FILE="$2";      shift 2 ;;
    --timestamp) TIMESTAMP="$2";     shift 2 ;;
    --db)        LOCAL_DB="$2";      shift 2 ;;
    --images)    LOCAL_IMAGES="$2";  shift 2 ;;
    --no-images) SKIP_IMAGES=true;   shift   ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# Load env file if provided
if [[ -n "$ENV_FILE" ]]; then
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: env file not found: $ENV_FILE" >&2; exit 1
  fi
  # shellcheck source=/dev/null
  source "$ENV_FILE"
fi

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONTAINER_NAME="${CONTAINER_NAME:-scatterbooks-scatterbooks-1}"
B2_PATH="${B2_PATH:-scatterbooks}"

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

cleanup() {
  if [[ -n "${WORK_DIR:-}" && -d "$WORK_DIR" ]]; then
    rm -rf "$WORK_DIR"
  fi
}
trap cleanup EXIT

rclone_b2() {
  RCLONE_CONFIG_B2_TYPE=b2 \
  RCLONE_CONFIG_B2_ACCOUNT="$B2_KEY_ID" \
  RCLONE_CONFIG_B2_KEY="$B2_APPLICATION_KEY" \
    rclone "$@"
}

# ---------------------------------------------------------------------------
# Resolve backup files
# ---------------------------------------------------------------------------
WORK_DIR=$(mktemp -d)

if [[ -n "$TIMESTAMP" ]]; then
  # Download from B2
  require_rclone
  : "${B2_KEY_ID:?B2_KEY_ID is required (set in --env file or environment)}"
  : "${B2_APPLICATION_KEY:?B2_APPLICATION_KEY is required}"
  : "${B2_BUCKET:?B2_BUCKET is required}"

  DB_FILENAME="scatterbooks-${TIMESTAMP}.db"
  IMAGES_FILENAME="scatterbooks-images-${TIMESTAMP}.tar.gz"

  log "Downloading database from B2..."
  rclone_b2 copy "b2:${B2_BUCKET}/${B2_PATH}/${DB_FILENAME}" "$WORK_DIR/"
  LOCAL_DB="${WORK_DIR}/${DB_FILENAME}"

  if [[ "$SKIP_IMAGES" == false ]]; then
    log "Downloading images from B2..."
    rclone_b2 copy "b2:${B2_BUCKET}/${B2_PATH}/${IMAGES_FILENAME}" "$WORK_DIR/"
    LOCAL_IMAGES="${WORK_DIR}/${IMAGES_FILENAME}"
  fi
fi

if [[ -z "$LOCAL_DB" ]]; then
  echo "ERROR: provide --timestamp (to pull from B2) or --db /path/to/backup.db" >&2
  exit 1
fi

if [[ ! -f "$LOCAL_DB" ]]; then
  echo "ERROR: database backup file not found: $LOCAL_DB" >&2; exit 1
fi

if [[ "$SKIP_IMAGES" == false && -n "$LOCAL_IMAGES" && ! -f "$LOCAL_IMAGES" ]]; then
  echo "ERROR: images backup file not found: $LOCAL_IMAGES" >&2; exit 1
fi

# ---------------------------------------------------------------------------
# Confirm before proceeding
# ---------------------------------------------------------------------------
echo ""
echo "  This will REPLACE the live database and (if specified) images."
echo "  The container will be stopped and restarted."
echo ""
echo "  Database:  $LOCAL_DB"
if [[ "$SKIP_IMAGES" == false && -n "$LOCAL_IMAGES" ]]; then
  echo "  Images:    $LOCAL_IMAGES"
else
  echo "  Images:    (skipped)"
fi
echo ""
read -r -p "  Type 'yes' to continue: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "Aborted."
  exit 0
fi

# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------
log "Stopping container..."
docker stop "$CONTAINER_NAME"

restore_failed() {
  log "ERROR: restore failed -- restarting container anyway"
  docker start "$CONTAINER_NAME"
  exit 1
}
trap restore_failed ERR

# Database
log "Restoring database..."
docker cp "$LOCAL_DB" "${CONTAINER_NAME}:/data/scatterbooks.db"
log "Database restored"

# Images
if [[ "$SKIP_IMAGES" == false && -n "$LOCAL_IMAGES" ]]; then
  log "Restoring images..."
  # Clear existing images, then extract the archive
  docker run --rm \
    --volumes-from "$CONTAINER_NAME" \
    python:3.12-slim \
    bash -c "rm -rf /data/images && tar -xzf /dev/stdin -C /data" \
    < "$LOCAL_IMAGES"
  log "Images restored"
fi

log "Restarting container..."
docker start "$CONTAINER_NAME"

# Reset the error trap now that we're past the risky part
trap cleanup EXIT

log "Restore complete"
