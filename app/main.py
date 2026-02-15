from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import auth, brainstorm, connectors, crm, dashboard, jobs, marketing, mobile, reports, workflows

app = FastAPI(title="AI Marketing Agency OS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(crm.router)
app.include_router(workflows.router)
app.include_router(brainstorm.router)
app.include_router(connectors.router)
app.include_router(mobile.router)
app.include_router(jobs.router)
app.include_router(reports.router)
app.include_router(marketing.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
