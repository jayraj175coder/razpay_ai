"""Unit and API tests for the Simulation and Benchmark Engine."""
import pytest
from httpx import AsyncClient

from simulator.generator import SyntheticTransactionGenerator
from simulator.benchmark import RecoveryBenchmarkRunner


def test_synthetic_generator_determinism():
    """Test that same seed generates identical batch of transactions."""
    batch1 = SyntheticTransactionGenerator.generate_batch(count=50, seed=42)
    batch2 = SyntheticTransactionGenerator.generate_batch(count=50, seed=42)

    assert len(batch1) == 50
    assert len(batch2) == 50
    assert batch1[0].id == batch2[0].id
    assert batch1[0].amount == batch2[0].amount
    assert batch1[0].failure_code == batch2[0].failure_code


def test_benchmark_runner_incremental_recovery():
    """Test that RecoverAI outperforms baseline on identical transaction batches."""
    res = RecoveryBenchmarkRunner.run_benchmark(count=100, seed=42)

    assert res.dataset_size == 100
    assert res.total_revenue_at_risk > 0
    assert res.recoverai_recovered_revenue > res.baseline_recovered_revenue
    assert res.incremental_recovered_revenue > 0
    assert res.recoverai_recovery_rate_pct > res.baseline_recovery_rate_pct
    assert res.policy_blocked_count > 0
    assert len(res.breakdown_by_category) > 0


@pytest.mark.asyncio
async def test_simulation_api_endpoint(client: AsyncClient):
    """Test POST /api/v1/simulation/run endpoint."""
    response = await client.post(
        "/api/v1/simulation/run",
        json={"count": 50, "seed": 101, "mandate_ratio": 0.4},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_size"] == 50
    assert data["seed"] == 101
    assert "incremental_recovered_revenue" in data
    assert "breakdown_by_category" in data


def test_synthetic_generator_mandate_ratio():
    """Test generating batch with explicit mandate_ratio."""
    batch = SyntheticTransactionGenerator.generate_batch(count=100, seed=42, mandate_ratio=0.5)
    mandate_txns = [t for t in batch if t.source_type == "MANDATE_FAILURE"]
    assert len(mandate_txns) > 20
    assert any(t.failure_code in ["npci_downtime", "bank_server_error", "low_balance_recurring"] for t in mandate_txns)
