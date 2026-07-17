from unittest.mock import patch

from src.agent import check_results, run_agent


def test_check_results_flags_thin_margin_and_no_mood_coverage():
    results = [
        ({"title": "A"}, 1.02, "energy similarity (+1.02)"),
        ({"title": "B"}, 1.01, "energy similarity (+1.01)"),
        ({"title": "C"}, 1.00, "energy similarity (+1.00)"),
        ({"title": "D"}, 0.99, "energy similarity (+0.99)"),
        ({"title": "E"}, 0.98, "energy similarity (+0.98)"),
    ]
    check = check_results(results)
    assert check["passed"] is False
    assert "thin_margin" in check["reason"]
    assert "no_mood_coverage" in check["reason"]


def test_check_results_flags_no_mood_coverage_even_with_healthy_margin():
    results = [
        ({"title": "A"}, 3.5, "genre match (+2.0); energy similarity (+1.5)"),
        ({"title": "B"}, 1.0, "energy similarity (+1.0)"),
    ]
    check = check_results(results)
    assert check["passed"] is False
    assert "no_mood_coverage" in check["reason"]


def test_check_results_passes_on_healthy_results():
    results = [
        ({"title": "A"}, 3.9, "genre match (+2.0); mood match (+1.0); energy similarity (+0.9)"),
        ({"title": "B"}, 2.0, "genre match (+2.0)"),
        ({"title": "C"}, 1.5, "energy similarity (+1.5)"),
    ]
    check = check_results(results)
    assert check["passed"] is True
    assert check["reason"] == "healthy"


def test_check_results_handles_empty_results():
    assert check_results([]) == {"passed": False, "reason": "no_results"}


@patch("src.agent.call_llm")
def test_run_agent_skips_revise_when_first_attempt_is_healthy(mock_call_llm):
    songs = [
        {"id": 1, "title": "Test Pop", "artist": "A", "genre": "pop", "mood": "happy",
         "energy": 0.8, "tempo_bpm": 120, "valence": 0.9, "danceability": 0.8, "acousticness": 0.2},
        {"id": 2, "title": "Test Lofi", "artist": "B", "genre": "lofi", "mood": "chill",
         "energy": 0.4, "tempo_bpm": 80, "valence": 0.6, "danceability": 0.5, "acousticness": 0.9},
    ]

    mock_call_llm.side_effect = [
        '{"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": false, "confidence": 0.9}',
        "Here are two picks that match your upbeat pop request.",
    ]

    outcome = run_agent("I want upbeat pop music", songs, k=2, max_retries=1)

    assert len(outcome["results"]) == 2
    assert outcome["summary"].startswith("Here are two picks")
    assert outcome["trace"]["attempts"][0]["check"]["passed"] is True
    assert len(outcome["trace"]["attempts"]) == 1
    assert mock_call_llm.call_count == 2  # plan + explain only, no revise needed


@patch("src.agent.call_llm")
def test_run_agent_revises_once_when_first_attempt_is_weak(mock_call_llm):
    songs = [
        {"id": 1, "title": "Test Pop", "artist": "A", "genre": "pop", "mood": "happy",
         "energy": 0.8, "tempo_bpm": 120, "valence": 0.9, "danceability": 0.8, "acousticness": 0.2},
        {"id": 2, "title": "Test Metal", "artist": "B", "genre": "metal", "mood": "intense",
         "energy": 0.95, "tempo_bpm": 180, "valence": 0.3, "danceability": 0.5, "acousticness": 0.05},
    ]

    mock_call_llm.side_effect = [
        # plan(): asks for a genre/mood combo with no catalog match at all
        '{"genre": "ambient", "mood": "sad", "energy": 0.95, "likes_acoustic": false, "confidence": 0.4}',
        # revise(): switches to a profile that actually matches the catalog
        '{"genre": "metal", "mood": "intense", "energy": 0.95, "likes_acoustic": false}',
        # explain()
        "Storm Runner-style picks matched once we adjusted for your intense mood.",
    ]

    outcome = run_agent("high energy but sad", songs, k=2, max_retries=1)

    assert mock_call_llm.call_count == 3  # plan + revise + explain
    assert len(outcome["trace"]["attempts"]) == 2
    assert outcome["trace"]["attempts"][0]["check"]["passed"] is False
    assert outcome["trace"]["final_profile"]["genre"] == "metal"
