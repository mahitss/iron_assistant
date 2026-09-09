"""Baseline metrics persistence and historical release retrieval."""

import json
import logging
from pathlib import Path
from app.evaluation.schemas import BaselineMetrics, MetricSummary

logger = logging.getLogger("kairo.evaluation.baseline")


class BaselineManager:
    """Manages frozen baseline metrics for comparison across releases."""

    def __init__(self, baselines_dir: str | Path = "evals/baselines") -> None:
        self.baselines_dir = Path(baselines_dir)
        self.baselines_dir.mkdir(parents=True, exist_ok=True)

    def save_baseline(self, baseline: BaselineMetrics) -> Path:
        """Save a release baseline to JSON."""
        file_path = self.baselines_dir / f"{baseline.version}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(baseline.model_dump_json(indent=2))
        logger.info("Saved baseline for %s to %s", baseline.version, file_path)
        return file_path

    def get_baseline(self, version: str) -> BaselineMetrics | None:
        """Load a specific version baseline."""
        file_path = self.baselines_dir / f"{version}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return BaselineMetrics.model_validate(data)
        except Exception as exc:
            logger.error("Failed to load baseline from %s: %s", file_path, exc)
            return None

    def list_baselines(self) -> list[str]:
        """List all available baseline version strings."""
        return [p.stem for p in self.baselines_dir.glob("*.json")]

    def get_latest_baseline(self) -> BaselineMetrics | None:
        """Retrieve the most recent release baseline."""
        versions = self.list_baselines()
        if not versions:
            return None
        # Sort by semver or filename
        versions.sort(reverse=True)
        return self.get_baseline(versions[0])
