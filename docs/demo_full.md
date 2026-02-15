# Full Demo Script (M1-M7)

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `alembic upgrade head`
4. `python scripts/seed.py`
5. `python scripts/demo_full.py`
6. `uvicorn app.main:app --reload`
7. Login at [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)

Quick route tour:

- Dashboard: `/`
- CRM: `/crm`
- Workflows + Jobs + logs: `/workflows`
- Brainstorm: `/brainstorm`
- Connectors: `/connectors`
- Mobile companion: `/m`
