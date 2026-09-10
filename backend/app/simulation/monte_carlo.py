"""Monte Carlo probabilistic simulation engine with valid distributions, seeded runs, and bounded budgets."""

from __future__ import annotations

import math
import random

from pydantic import BaseModel

from app.simulation.safety import SimulationResourceBudgetExceededError


class DistributionParam(BaseModel):
    """Parameter definition for a probabilistic distribution."""

    distribution_type: str  # NORMAL, UNIFORM, BERNOULLI
    mean: float = 0.0
    std_dev: float = 1.0
    min_val: float = 0.0
    max_val: float = 1.0
    probability: float = 0.5


class MonteCarloResult(BaseModel):
    """Aggregated statistical outcome of a Monte Carlo simulation."""

    iterations_run: int
    seed: int
    metric_name: str
    mean: float
    std_dev: float
    p5: float
    p50: float
    p95: float
    distribution_used: str
    is_reproducible: bool = True
    disclaimer: str = "Monte Carlo percentiles represent probabilistic model estimates, not real-world guarantees."


class MonteCarloEngine:
    """Runs seeded, bounded Monte Carlo experiments using verified standard distributions."""

    MAX_ITERATIONS = 1000  # Hard compute limit (Prompt #163 & #164)

    def run_simulation(
        self,
        metric_name: str,
        base_value: float,
        distribution: DistributionParam,
        iterations: int = 100,
        seed: int = 42,
    ) -> MonteCarloResult:
        """Executes probabilistic sampling over iterations with explicit seed."""
        if iterations > self.MAX_ITERATIONS:
            raise SimulationResourceBudgetExceededError(
                f"Requested iterations ({iterations}) exceeds Monte Carlo safety ceiling ({self.MAX_ITERATIONS})."
            )

        rng = random.Random(seed)
        samples: list[float] = []

        dist_type = distribution.distribution_type.upper()
        for _ in range(iterations):
            if dist_type == "NORMAL":
                # Box-Muller / gauss
                val = rng.gauss(base_value + distribution.mean, max(0.001, distribution.std_dev))
            elif dist_type == "UNIFORM":
                val = base_value + rng.uniform(distribution.min_val, distribution.max_val)
            elif dist_type == "BERNOULLI":
                event = 1.0 if rng.random() < distribution.probability else 0.0
                val = base_value + (event * distribution.std_dev)
            else:
                raise ValueError(f"Unsupported distribution type '{dist_type}'. Must be NORMAL, UNIFORM, or BERNOULLI.")

            samples.append(round(val, 2))

        samples.sort()
        n = len(samples)
        mean_val = round(sum(samples) / n, 2)
        variance = sum((x - mean_val) ** 2 for x in samples) / max(1, n - 1)
        std_val = round(math.sqrt(variance), 2)

        p5_idx = int(0.05 * n)
        p50_idx = int(0.50 * n)
        p95_idx = min(n - 1, int(0.95 * n))

        return MonteCarloResult(
            iterations_run=n,
            seed=seed,
            metric_name=metric_name,
            mean=mean_val,
            std_dev=std_val,
            p5=samples[p5_idx],
            p50=samples[p50_idx],
            p95=samples[p95_idx],
            distribution_used=dist_type,
            is_reproducible=True,
        )
