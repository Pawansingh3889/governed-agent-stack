"""Chat endpoint with SSE streaming for LLM responses."""
from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.auth import get_current_user
from api.deps import clear_chat_history, get_chat_history, save_chat_message
from api.schemas import ChatMessage, ChatRequest, ChatResponse
from modules.doc_search import search as doc_search
from modules.llm import FACTORY_SYSTEM_PROMPT, get_response, get_streaming_response
from modules.sql_agent import run_query

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

SQL_KEYWORDS = frozenset({
    "how much", "how many", "show me", "total", "average", "count",
    "list", "top", "worst", "best", "compare", "trend", "waste",
    "yield", "production", "order", "customer", "staff", "temperature",
    "cost", "profit", "margin", "revenue", "kg", "today", "week", "month",
    "yesterday", "last", "this", "supplier", "batch", "salary", "hours",
})

DOC_KEYWORDS = frozenset({
    "procedure", "sop", "haccp", "brc", "policy", "handbook",
    "specification", "spec", "cleaning", "allergen procedure",
    "how to", "what is the process", "document", "guideline",
})


def _classify_question(question: str) -> str:
    """Classify a question as 'sql', 'doc', or 'chat'."""
    q = question.lower()
    is_sql = any(kw in q for kw in SQL_KEYWORDS)
    is_doc = any(kw in q for kw in DOC_KEYWORDS)
    if is_sql and not is_doc:
        return "sql"
    if is_doc:
        return "doc"
    return "chat"


def _df_to_records(df) -> list[dict]:
    """Convert a pandas DataFrame to a list of dicts for JSON serialisation."""
    if df is None:
        return []
    if hasattr(df, "to_dict"):
        return df.to_dict(orient="records")
    return []


# ---------------------------------------------------------------------------
# SSE streaming chat
# ---------------------------------------------------------------------------

async def _stream_chat(request: ChatRequest, session_id: str) -> AsyncGenerator[str, None]:
    """Generator that yields SSE events for a chat message."""
    q_type = _classify_question(request.message)

    if q_type == "sql":
        # SQL path: non-streaming (query + explanation)
        result = run_query(request.message)
        data = _df_to_records(result.get("data"))
        payload = {
            "type": "result",
            "explanation": result["explanation"],
            "sql": result.get("sql"),
            "data": data,
            "error": result.get("error", False),
        }
        yield f"data: {json.dumps(payload)}\n\n"
        save_chat_message(session_id, "user", request.message)
        save_chat_message(
            session_id, "assistant", result["explanation"],
            sql=result.get("sql"), data=data,
        )

    elif q_type == "doc":
        # Document search path
        results = doc_search(request.message, n_results=3)
        if results:
            context = "\n\n".join(
                f"[{r['metadata'].get('source', 'doc')}]: {r['text']}"
                for r in results
            )
            # Stream the LLM explanation
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            for chunk in get_streaming_response(
                f"Question: {request.message}\n\nRelevant documents:\n{context}\n\nAnswer:",
                system_prompt=FACTORY_SYSTEM_PROMPT,
            ):
                yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            save_chat_message(session_id, "user", request.message)
            save_chat_message(session_id, "assistant", "[doc search result]")
        else:
            payload = {
                "type": "result",
                "explanation": "No documents found. Please upload relevant documents first.",
                "error": False,
            }
            yield f"data: {json.dumps(payload)}\n\n"

    else:
        # General chat: streaming LLM response
        history_dicts = [{"role": m["role"], "content": m["content"]} for m in request.history[-6:]]
        yield f"data: {json.dumps({'type': 'start'})}\n\n"
        full_response = ""
        for chunk in get_streaming_response(
            request.message,
            system_prompt=FACTORY_SYSTEM_PROMPT,
            context=history_dicts,
        ):
            full_response += chunk
            yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        save_chat_message(session_id, "user", request.message)
        save_chat_message(session_id, "assistant", full_response)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("")
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    """Send a chat message. Returns SSE stream when stream=true, JSON otherwise."""
    session_id = request.history[0].content if request.history else str(uuid.uuid4())

    if not request.stream:
        # Non-streaming: run synchronously and return JSON
        q_type = _classify_question(request.message)
        if q_type == "sql":
            result = run_query(request.message)
            return ChatResponse(
                explanation=result["explanation"],
                sql=result.get("sql"),
                data=_df_to_records(result.get("data")),
                error=result.get("error", False),
            )
        answer = get_response(request.message, system_prompt=FACTORY_SYSTEM_PROMPT)
        return ChatResponse(explanation=answer)

    return StreamingResponse(
        _stream_chat(request, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/history")
async def chat_history(
    session_id: str = "default",
    user: dict = Depends(get_current_user),
) -> list[ChatMessage]:
    """Return chat history for a session."""
    messages = get_chat_history(session_id)
    return [
        ChatMessage(
            role=m["role"],
            content=m["content"],
            timestamp=m.get("timestamp"),
        )
        for m in messages
    ]


@router.delete("/history", status_code=204)
async def delete_chat_history(
    session_id: str = "default",
    user: dict = Depends(get_current_user),
) -> None:
    """Clear chat history for a session."""
    clear_chat_history(session_id)
