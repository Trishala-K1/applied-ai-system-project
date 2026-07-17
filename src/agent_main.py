"""
Interactive CLI for the agentic music recommendation loop.
Run from the project root: python -m src.agent_main "some request in plain English"

If ANTHROPIC_API_KEY is unset or the API call fails (e.g. no credit balance),
each step transparently falls back to a rule-based offline mode rather than
crashing -- the printed output below states which mode each step actually ran in.
"""
import sys

from src.agent import run_agent
from src.recommender import load_songs


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m src.agent_main "your request in plain English"')
        sys.exit(1)

    user_text = " ".join(sys.argv[1:])
    songs = load_songs("data/songs.csv")
    outcome = run_agent(user_text, songs)
    trace = outcome["trace"]

    print(f"\nRequest: {user_text}\n")
    for i, (song, score, reasons) in enumerate(outcome["results"], 1):
        print(f"  {i}. {song['title']} by {song['artist']} — {score:.2f} | {reasons}")

    print(f"\nSummary: {outcome['summary']}\n")
    print(f"Attempts taken: {len(trace['attempts'])}")
    print(f"Final check: {trace['final_check']}")
    print(
        f"Modes used -- plan: {trace['plan_mode']}, "
        f"revise: {trace.get('revise_modes', [])}, "
        f"explain: {trace['explain_mode']}"
    )
    print("Full trace appended to logs/agent_traces.jsonl")


if __name__ == "__main__":
    main()
