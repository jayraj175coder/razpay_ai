"""API v1 router registry."""
from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.cases import router as cases_router
from app.api.v1.ledger import router as ledger_router
from app.api.v1.simulation import router as simulation_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(cases_router, prefix="/cases", tags=["Cases"])
api_router.include_router(ledger_router, prefix="/ledger", tags=["Ledger"])
api_router.include_router(simulation_router, prefix="/simulation", tags=["Simulation"])
