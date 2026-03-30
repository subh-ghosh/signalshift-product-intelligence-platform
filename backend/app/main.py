from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router, set_ml_service
from app.services.ml_service import MLService


app = FastAPI(
    title="SignalShift API",
    description="AI-powered product feedback intelligence system",
    version="1.0"
)


# load ML service
ml_service = MLService()

# inject into routes
set_ml_service(ml_service)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)