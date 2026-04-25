# ─────────────────────────────────────────────────────────
# Stage 1 — builder : installation des dépendances Python
# ─────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

RUN python -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    UV_NO_CACHE=1

COPY pyproject.toml uv.lock ./
RUN uv pip install .


# ─────────────────────────────────────────────────────────
# Stage 2 — runtime : image finale
# ─────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

COPY --from=builder /opt/venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY . .

EXPOSE 7860

CMD ["python", "ui.py"]
