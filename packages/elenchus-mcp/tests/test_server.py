"""Tests for elenchus-mcp server."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def mock_env(monkeypatch):
    monkeypatch.setenv("ELENCHUS_URL", "http://localhost:8000")
    monkeypatch.setenv("ELENCHUS_USER_ID", "test-user-001")


@pytest.fixture()
def mock_client():
    with patch("elenchus_mcp.server.httpx") as mock:
        client = MagicMock()
        mock.Client.return_value.__enter__.return_value = client
        yield client


class TestListSurveys:
    def test_returns_surveys(self, mock_env, mock_client):
        mock_client.get.return_value.json.return_value = [
            {"id": "t1", "title": "Safety", "status": "published", "run_count": 5}
        ]
        mock_client.get.return_value.raise_for_status = MagicMock()

        from elenchus_mcp.server import list_surveys

        result = list_surveys()

        assert result["count"] == 1
        assert result["surveys"][0]["id"] == "t1"


class TestCreateSurvey:
    def test_creates_template(self, mock_env, mock_client):
        mock_client.post.return_value.json.return_value = {
            "id": "t2",
            "title": "Test",
            "status": "draft",
            "questions": [{"text": "Q1"}],
        }
        mock_client.post.return_value.raise_for_status = MagicMock()

        from elenchus_mcp.server import create_survey

        result = create_survey(
            title="Test",
            questions=[{"text": "Q1", "kind": "text"}],
        )

        assert result["id"] == "t2"
        assert result["question_count"] == 1


class TestPublishSurvey:
    def test_publishes(self, mock_env, mock_client):
        mock_client.post.return_value.json.return_value = {
            "id": "t1",
            "title": "Safety",
            "status": "published",
            "published_at": "2026-08-19T12:00:00",
        }
        mock_client.post.return_value.raise_for_status = MagicMock()

        from elenchus_mcp.server import publish_survey

        result = publish_survey(survey_id="t1")

        assert result["status"] == "published"


class TestStartConversation:
    def test_starts_run(self, mock_env, mock_client):
        mock_client.post.return_value.json.return_value = {
            "id": "r1",
            "status": "in_progress",
            "current_question": "How are you?",
            "messages": [],
        }
        mock_client.post.return_value.raise_for_status = MagicMock()

        from elenchus_mcp.server import start_conversation

        result = start_conversation(survey_id="t1", respondent_id="u1")

        assert result["run_id"] == "r1"
        assert result["current_question"] == "How are you?"


class TestSendResponse:
    def test_sends_answer(self, mock_env, mock_client):
        mock_client.post.return_value.json.return_value = {
            "id": "r1",
            "status": "in_progress",
            "current_question": "Next?",
        }
        mock_client.post.return_value.raise_for_status = MagicMock()

        from elenchus_mcp.server import send_response

        result = send_response(run_id="r1", answer="Good")

        assert result["run_id"] == "r1"
        assert result["is_complete"] is False

    def test_completes_run(self, mock_env, mock_client):
        mock_client.post.return_value.json.return_value = {
            "id": "r1",
            "status": "completed",
            "current_question": None,
        }
        mock_client.post.return_value.raise_for_status = MagicMock()

        from elenchus_mcp.server import send_response

        result = send_response(run_id="r1", answer="Done")

        assert result["is_complete"] is True


class TestGetResults:
    def test_returns_report(self, mock_env, mock_client):
        mock_client.get.return_value.json.return_value = {
            "title": "Safety",
            "total_runs": 10,
            "completed_runs": 8,
            "questions": [{"text": "Q1", "answers": 8}],
        }
        mock_client.get.return_value.raise_for_status = MagicMock()

        from elenchus_mcp.server import get_results

        result = get_results(survey_id="t1")

        assert result["total_runs"] == 10
        assert result["completed_runs"] == 8
