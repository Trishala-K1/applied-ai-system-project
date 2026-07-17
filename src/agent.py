"""
Agentic layer on top of the existing content-based recommender.

Loop: plan -> act -> check -> (revise -> act -> check, at most once) -> explain

- plan(), revise(), and explain() call the LLM by default.
- If the LLM call raises (missing key, no credit, network error), each step
  falls back to a small deterministic, rule-based stand-in so the pipeline
  still produces real output instead of crashing. Every trace entry records
  which mode ("llm" or "offline_fallback") actually ran each step, so this
  is never silently misrepresented as a live LLM response.
- check_results() is deliberately pure/rule-based (no LLM call) so it is
  reproducible and unit-testable without hitting the network. It tests
  results against the failure modes documented in README.md and model_card.md
  (genre over-weight, missing mood coverage, weak overall matches).
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from src.llm_client import call_llm
from src.recommender import recommend_songs

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "agent_traces.jsonl")

PLAN_SYSTEM_PROMPT = """You convert a listener's free-text music request into a structured profile.
Respond with ONLY a JSON object, no other text, in this exact shape:
{"genre": "<one word genre>", "mood": "<one word mood>", "energy": <float 0.0-1.0>, "likes_acoustic": <true|false>, "confidence": <float 0.0-1.0>}
"confidence" reflects how sure you are the request maps cleanly onto genre/mood/energy."""

REVISE_SYSTEM_PROMPT = """A music recommender's first attempt produced weak results for a listener's request.
You will get the original request, the profile that was tried, the reason it was flagged weak, and the
actual genre/mood vocabulary available in the song catalog. Propose ONE revised profile that is more likely
to find good matches in that vocabulary, while staying faithful to the listener's intent.
Respond with ONLY a JSON object in this exact shape:
{"genre": "<one word genre from the catalog vocabulary>", "mood": "<one word mood from the catalog vocabulary>", "energy": <float 0.0-1.0>, "likes_acoustic": <true|false>}"""

EXPLAIN_SYSTEM_PROMPT = """You explain music recommendations to a listener in 2-4 friendly sentences.
Use ONLY the song titles, artists, scores, and reasons given to you -- do not invent facts about the songs."""


def _catalog_vocab(songs: List[Dict]) -> Dict[str, List[str]]:
    return {
        "genres": sorted({s["genre"] for s in songs}),
        "moods": sorted({s["mood"] for s in songs}),
    }


def _parse_json_response(text: str, fallback: Dict) -> Dict:
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return dict(fallback)


# Keyword heuristics used only by the offline fallback path (no LLM available).
_ENERGY_KEYWORDS = {
    "upbeat": 0.8, "energetic": 0.85, "high energy": 0.9, "intense": 0.9,
    "hype": 0.9, "chill": 0.3, "relaxed": 0.3, "calm": 0.25, "mellow": 0.3,
    "slow": 0.2, "sleepy": 0.15, "peaceful": 0.25,
}
_MOOD_SYNONYMS = {
    "sad": "melancholic", "angry": "intense", "cheerful": "happy",
    "sleepy": "chill", "romantic": "romantic", "nostalgic": "nostalgic",
}


def _offline_plan(user_text: str, songs: List[Dict]) -> Dict:
    """Rule-based stand-in for plan() when the LLM is unavailable."""
    text = user_text.lower()
    vocab = _catalog_vocab(songs)

    genre = next((g for g in vocab["genres"] if g in text), vocab["genres"][0])
    mood = next((m for m in vocab["moods"] if m in text), vocab["moods"][0])

    energy_hits = [v for k, v in _ENERGY_KEYWORDS.items() if k in text]
    energy = sum(energy_hits) / len(energy_hits) if energy_hits else 0.5

    return {
        "genre": genre,
        "mood": mood,
        "energy": round(energy, 2),
        "likes_acoustic": "acoustic" in text,
        "confidence": 0.3,  # heuristic parsing is inherently less certain than an LLM read
    }


def plan(user_text: str, songs: List[Dict]) -> Tuple[Dict, float, str]:
    """Turns free text into a structured profile + confidence score. Falls back to
    rule-based parsing if the LLM call fails. Returns (profile, confidence, mode)."""
    fallback = {"genre": "pop", "mood": "happy", "energy": 0.5, "likes_acoustic": False, "confidence": 0.0}
    try:
        raw = call_llm(PLAN_SYSTEM_PROMPT, user_text)
        parsed = _parse_json_response(raw, fallback)
        confidence = float(parsed.pop("confidence", 0.5))
        return parsed, confidence, "llm"
    except Exception:
        parsed = _offline_plan(user_text, songs)
        confidence = float(parsed.pop("confidence", 0.3))
        return parsed, confidence, "offline_fallback"


def check_results(scored_results: List[Tuple[Dict, float, str]]) -> Dict:
    """Deterministic, rule-based check against documented failure modes. No LLM call."""
    if not scored_results:
        return {"passed": False, "reason": "no_results"}

    scores = [score for _, score, _ in scored_results]
    margin = scores[0] - scores[-1]
    has_mood_match = any("mood match" in explanation for _, _, explanation in scored_results)
    avg_score = sum(scores) / len(scores)

    issues = []
    if margin < 0.5:
        issues.append("thin_margin")
    if not has_mood_match:
        issues.append("no_mood_coverage")
    if avg_score < 1.0:
        issues.append("weak_overall_matches")

    return {"passed": len(issues) == 0, "reason": ", ".join(issues) if issues else "healthy"}


def _offline_revise(profile: Dict, reason: str, songs: List[Dict]) -> Dict:
    """Rule-based stand-in for revise() when the LLM is unavailable."""
    vocab = _catalog_vocab(songs)
    revised = dict(profile)

    if "no_mood_coverage" in reason and revised.get("mood") not in vocab["moods"]:
        revised["mood"] = _MOOD_SYNONYMS.get(revised.get("mood", ""), vocab["moods"][0])

    if revised.get("genre") not in vocab["genres"]:
        revised["genre"] = vocab["genres"][0]

    return revised


def revise(user_text: str, profile: Dict, reason: str, songs: List[Dict]) -> Tuple[Dict, str]:
    """Proposes an adjusted profile given why the first attempt was weak. Falls back to
    rule-based synonym/vocab matching if the LLM call fails. Returns (profile, mode)."""
    vocab = _catalog_vocab(songs)
    try:
        prompt = (
            f"Original request: {user_text}\n"
            f"Profile tried: {json.dumps(profile)}\n"
            f"Why it was flagged weak: {reason}\n"
            f"Catalog genres: {vocab['genres']}\n"
            f"Catalog moods: {vocab['moods']}"
        )
        raw = call_llm(REVISE_SYSTEM_PROMPT, prompt)
        return _parse_json_response(raw, profile), "llm"
    except Exception:
        return _offline_revise(profile, reason, songs), "offline_fallback"


def _offline_explain(user_text: str, scored_results: List[Tuple[Dict, float, str]]) -> str:
    """Rule-based stand-in for explain() when the LLM is unavailable."""
    if not scored_results:
        return f"No strong matches were found for: \"{user_text}\"."
    picks = "; ".join(
        f"{song['title']} by {song['artist']} (score {score:.2f}: {reasons})"
        for song, score, reasons in scored_results
    )
    return f"For \"{user_text}\", the top picks were: {picks}."


def explain(user_text: str, scored_results: List[Tuple[Dict, float, str]]) -> Tuple[str, str]:
    """Writes a grounded natural-language summary of the final picks. Falls back to a
    templated summary if the LLM call fails. Returns (summary, mode)."""
    try:
        facts = [
            {"title": song["title"], "artist": song["artist"], "score": round(score, 2), "reasons": reasons}
            for song, score, reasons in scored_results
        ]
        prompt = f"Listener asked for: {user_text}\nFinal picks: {json.dumps(facts)}"
        return call_llm(EXPLAIN_SYSTEM_PROMPT, prompt), "llm"
    except Exception:
        return _offline_explain(user_text, scored_results), "offline_fallback"


def log_trace(trace: Dict) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    trace = dict(trace)
    trace["logged_at"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(trace) + "\n")


def run_agent(user_text: str, songs: List[Dict], k: int = 5, max_retries: int = 1) -> Dict:
    """Orchestrates plan -> act -> check -> (revise -> act -> check) -> explain."""
    trace = {"input": user_text, "attempts": []}

    profile, confidence, plan_mode = plan(user_text, songs)
    trace["confidence"] = confidence
    trace["plan_mode"] = plan_mode

    results: List[Tuple[Dict, float, str]] = []
    check = {"passed": False, "reason": "not_run"}
    for attempt in range(max_retries + 1):
        results = recommend_songs(profile, songs, k=k)
        check = check_results(results)
        trace["attempts"].append({"profile": profile, "check": check})
        if check["passed"] or attempt == max_retries:
            break
        profile, revise_mode = revise(user_text, profile, check["reason"], songs)
        trace.setdefault("revise_modes", []).append(revise_mode)

    summary, explain_mode = explain(user_text, results)
    trace["explain_mode"] = explain_mode
    trace["final_profile"] = profile
    trace["final_check"] = check
    trace["summary"] = summary
    log_trace(trace)

    return {"results": results, "summary": summary, "trace": trace}
