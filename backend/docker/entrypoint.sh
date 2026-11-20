#!/bin/sh
# Volumes mount root-owned; fix the upload folder, then drop privileges.
set -e
mkdir -p "$STORAGE_DIR"
chown -R app:app "$STORAGE_DIR"
exec setpriv --reuid=app --regid=app --init-groups "$@"
