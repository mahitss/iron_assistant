"""Intent Priority, Dependency Ordering, and Primary vs Secondary Extraction (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional
from app.intent.schemas import IntentType

logger = logging.getLogger("kairo.intent.priorities")


@dataclass
class IntentPriorityNode:
    """Individual parsed intent with execution ordering and dependency tags (Spec 6-8)."""

    intent_type: IntentType
    description: str
    is_primary: bool = False
    order_index: int = 0
    depends_on_indices: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type.value if hasattr(self.intent_type, "value") else str(self.intent_type),
            "description": self.description,
            "is_primary": self.is_primary,
            "order_index": self.order_index,
            "depends_on_indices": self.depends_on_indices,
        }


class IntentPrioritizer:
    """Orders multi-intent utterances into sequential dependency chains (Spec 5-8)."""

    # Typical execution pipeline order for multi-intent verbs:
    # 1. Inspect / Search / Analyze
    # 2. Repair / Create / Modify / Code
    # 3. Test / Deploy / Execute
    # 4. Notify / Communicate / Explain
    PIPELINE_WEIGHTS = {
        IntentType.SEARCH: 10,
        IntentType.RESEARCH: 12,
        IntentType.ANALYZE: 15,
        IntentType.QUESTION: 20,
        IntentType.DEBUG: 25,
        IntentType.TASK: 30,
        IntentType.CREATE: 40,
        IntentType.MODIFY: 45,
        IntentType.CODE: 50,
        IntentType.DEPLOY: 70,
        IntentType.NOTIFY: 90,
        IntentType.COMMUNICATE: 95,
    }

    @classmethod
    def prioritize_multi_intents(cls, intents: List[tuple[IntentType, str]]) -> List[IntentPriorityNode]:
        """Enforce Spec 5-8: Separate primary intent and order supporting secondary intents by dependency."""
        if not intents:
            return []

        sorted_intents = sorted(intents, key=lambda pair: cls.PIPELINE_WEIGHTS.get(pair[0], 50))

        nodes: List[IntentPriorityNode] = []
        for idx, (itype, desc) in enumerate(sorted_intents):
            is_prim = (idx == 0)
            nodes.append(
                IntentPriorityNode(
                    intent_type=itype,
                    description=desc,
                    is_primary=is_prim,
                    order_index=idx,
                    depends_on_indices=[i for i in range(idx)],
                )
            )

        return nodes

