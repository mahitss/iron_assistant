"""Event clustering and incident situation grouping (Task 60)."""

from __future__ import annotations

import logging

from app.situational_awareness.correlation import EventCorrelator, event_correlator
from app.situational_awareness.schemas import EventCluster, NormalizedEvent

logger = logging.getLogger(__name__)


class EventClusterer:
    """Groups correlated events into discrete incident clusters."""

    def __init__(self, correlator: EventCorrelator | None = None) -> None:
        self._correlator = correlator or event_correlator

    def cluster_events(
        self,
        events: list[NormalizedEvent],
        dependency_map: dict[str, list[str]] | None = None,
    ) -> list[EventCluster]:
        """Partition a list of normalized events into correlated clusters."""
        if not events:
            return []

        clusters: list[list[NormalizedEvent]] = []

        for event in events:
            placed = False
            for cluster_events in clusters:
                # Check if event correlates with any event in the existing cluster
                for member in cluster_events:
                    corr = self._correlator.correlate_events(event, member, dependency_map)
                    if corr["is_correlated"]:
                        cluster_events.append(event)
                        placed = True
                        break
                if placed:
                    break
            if not placed:
                clusters.append([event])

        # Convert to EventCluster objects
        result: list[EventCluster] = []
        for c_events in clusters:
            resources = list({e.resource for e in c_events if e.resource})
            env = c_events[0].environment
            avg_conf = sum(e.confidence for e in c_events) / len(c_events)
            cluster = EventCluster(
                events=c_events,
                resources=resources,
                environment=env,
                confidence=round(avg_conf, 3),
                rationale=f"Clustered {len(c_events)} events across resources {resources}",
            )
            result.append(cluster)

        logger.info("EVENTS_CLUSTERED: input=%d events -> output=%d clusters", len(events), len(result))
        return result


event_clusterer = EventClusterer()
