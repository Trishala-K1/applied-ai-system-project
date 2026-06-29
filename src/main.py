"""
Command line runner for the Music Recommender Simulation.
Run from the project root: python -m src.main
"""

from src.recommender import load_songs, recommend_songs


def print_recommendations(profile_name: str, recommendations: list) -> None:
    """Prints a formatted recommendation list for a given profile."""
    print(f"\n{'='*55}")
    print(f"  Profile: {profile_name}")
    print('='*55)
    for i, rec in enumerate(recommendations, 1):
        song, score, explanation = rec
        print(f"  {i}. {song['title']} by {song['artist']}")
        print(f"     Score: {score:.2f} | {explanation}")
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")

    profiles = [
        (
            "High-Energy Pop",
            {"genre": "pop", "mood": "happy", "energy": 0.85},
        ),
        (
            "Chill Lofi (Acoustic Fan)",
            {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True},
        ),
        (
            "Deep Intense Rock",
            {"genre": "rock", "mood": "intense", "energy": 0.9},
        ),
        (
            "Adversarial: High Energy + Sad Mood",
            {"genre": "ambient", "mood": "sad", "energy": 0.95},
        ),
    ]

    for profile_name, prefs in profiles:
        recs = recommend_songs(prefs, songs, k=5)
        print_recommendations(profile_name, recs)


if __name__ == "__main__":
    main()
