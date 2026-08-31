"""Model Context Protocol server that exposes Elenchus survey tools to LLMs.

Tools:
* ``list_surveys`` returns published survey templates with run counts.
* ``create_survey`` creates a new survey template from a description.
* ``publish_survey`` opens a survey for responses.
* ``start_conversation`` begins a survey run with a respondent.
* ``send_response`` records a respondent's answer in an active run.
* ``get_results`` returns aggregated survey results.
* ``generate_survey`` uses LLM to draft a survey from natural language.

Designed for Claude Desktop, Cursor, ChatGPT desktop, Continue, and any other
MCP client. Communication happens over stdio so no network listener is opened.
"""

from __future__ import annotations

import os
from typing import Annotated

import httpx
from fastmcp import FastMCP
from pydantic import Field

ELENCHUS_URL = os.environ.get("ELENCHUS_URL", "http://localhost:8000")
ELENCHUS_USER_ID = os.environ.get("ELENCHUS_USER_ID", "")

mcp = FastMCP(
    name="elenchus",
    instructions=(
        "Manage and conduct surveys through the Elenchus service. "
        "Use list_surveys to see available surveys, create_survey to build new ones, "
        "publish_survey to open them for responses, start_conversation to begin a "
        "respondent's session, send_response to record answers, and get_results to "
        "view aggregated results."
    ),
)


def _headers() -> dict[str, str]:
    return {"X-User-Id": ELENCHUS_USER_ID}


@mcp.tool(
    description=(
        "List published survey templates with their run counts and status. "
        "Returns summaries suitable for selecting which survey to work with."
    )
)
def list_surveys() -> dict:
    with httpx.Client(base_url=ELENCHUS_URL, timeout=30) as client:
        resp = client.get("/api/v1/templates/published", headers=_headers())
        resp.raise_for_status()
        templates = resp.json()

    return {
        "count": len(templates),
        "surveys": [
            {
                "id": t["id"],
                "title": t["title"],
                "status": t["status"],
                "run_count": t.get("run_count", 0),
                "created_at": t.get("created_at"),
            }
            for t in templates
        ],
    }


@mcp.tool(
    description=(
        "Create a new survey template with questions. Returns the template ID "
        "for use with publish_survey. The template starts in draft status."
    )
)
def create_survey(
    title: Annotated[str, Field(description="The survey title")],
    questions: Annotated[
        list[dict],
        Field(
            description="List of question objects with 'text' and 'kind' (single_select, multi_select, text, numeric, boolean)"
        ),
    ],
    description: Annotated[str, Field(description="Survey description")] = "",
    audience: Annotated[
        str | None, Field(description="Target audience filter (e.g. 'production', 'hr')")
    ] = None,
) -> dict:
    payload = {
        "title": title,
        "description": description,
        "questions": questions,
    }
    if audience:
        payload["audience"] = audience

    with httpx.Client(base_url=ELENCHUS_URL, timeout=30) as client:
        resp = client.post(
            "/api/v1/templates", json=payload, headers=_headers()
        )
        resp.raise_for_status()
        template = resp.json()

    return {
        "id": template["id"],
        "title": template["title"],
        "status": template["status"],
        "question_count": len(template.get("questions", [])),
    }


@mcp.tool(
    description=(
        "Generate a survey template from a natural-language description. "
        "The LLM drafts questions based on the description. Returns the template ID."
    )
)
def generate_survey(
    description: Annotated[str, Field(description="Natural-language description of the survey to create")],
    title: Annotated[str | None, Field(description="Optional title; generated if omitted")] = None,
) -> dict:
    payload = {"description": description}
    if title:
        payload["title"] = title

    with httpx.Client(base_url=ELENCHUS_URL, timeout=30) as client:
        resp = client.post(
            "/api/v1/templates/generate", json=payload, headers=_headers()
        )
        resp.raise_for_status()
        result = resp.json()

    return {
        "id": result["id"],
        "title": result.get("title", ""),
        "description": result.get("description", ""),
        "questions": result.get("questions", []),
    }


@mcp.tool(
    description=(
        "Publish a draft survey, opening it for respondent conversations. "
        "Only draft surveys with at least one question can be published."
    )
)
def publish_survey(
    survey_id: Annotated[str, Field(description="The template/survey ID to publish")],
) -> dict:
    with httpx.Client(base_url=ELENCHUS_URL, timeout=30) as client:
        resp = client.post(
            f"/api/v1/templates/{survey_id}/publish", headers=_headers()
        )
        resp.raise_for_status()
        template = resp.json()

    return {
        "id": template["id"],
        "title": template["title"],
        "status": template["status"],
        "published_at": template.get("published_at"),
    }


@mcp.tool(
    description=(
        "Start a new survey conversation with a respondent. Returns a run_id "
        "for use with send_response. The first question is returned in the response."
    )
)
def start_conversation(
    survey_id: Annotated[str, Field(description="The published survey ID")],
    respondent_id: Annotated[str, Field(description="The respondent's user ID")],
) -> dict:
    with httpx.Client(base_url=ELENCHUS_URL, timeout=30) as client:
        resp = client.post(
            "/api/v1/conduct",
            json={"template_id": survey_id, "respondent_id": respondent_id},
            headers=_headers(),
        )
        resp.raise_for_status()
        run = resp.json()

    return {
        "run_id": run["id"],
        "status": run["status"],
        "current_question": run.get("current_question"),
        "message_count": len(run.get("messages", [])),
    }


@mcp.tool(
    description=(
        "Record a respondent's answer in an active survey run. "
        "Returns the next question or completion status."
    )
)
def send_response(
    run_id: Annotated[str, Field(description="The survey run ID")],
    answer: Annotated[str, Field(description="The respondent's answer text")],
) -> dict:
    with httpx.Client(base_url=ELENCHUS_URL, timeout=30) as client:
        resp = client.post(
            f"/api/v1/conduct/{run_id}/messages",
            json={"content": answer},
            headers=_headers(),
        )
        resp.raise_for_status()
        run = resp.json()

    return {
        "run_id": run["id"],
        "status": run["status"],
        "current_question": run.get("current_question"),
        "is_complete": run.get("status") == "completed",
    }


@mcp.tool(
    description=(
        "Get aggregated results for a survey. Returns counts, response rates, "
        "and answer distributions. Optionally filter by run status."
    )
)
def get_results(
    survey_id: Annotated[str, Field(description="The survey/template ID")],
) -> dict:
    with httpx.Client(base_url=ELENCHUS_URL, timeout=30) as client:
        resp = client.get(
            f"/api/v1/runs/{survey_id}/report", headers=_headers()
        )
        resp.raise_for_status()
        report = resp.json()

    return {
        "survey_id": survey_id,
        "title": report.get("title", ""),
        "total_runs": report.get("total_runs", 0),
        "completed_runs": report.get("completed_runs", 0),
        "questions": report.get("questions", []),
    }


@mcp.tool(
    description=(
        "Close a survey, preventing new conversations from starting. "
        "Existing runs can still be completed."
    )
)
def close_survey(
    survey_id: Annotated[str, Field(description="The survey ID to close")],
) -> dict:
    with httpx.Client(base_url=ELENCHUS_URL, timeout=30) as client:
        resp = client.post(
            f"/api/v1/templates/{survey_id}/close", headers=_headers()
        )
        resp.raise_for_status()
        template = resp.json()

    return {
        "id": template["id"],
        "status": template["status"],
        "closed_at": template.get("closed_at"),
    }


def main() -> None:
    """Console-script entry point. Runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
