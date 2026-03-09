from fastapi import FastAPI
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from db import client
from routes.auth import router as auth_router
from routes.keys import router as keys_router
from routes.chat import router as chat_router
from routes.export import router as export_router
from routes.agent_zero import router as a0_router
from routes.edcm import router as edcm_router
from routes.payments import router as payments_router
from routes.console import router as console_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI()

app.include_router(auth_router)
app.include_router(keys_router)
app.include_router(chat_router)
app.include_router(export_router)
app.include_router(a0_router)
app.include_router(edcm_router)
app.include_router(payments_router)
app.include_router(console_router)

cors_origins_raw = os.environ.get('CORS_ORIGINS')
if not cors_origins_raw:
    raise RuntimeError('CORS_ORIGINS is required')

cors_origins = [origin.strip() for origin in cors_origins_raw.split(',') if origin.strip()]
allow_all_origins = '*' in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[] if allow_all_origins else cors_origins,
    allow_origin_regex=r'https?://.*' if allow_all_origins else None,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/")
async def root():
    return {"message": "Multi-AI Chat API"}


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
