# 🎵 Music Recommender Simulation

## Project Summary

This project builds a content-based music recommender system in Python. Given a user's taste profile (favorite genre, mood, and target energy level), the system scores every song in a 20-track catalog and returns the top-5 best matches along with plain-language reasons for each pick.

Unlike collaborative filtering systems (which need data from many users), this system works entirely from song attributes — no listening history required. That makes it simple, transparent, and easy to evaluate.

---

## How The System Works

**Real-world systems** like Spotify combine two approaches:
- **Collaborative filtering** — "users who liked X also liked Y" — leverages patterns across millions of listeners.
- **Content-based filtering** — scores songs by how closely their attributes (genre, energy, mood, tempo) match what a single user says they want.

**This simulation** uses content-based filtering only. Here's the algorithm recipe:

| Signal | Points |
|--------|--------|
| Genre matches user's favorite genre | +2.0 |
| Mood matches user's favorite mood | +1.0 |
| Energy proximity: `1.0 - abs(song_energy - target_energy)` | 0.0 – 1.0 |
| Song is acoustic and user likes acoustic | +0.5 bonus |

Songs are ranked highest-score first; ties favor the order they appear in the CSV.

**Features used per `Song`:** `genre`, `mood`, `energy`, `tempo_bpm`, `valence`, `danceability`, `acousticness`

**Fields stored in `UserProfile`:** `favorite_genre`, `favorite_mood`, `target_energy`, `likes_acoustic`

**Data flow:**

```
User Preferences
       ↓
score_song() called for every song in the catalog
       ↓
Songs sorted by score (highest first)
       ↓
Top-k recommendations returned with reasons
```

**Expected bias:** Genre gets the highest weight (2.0), so songs whose genre matches will almost always appear above equally-good songs in other genres. A small catalog also amplifies this — only 3 pop songs exist, so pop fans will see the same titles repeatedly.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   python -m src.main
   ```

### Running Tests

```bash
pytest
```

---

## Sample Recommendation Output

```
Loaded songs: 20

=======================================================
  Profile: High-Energy Pop
=======================================================
  1. Sunrise City by Neon Echo
     Score: 3.97 | genre match (+2.0); mood match (+1.0); energy similarity (+0.97)
  2. Gym Hero by Max Pulse
     Score: 2.92 | genre match (+2.0); energy similarity (+0.92)
  3. Rooftop Lights by Indigo Parade
     Score: 1.91 | mood match (+1.0); energy similarity (+0.91)
  4. Neon Pulse by Circuit Drop
     Score: 0.97 | energy similarity (+0.97)
  5. Ritmo Caliente by Los Fuego
     Score: 0.95 | energy similarity (+0.95)


=======================================================
  Profile: Chill Lofi (Acoustic Fan)
=======================================================
  1. Midnight Coding by LoRoom
     Score: 4.48 | genre match (+2.0); mood match (+1.0); energy similarity (+0.98); acoustic bonus (+0.5)
  2. Library Rain by Paper Lanterns
     Score: 4.45 | genre match (+2.0); mood match (+1.0); energy similarity (+0.95); acoustic bonus (+0.5)
  3. Focus Flow by LoRoom
     Score: 3.50 | genre match (+2.0); energy similarity (+1.00); acoustic bonus (+0.5)
  4. Spacewalk Thoughts by Orbit Bloom
     Score: 2.38 | mood match (+1.0); energy similarity (+0.88); acoustic bonus (+0.5)
  5. Coffee Shop Stories by Slow Stereo
     Score: 1.47 | energy similarity (+0.97); acoustic bonus (+0.5)


=======================================================
  Profile: Deep Intense Rock
=======================================================
  1. Storm Runner by Voltline
     Score: 3.99 | genre match (+2.0); mood match (+1.0); energy similarity (+0.99)
  2. Gym Hero by Max Pulse
     Score: 1.97 | mood match (+1.0); energy similarity (+0.97)
  3. Iron Fist by Shredder
     Score: 1.95 | mood match (+1.0); energy similarity (+0.95)
  4. Neon Pulse by Circuit Drop
     Score: 0.98 | energy similarity (+0.98)
  5. Sunrise City by Neon Echo
     Score: 0.92 | energy similarity (+0.92)


=======================================================
  Profile: Adversarial: High Energy + Sad Mood
=======================================================
  1. Spacewalk Thoughts by Orbit Bloom
     Score: 2.33 | genre match (+2.0); energy similarity (+0.33)
  2. Iron Fist by Shredder
     Score: 1.00 | energy similarity (+1.00)
  3. Gym Hero by Max Pulse
     Score: 0.98 | energy similarity (+0.98)
  4. Storm Runner by Voltline
     Score: 0.96 | energy similarity (+0.96)
  5. Neon Pulse by Circuit Drop
     Score: 0.93 | energy similarity (+0.93)
```

---

## Experiments You Tried

**Experiment 1 — Adversarial profile (high energy + sad mood):**
Asking for ambient + sad + energy 0.95 is deliberately contradictory — ambient songs in the dataset are all low energy. The system correctly gives Spacewalk Thoughts a genre-match bonus, but its energy score is terrible (0.33), and the runner-up Iron Fist is a metal song. The "sad" mood got zero matches because no songs in the catalog are tagged sad. This reveals that missing mood coverage causes the mood dimension to silently disappear.

**Experiment 2 — Doubling energy weight (hypothetical):**
If the energy proximity term were multiplied by 2, the adversarial Iron Fist result (energy 0.95, gap = 0.0) would outscore the genre-matched Spacewalk Thoughts, showing how sensitive rankings are to weight choices.

**Experiment 3 — Removing mood check:**
Commenting out the mood bonus collapsed the lofi profiles — Midnight Coding and Library Rain still ranked first (genre + acoustic bonus), but their margin over non-lofi acoustic songs like Rain on Glass shrank dramatically, illustrating that mood adds real differentiation.

---

## Limitations and Risks

- **Tiny catalog:** 20 songs means genre categories often have only 1–3 representatives. Recommendations feel repetitive fast.
- **Genre over-weight:** The 2-point genre bonus dominates. A pop song with the wrong mood still outscores a perfect-mood song from another genre.
- **No mood coverage for many tags:** Tags like "nostalgic," "confident," and "peaceful" appear in the catalog but almost never in user profiles, making those songs invisible.
- **No tempo or valence in scoring:** Both fields are loaded but unused — a jazz fan who wants high valence gets no benefit from valence data.
- **Filter bubble risk:** A user who always picks pop will only ever see pop results; there is no diversity injection to surface surprising matches.

---

## Reflection

See [model_card.md](model_card.md) for the full model card and personal reflection.
