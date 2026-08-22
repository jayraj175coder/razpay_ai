"""Simulation Benchmark API Endpoint."""
from typing import Optional
from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from simulator.benchmark import RecoveryBenchmarkRunner

router = APIRouter()


class SimulationRequest(BaseModel):
    count: int = Field(default=100, ge=10, le=2000, description="Number of synthetic transactions to simulate (e.g. 100, 500, 1000)")
    seed: int = Field(default=42, ge=1, le=999999, description="Random seed for reproducible results")


@router.post("/run", status_code=status.HTTP_200_OK)
async def run_simulation(req: SimulationRequest):
    """
    Execute deterministic side-by-side recovery simulation (Baseline vs RecoverAI).
    """
    result = RecoveryBenchmarkRunner.run_benchmark(count=req.count, seed=req.seed)
    return result.to_dict()
