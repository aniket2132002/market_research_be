from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import company

app = FastAPI(title="Researcher Bot")

# CORS settings
origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://your-frontend-domain.com",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(company.router, prefix="/api", tags=["Company Info"])
