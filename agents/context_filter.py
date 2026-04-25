"""Filtres de contexte pour les sous-agents.

Logique extraite de google.adk.plugins.context_filter_plugin.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Optional

from google.genai import types

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


# ---------------------------------------------------------------------------
# Helpers partagés
# ---------------------------------------------------------------------------

def _is_function_response_content(content: types.Content) -> bool:
    return bool(content.parts) and any(
        part.function_response is not None for part in content.parts
    )


def _is_human_user_content(content: types.Content) -> bool:
    return content.role == "user" and not _is_function_response_content(content)


def _get_invocation_start_indices(contents: Sequence[types.Content]) -> list[int]:
    indices = []
    prev_was_human = False
    for i, content in enumerate(contents):
        is_human = _is_human_user_content(content)
        if is_human and not prev_was_human:
            indices.append(i)
        prev_was_human = is_human
    return indices


def _safe_split_index(contents: Sequence[types.Content], split_index: int) -> int:
    needed_call_ids: set[str] = set()
    for i in range(len(contents) - 1, -1, -1):
        parts = contents[i].parts
        if parts:
            for part in reversed(parts):
                if part.function_response and part.function_response.id:
                    needed_call_ids.add(part.function_response.id)
                if part.function_call and part.function_call.id:
                    needed_call_ids.discard(part.function_call.id)
        if i <= split_index and not needed_call_ids:
            return i
    return 0


# ---------------------------------------------------------------------------
# keep_last_invocation
# ---------------------------------------------------------------------------

def keep_last_invocation(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """Garde uniquement la dernière invocation (message de délégation + tool calls propres)."""
    contents = llm_request.contents
    if not contents:
        return None

    starts = _get_invocation_start_indices(contents)
    if len(starts) <= 1:
        return None

    split = _safe_split_index(contents, starts[-1])
    llm_request.contents = contents[split:]
    return None


# ---------------------------------------------------------------------------
# keep_orchestrator_context
# ---------------------------------------------------------------------------

_AGENT_TAG_RE = re.compile(r'^\[(\w+)\]')


def _is_context_block(content: types.Content) -> bool:
    """Vrai si le contenu est un bloc 'For context:' injecté par ADK."""
    return bool(content.parts) and any(
        part.text is not None and part.text.strip() == "For context:"
        for part in content.parts
    )


def _filter_context_parts(parts: list[types.Part]) -> list[types.Part]:
    """Garde le header 'For context:' et les parts qui référencent [orchestrator] ou aucun agent."""
    kept = []
    for part in parts:
        if part.text is None:
            kept.append(part)
            continue
        text = part.text.strip()
        if text == "For context:":
            kept.append(part)
            continue
        m = _AGENT_TAG_RE.match(text)
        if m is None or m.group(1) == "orchestrator":
            kept.append(part)
    return kept


def keep_orchestrator_context(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """before_model_callback : filtre les blocs 'For context:' pour ne garder
    que les events de l'orchestrator et les vrais messages utilisateur.

    Les parts qui référencent d'autres sous-agents (ex. [med_finder]) sont supprimées.
    Un bloc 'For context:' qui n'a plus de contenu utile après filtrage est entièrement retiré.
    """
    if not callback_context.state.get("current_med"):
        callback_context.state["current_med"] = "Aucun médicament sélectionné pour cette session."

    contents = llm_request.contents
    if not contents:
        return None

    filtered: list[types.Content] = []
    for content in contents:
        if content.role != "user" or not _is_context_block(content):
            filtered.append(content)
            continue

        kept_parts = _filter_context_parts(list(content.parts))
        # Ne conserver le bloc que s'il reste des parts au-delà du header
        meaningful = [p for p in kept_parts if p.text and p.text.strip() != "For context:"]
        if meaningful:
            filtered.append(types.Content(role=content.role, parts=kept_parts))

    llm_request.contents = filtered
    return None
