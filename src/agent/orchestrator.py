"""Agent orchestration boundary.

Bedrock is optional for deterministic demo execution. The same tool contract is
used in both modes, so model availability cannot bypass approval/evidence gates.
"""

from __future__ import annotations

from contextlib import nullcontext
from typing import Any

from .runtime import load_bedrock_config
from .tools import AgentToolbox


class MoneyFinderAgent:
    def __init__(self, tools: AgentToolbox | None = None):
        self.tools = tools or AgentToolbox()
        self.config = load_bedrock_config()
        self.tracer = self._tracer()

    @staticmethod
    def _tracer():
        try:
            from src.observability.arize import get_tracer, init_arize

            init_arize()
            return get_tracer("moneyfinder-agent")
        except Exception:
            return None

    def _span(self, name: str):
        return self.tracer.start_as_current_span(name) if self.tracer else nullcontext()

    def build_and_search(self, profile: dict[str, Any]) -> list[dict[str, Any]]:
        with self._span("moneyfinder.search") as span:
            valid = self.tools.build_search_profile(profile)
            hits = self.tools.search_unclaimed(valid)
            if span:
                span.set_attribute("moneyfinder.search.source", hits[0]["source"] if hits else "none")
                span.set_attribute("moneyfinder.search.hit_count", len(hits))
                span.set_attribute("moneyfinder.agent.model_id", self.config.model_id)
            return hits

    def prepare(self, profile: dict[str, Any], hit: dict[str, Any]) -> dict[str, Any]:
        with self._span("moneyfinder.form_prepare") as span:
            form = self.tools.prepare_claim_form(profile, hit)
            if span:
                span.set_attribute("moneyfinder.form.validation_errors", len(form["validation_errors"]))
            return form

    def explain_mode(self) -> dict[str, str]:
        return {
            "model_id": self.config.model_id,
            "mode": "deterministic_tools_with_optional_bedrock",
            "rule": "Bedrock may select tools; it may not bypass approval or evidence gates.",
        }
