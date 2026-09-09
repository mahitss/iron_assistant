"""Entity modeling, attribute representation, and domain extraction."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.knowledge_graph.schemas import NodeType, ScopeType


class EntityDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    canonical_name: str
    node_type: NodeType
    aliases: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    scope: ScopeType = ScopeType.PRIVATE
    confidence: float = 1.0
    provenance: Dict[str, Any] = Field(default_factory=dict)


class EntityExtractor:
    """Extracts candidate entities from text, documents, or event metadata."""

    @staticmethod
    def extract_from_text(text: str, project_hint: Optional[str] = None) -> List[EntityDefinition]:
        candidates: List[EntityDefinition] = []
        words = text.split()

        # Simple high-precision pattern recognition for repositories, files, services
        for word in words:
            # File references
            if ("." in word and any(word.endswith(ext) for ext in [".py", ".js", ".md", ".json", ".html", ".css", ".go", ".rs"])) and "/" not in word:
                candidates.append(
                    EntityDefinition(
                        canonical_name=word.strip(".,;:()"),
                        node_type=NodeType.FILE,
                        provenance={"source": "text_mention"},
                    )
                )
            # Service / repo references
            elif word.startswith("repo:") or word.startswith("service:"):
                prefix, name = word.split(":", 1)
                t = NodeType.REPOSITORY if prefix == "repo" else NodeType.SERVICE
                candidates.append(
                    EntityDefinition(
                        canonical_name=name.strip(".,;:()"),
                        node_type=t,
                        provenance={"source": "prefixed_identifier"},
                    )
                )

        return candidates
