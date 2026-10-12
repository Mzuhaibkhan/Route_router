#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "============================================="
echo "==> Phase 5: Building React 19 Frontend SPA"
echo "============================================="
npm --prefix frontend install
npm --prefix frontend run build

echo "============================================="
echo "==> Phase 5: Installing Python Backend"
echo "============================================="
pip install -r backend/requirements.txt

echo "============================================="
echo "==> Phase 5: Collecting WhiteNoise Static Assets"
echo "============================================="
python backend/manage.py collectstatic --noinput

echo "==> Build Completed Successfully!"
