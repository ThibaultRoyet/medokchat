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

def _is_context_block(content: types.Content) -> bool:
    """Vrai si le contenu est un bloc 'For context:' injecté par ADK."""
    return bool(content.parts) and any(
        part.text is not None and part.text.strip() == "For context:"
        for part in content.parts
    )


_AGENT_TAG_RE = re.compile(r'^\[(\w+)\]')
_TOOL_RESULT_RE = re.compile(r'`\w+`\s+tool\s+returned\s+result')


def _filter_context_parts(parts: list[types.Part]) -> list[types.Part]:
    """Règles de filtrage dans les blocs 'For context:' :

    Supprimé :
    - function_call et function_response (tool calls internes + transfer_to_agent)
    - textes taggés sous-agent qui sont des tool results

    Gardé :
    - header 'For context:'
    - messages utilisateur (pas de tag)
    - textes [orchestrator]
    - réponses purement textuelles des sous-agents
    """
    kept = []
    for part in parts:
        if part.function_call is not None or part.function_response is not None:
            continue
        if part.text is None:
            kept.append(part)
            continue
        text = part.text.strip()
        if text == "For context:":
            kept.append(part)
            continue
        m = _AGENT_TAG_RE.match(text)
        if m is not None and m.group(1) != "orchestrator":
            # Texte d'un sous-agent : garder seulement si ce n'est pas un tool result
            if _TOOL_RESULT_RE.search(text):
                continue
        kept.append(part)
    return kept


def keep_orchestrator_context(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """before_model_callback : dans les blocs 'For context:', supprime les tool calls
    des sous-agents (y compris transfer_to_agent) et garde uniquement leurs réponses textuelles.

    Un bloc 'For context:' vide après filtrage est entièrement retiré.
    """
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
