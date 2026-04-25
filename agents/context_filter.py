"""Filtre de contexte pour les sous-agents.

Logique extraite de google.adk.plugins.context_filter_plugin.
Garde uniquement la dernière invocation dans llm_request.contents,
ce qui correspond à : message de délégation de l'orchestrateur + tool calls propres à l'agent.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from google.genai import types

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


def _is_function_response_content(content: types.Content) -> bool:
    return bool(content.parts) and any(
        part.function_response is not None for part in content.parts
    )


def _is_human_user_content(content: types.Content) -> bool:
    return content.role == "user" and not _is_function_response_content(content)


def _get_invocation_start_indices(contents: Sequence[types.Content]) -> list[int]:
    """Retourne les indices où commence chaque invocation utilisateur."""
    indices = []
    prev_was_human = False
    for i, content in enumerate(contents):
        is_human = _is_human_user_content(content)
        if is_human and not prev_was_human:
            indices.append(i)
        prev_was_human = is_human
    return indices


def _safe_split_index(contents: Sequence[types.Content], split_index: int) -> int:
    """Recule split_index pour ne pas orpheliner des function_responses."""
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


def keep_last_invocation(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """before_model_callback : ne garde que la dernière invocation.

    Le sous-agent ne voit que le message de délégation de l'orchestrateur
    et ses propres tool calls / réponses. Tout l'historique antérieur est élidé.
    """
    contents = llm_request.contents
    if not contents:
        return None

    starts = _get_invocation_start_indices(contents)
    if len(starts) <= 1:
        return None

    split = _safe_split_index(contents, starts[-1])
    llm_request.contents = contents[split:]
    return None
