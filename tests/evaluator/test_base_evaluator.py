"""
Tests for the shared evaluation harness

All tests run offline: query backends are fixtures/stubs, no LLM credentials
or vector store required.
"""

import json

import pytest

from apps.evaluator.base_evaluator import (
    BaseEvaluator,
    FixtureBackend,
    RecordingBackend,
)
from apps.evaluator.chatbot_evaluator import ChatbotEvaluator


# =============================================================================
# QUERY BACKENDS
# =============================================================================

def test_fixture_backend_replays_recorded_responses(tmp_path):
    fixture_file = tmp_path / "fixture.json"
    fixture_file.write_text(json.dumps({
        "What properties does Poolula LLC own?": {
            "response": "Poolula LLC owns 900 S 9th St.",
            "sources": [{"query_type": "properties", "text": "Database Query: properties"}],
        }
    }))

    backend = FixtureBackend(str(fixture_file))
    response, sources = backend("What properties does Poolula LLC own?")

    assert "900 S 9th St" in response
    assert sources[0]["query_type"] == "properties"


def test_fixture_backend_missing_question_raises(tmp_path):
    fixture_file = tmp_path / "fixture.json"
    fixture_file.write_text("{}")

    backend = FixtureBackend(str(fixture_file))
    with pytest.raises(KeyError):
        backend("Unrecorded question?")


def test_recording_backend_captures_and_saves(tmp_path):
    def live_backend(question):
        return f"Answer to: {question}", [{"query_type": "properties"}]

    recorder = RecordingBackend(live_backend)
    response, sources = recorder("Q1?")
    assert response == "Answer to: Q1?"

    fixture_path = tmp_path / "recorded.json"
    recorder.save(str(fixture_path))

    # Round-trip: recorded fixture replays identically
    replay = FixtureBackend(str(fixture_path))
    assert replay("Q1?") == ("Answer to: Q1?", [{"query_type": "properties"}])


# =============================================================================
# SHARED CHECKS
# =============================================================================

def test_extract_tools_used():
    sources = [
        {"query_type": "transactions", "text": "Database Query: transactions"},
        {"document_title": "Articles of Organization", "text": "Articles - Page 1"},
    ]
    tools = BaseEvaluator.extract_tools_used(sources)
    assert tools == ["query_database", "search_document_content"]


def test_check_tool_usage_reports_missing_tools():
    evaluator = ChatbotEvaluator(query_fn=lambda q: ("", []))
    check = evaluator.check_tool_usage(
        ["query_database"], [{"document_title": "Some Doc"}]
    )
    assert check["score"] == 0.0
    assert "query_database" in check["reason"]
    assert check["actual"] == ["search_document_content"]


def test_check_content_relevance_partial_match():
    check = BaseEvaluator.check_content_relevance(
        ["rental", "income", "unicorn"], "Rental income was $500."
    )
    assert check["score"] == pytest.approx(2 / 3)
    assert check["keywords_missing"] == ["unicorn"]
    assert "unicorn" in check["reason"]


def test_check_completeness():
    assert BaseEvaluator.check_completeness("")["score"] == 0.0
    assert BaseEvaluator.check_completeness("Error: something failed")["score"] == 0.3
    assert BaseEvaluator.check_completeness("short")["score"] == 0.5
    assert BaseEvaluator.check_completeness("A perfectly normal full answer.")["score"] == 1.0


# =============================================================================
# END-TO-END EVALUATION WITH FIXTURES
# =============================================================================

@pytest.fixture(name="eval_set_path")
def eval_set_fixture(tmp_path):
    eval_file = tmp_path / "eval.jsonl"
    items = [
        {
            "question": "What properties does Poolula LLC own?",
            "expected_tools": ["query_database"],
            "expected_content": ["900 S 9th St"],
        },
        {
            "question": "What is the business purpose?",
            "expected_tools": ["search_document_content"],
            "expected_content": ["rental", "property"],
            "gold_answer": "Operating a short-term rental property business.",
        },
    ]
    eval_file.write_text("\n".join(json.dumps(i) for i in items))
    return str(eval_file)


@pytest.fixture(name="fixture_backend")
def fixture_backend_fixture(tmp_path):
    fixture_file = tmp_path / "responses.json"
    fixture_file.write_text(json.dumps({
        # Good answer: right tool, right content
        "What properties does Poolula LLC own?": {
            "response": "Poolula LLC owns one property at 900 S 9th St, Montrose, CO.",
            "sources": [{"query_type": "properties", "text": "Database Query: properties"}],
        },
        # Bad answer: wrong tool, missing keywords
        "What is the business purpose?": {
            "response": "I could not determine that.",
            "sources": [{"query_type": "properties", "text": "Database Query: properties"}],
        },
    }))
    return FixtureBackend(str(fixture_file))


def test_run_evaluation_produces_diagnostic_report(eval_set_path, fixture_backend, capsys):
    evaluator = ChatbotEvaluator(query_fn=fixture_backend)
    report = evaluator.run_evaluation(eval_set_path)

    assert report["total_questions"] == 2
    assert report["passed"] == 1
    assert report["passed"] + report["warned"] + report["failed"] == 2

    # The failing question produced an actionable failure record
    assert len(report["failures"]) == 1
    failure = report["failures"][0]
    assert failure["question"] == "What is the business purpose?"
    assert failure["expected_tools"] == ["search_document_content"]
    assert failure["actual_tools"] == ["query_database"]
    assert failure["gold_answer"].startswith("Operating a short-term")
    assert any("search_document_content" in r for r in failure["reasons"])
    assert any("rental" in r for r in failure["reasons"])
    assert failure["sources"] == ["Database Query: properties"]


def test_run_evaluation_handles_backend_errors(eval_set_path):
    def broken_backend(question):
        raise RuntimeError("connection refused")

    evaluator = ChatbotEvaluator(query_fn=broken_backend)
    report = evaluator.run_evaluation(eval_set_path)

    assert report["failed"] == 2
    assert all("connection refused" in f["reasons"][0] for f in report["failures"])


def test_save_reports(eval_set_path, fixture_backend, tmp_path):
    evaluator = ChatbotEvaluator(query_fn=fixture_backend)
    report = evaluator.run_evaluation(eval_set_path)

    json_path = tmp_path / "out" / "report.json"
    md_path = tmp_path / "out" / "report.md"
    evaluator.save_report(report, str(json_path))
    evaluator.save_markdown(report, str(md_path))

    # JSON round-trips
    loaded = json.loads(json_path.read_text())
    assert loaded["total_questions"] == 2

    # Markdown contains the failure diagnostics
    md = md_path.read_text()
    assert "Evaluation Report" in md
    assert "What is the business purpose?" in md
    assert "Expected tools" in md
    assert "Why it failed" in md
