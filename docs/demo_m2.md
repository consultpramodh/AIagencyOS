# M2 Demo Script (3 minutes)

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `alembic upgrade head`
4. `python scripts/seed.py`
5. `python scripts/demo_m2.py`
6. `uvicorn app.main:app --reload`
7. Open [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
8. Login: `owner@demo.local` / `demo1234`

Manual checks:

- Create a note in Notes & Docs
- Edit the note and save changes
- Upload an attachment to that note
- Create a task due today and see it in Today Queue
- Move task across kanban lanes
