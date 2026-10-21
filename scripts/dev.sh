#!/usr/bin/env bash
# راه‌اندازی کامل محیط توسعه فرایارا (لینوکس/مک)
set -e
cd "$(dirname "$0")/.."

echo "==> راه‌اندازی بک‌اند"
cd backend
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000 &
BACK_PID=$!
cd ..

echo "==> راه‌اندازی فرانت‌اند"
cd frontend
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev &
FRONT_PID=$!
cd ..

echo "بک‌اند: http://localhost:8000 (PID $BACK_PID)"
echo "فرانت‌اند: http://localhost:5173 (PID $FRONT_PID)"
echo "برای توقف: kill $BACK_PID $FRONT_PID"
wait
