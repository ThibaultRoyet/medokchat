from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import base64
import html as _html
import uuid

import gradio as gr
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from orchestrator.agent import root_agent

APP_NAME = "medokchat"
USER_ID = "user"

# ---------------------------------------------------------------------------
# Avatars — cercles SVG avec emoji encodés en data URI
# ---------------------------------------------------------------------------

def _svg_avatar(emoji: str, bg: str) -> str:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
        f'<circle cx="24" cy="24" r="24" fill="{bg}"/>'
        f'<text x="24" y="32" text-anchor="middle" font-size="24" '
        f'font-family="Apple Color Emoji,Segoe UI Emoji,Noto Color Emoji,sans-serif">{emoji}</text>'
        f'</svg>'
    )
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"

AVATAR_USER      = _svg_avatar("🧑‍⚕️", "#E8F5E9")
AVATAR_ASSISTANT = _svg_avatar("💊",   "#EDE7F6")

# Nom et emoji affichés dans le titre de chaque bulle d'agent
AGENT_DISPLAY = {
    "orchestrator":      ("🩺", "Assistant"),
    "med_finder":        ("🔍", "Recherche ANSM"),
    "med_documentation": ("📋", "Fiche officielle"),
}

# ---------------------------------------------------------------------------
# ADK runner
# ---------------------------------------------------------------------------

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


async def _ensure_session(session_id: str) -> None:
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    if session is None:
        await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )


async def _get_state(session_id: str) -> dict:
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    return session.state if session else {}


# ---------------------------------------------------------------------------
# Handler principal
# ---------------------------------------------------------------------------

async def respond(message: str, history: list, session_id: str):
    await _ensure_session(session_id)

    content = types.Content(role="user", parts=[types.Part(text=message)])

    new_history = history + [{"role": "user", "content": message}]
    agent_text: dict[str, str] = {}   # texte accumulé par auteur (run courant)
    agent_idx: dict[str, int] = {}    # index dans new_history par auteur (run courant)
    agent_done: set[str] = set()      # auteurs dont le run courant est terminé

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if not event.content or not event.content.parts:
            continue

        chunk = "".join(
            part.text for part in event.content.parts if getattr(part, "text", None)
        )
        if not chunk:
            continue

        author = event.author
        is_partial = event.partial is True

        # Si cet auteur avait déjà terminé un run, on repart sur une nouvelle bulle
        if author in agent_done:
            agent_done.discard(author)
            agent_idx.pop(author, None)
            agent_text.pop(author, None)

        if is_partial:
            agent_text[author] = agent_text.get(author, "") + chunk
        else:
            agent_text[author] = chunk
            agent_done.add(author)

        text = agent_text[author]
        emoji, label = AGENT_DISPLAY.get(author, ("🤖", author))
        title = f"{emoji} {label}"
        metadata = {"title": title, "status": "pending"} if is_partial else {"title": title}

        if author not in agent_idx:
            new_history.append({
                "role": "assistant",
                "content": text,
                "metadata": metadata,
            })
            agent_idx[author] = len(new_history) - 1
        else:
            idx = agent_idx[author]
            new_history[idx] = {
                "role": "assistant",
                "content": text,
                "metadata": metadata,
            }

        yield new_history, gr.update()

    state = await _get_state(session_id)
    doc_html = state.get("current_med_documentation", "")

    if doc_html:
        doc_html = doc_html.replace(
            "<head",
            '<head><base href="https://base-donnees-publique.medicaments.gouv.fr/">',
            1,
        )
        srcdoc = _html.escape(doc_html, quote=True)
        doc_output = (
            f'<iframe srcdoc="{srcdoc}" '
            f'style="width:100%;height:680px;border:none;" '
            f'sandbox="allow-same-origin allow-scripts allow-popups allow-forms"></iframe>'
        )
    else:
        doc_output = "<p style='color:#888;text-align:center;margin-top:4rem'>Ask about a medication to see its official documentation.</p>"

    yield new_history, doc_output


def new_session() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

with gr.Blocks(title="medokchat", fill_height=True) as demo:
    session_id = gr.State(new_session)

    gr.Markdown("# medokchat\nAssistant médical — informations sur les médicaments")

    with gr.Row(equal_height=True):

        with gr.Column(scale=1):
            chatbot = gr.Chatbot(
                label="Assistant Médical",
                height=700,
                layout="bubble",
                avatar_images=(AVATAR_USER, AVATAR_ASSISTANT),
                placeholder="Pose une question sur un médicament…",
            )
            txt = gr.Textbox(
                placeholder="Ex : Quelle est la posologie du Doliprane adulte ?",
                show_label=False,
                submit_btn=True,
            )

        with gr.Column(scale=1):
            doc_panel = gr.HTML(
                value="<p style='color:#888;text-align:center;margin-top:4rem'>Ask about a medication to see its official documentation.</p>",
                label="Documentation officielle (ANSM)",
            )

    txt.submit(
        fn=respond,
        inputs=[txt, chatbot, session_id],
        outputs=[chatbot, doc_panel],
        show_progress="hidden",
    ).then(fn=lambda: "", outputs=txt)


if __name__ == "__main__":
    import os
    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
    )
