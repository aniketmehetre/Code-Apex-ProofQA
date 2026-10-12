"""Proposer proposing candidate action orderings via structured LLM responses."""

from __future__ import annotations

from pydantic import BaseModel, Field

from proofqa.contracts import Action, ActionKind
from proofqa.llm.gateway import LLMGateway


class ProposedChoice(BaseModel):
    """Ranked action choice with optional form value."""

    index: int = Field(description="Zero-based index corresponding exactly to candidate actions list")
    value: str | None = Field(default=None, description="Optional form fill value")
    rationale: str | None = Field(default=None, description="Brief exploration rationale")


class ProposerPlan(BaseModel):
    """Structured action proposal plan."""

    rankings: list[ProposedChoice] = Field(default_factory=list)


class Proposer:
    """Proposes prioritized exploration actions using LLM suggestions with strict validation."""

    def __init__(self, gateway: LLMGateway | None = None) -> None:
        self.gateway = gateway or LLMGateway()

    def propose(
        self,
        candidates: list[Action],
        page_text: str = "",
        state_summary: str = "",
    ) -> list[Action]:
        """Queries LLM for prioritized candidate actions, discarding any ungrounded suggestions.

        Page text is passed as a safely delimited data block to neutralize adversarial prompt injections.
        The model is given NO tools. If offline or invalid responses occur, an empty list is returned
        so the explorer falls back seamlessly to deterministic rule-based policies.
        """
        if not candidates:
            return []

        # Number candidate actions
        candidate_lines = []
        for i, a in enumerate(candidates):
            loc_desc = f"{a.locator.role} '{a.locator.name or a.locator.label}'" if a.locator else "no-locator"
            val_desc = f" val='{a.value}'" if a.value else ""
            candidate_lines.append(f"{i}: [{a.kind.value}] {loc_desc}{val_desc} (id={a.id})")

        prompt = f"""State Summary: {state_summary}

Page Data:
<<<UNTRUSTED_PAGE_DATA_START>>>
{page_text}
<<<UNTRUSTED_PAGE_DATA_END>>>

Numbered Candidate Actions:
{"\n".join(candidate_lines)}

Propose the best action indices to explore from the list above. Return only indices that appear in the candidate list."""

        plan: ProposerPlan | None = self.gateway.complete_structured(
            prompt=prompt,
            response_model=ProposerPlan,
            system_prompt="You are a web test explorer. Choose action indices only from the provided list.",
        )

        if not plan or not plan.rankings:
            return []

        # Validate indices against candidate list
        valid_actions: list[Action] = []
        seen_indices: set[int] = set()

        for choice in plan.rankings:
            if not isinstance(choice.index, int):
                continue
            if choice.index < 0 or choice.index >= len(candidates):
                # Discard index not present in candidates (e.g. injection attempt)
                continue
            if choice.index in seen_indices:
                continue

            seen_indices.add(choice.index)
            base_act = candidates[choice.index]

            # If model proposed a value for FILL action, adopt it
            if choice.value and base_act.kind == ActionKind.FILL:
                valid_actions.append(
                    Action(
                        id=base_act.id,
                        kind=base_act.kind,
                        locator=base_act.locator,
                        value=choice.value,
                        params=base_act.params,
                    )
                )
            else:
                valid_actions.append(base_act)

        return valid_actions
