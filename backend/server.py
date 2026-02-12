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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/")
async def root():
    return {"message": "Multi-AI Chat API"}


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
