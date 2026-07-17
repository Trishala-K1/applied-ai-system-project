# 🎵 Music Recommender Simulation — Applied AI System Extension

## Base Project

This project extends **[ai110-module3show-musicrecommendersimulation-starter](https://github.com/Trishala-K1/ai110-module3show-musicrecommendersimulation-starter)**, a Module 3 "Show What You Know" submission. The original project built a content-based music recommender in Python: given a user's taste profile (favorite genre, mood, target energy), it scored every song in a 20-track catalog and returned the top-5 best matches with plain-language reasons for each pick. It intentionally used no LLM — the whole system was a deterministic weighted-scoring function.

This extension adds an **agentic workflow** on top of that unchanged scoring engine: an LLM-driven loop that plans, acts, checks its own results against documented failure modes, and revises before explaining the picks in natural language.

## Project Summary

This project builds a content-based music recommender system in Python. Given a user's taste profile (favorite genre, mood, and target energy level), the system scores every song in a 20-track catalog and returns the top-5 best matches along with plain-language reasons for each pick.

Unlike collaborative filtering systems (which need data from many users), this system works entirely from song attributes — no listening history required. That makes it simple, transparent, and easy to evaluate.

---

## 🤖 Agentic Extension

The original system only accepted structured profiles (`genre`, `mood`, `energy`, `likes_acoustic`). The agentic layer (`src/agent.py`) lets a listener describe what they want in plain English, and wraps the existing scoring engine in a **plan → act → check → (revise → act → check) → explain** loop, capped at one retry so it stays bounded and demoable.

**Architecture diagram:** [diagrams/architecture.mmd](diagrams/architecture.mmd)

| Step | What it does | LLM call? |
|---|---|---|
| Plan | Parses free text into a structured profile + confidence score | Yes, falls back to rule-based keyword matching if the LLM call fails |
| Act | Runs the **unmodified** `recommend_songs()` scoring engine | No |
| Check | Tests results against documented failure modes: `thin_margin` (top vs. bottom score too close), `no_mood_coverage` (no pick got a mood bonus), `weak_overall_matches` (low average score) | No — deterministic, unit-tested |
| Revise | If the check fails, proposes an adjusted profile using the catalog's actual genre/mood vocabulary | Yes, falls back to a synonym/vocab-matching rule if the LLM call fails |
| Explain | Writes a 2–4 sentence natural-language summary, grounded only in the actual titles/artists/scores/reasons computed above | Yes, falls back to a templated summary if the LLM call fails |

**Offline fallback mode:** if `ANTHROPIC_API_KEY` is missing or the call errors (e.g. no credit balance), each step transparently degrades to a small deterministic stand-in instead of crashing, and the trace records which mode (`"llm"` or `"offline_fallback"`) actually ran for every step. This is a legitimate reliability feature (graceful degradation), not a substitute for the real LLM integration — see the honestly-labeled sample runs below, which were captured in offline mode because none of the API keys available to me during development had an active credit balance.

Every run appends a full JSON trace (input, every attempt's profile + check result, final profile, mode per step, summary) to `logs/agent_traces.jsonl` — this is the reproducibility/evidence trail referenced in the Testing section below.

### Setup for the agentic feature

1. Copy `.env.example` to `.env` and add your Anthropic API key (or `export ANTHROPIC_API_KEY=sk-ant-...` directly):
   ```bash
   cp .env.example .env
   ```
2. Run it:
   ```bash
   python -m src.agent_main "I want something upbeat but chill at the same time"
   ```

### Sample Interactions

The two runs below are real, unedited terminal output. They ran in **offline fallback mode** — during development, none of the API keys I had access to (my own, and one provided through the course) had an active credit balance, so every LLM call raised and the system fell back to its rule-based stand-ins, exactly as designed. `Modes used` on the last line of each run confirms this rather than hiding it.

```
$ python -m src.agent_main "I want something upbeat but chill at the same time"
Loaded songs: 20

Request: I want something upbeat but chill at the same time

  1. Spacewalk Thoughts by Orbit Bloom — 3.73 | genre match (+2.0); mood match (+1.0); energy similarity (+0.73)
  2. Midnight Coding by LoRoom — 1.87 | mood match (+1.0); energy similarity (+0.87)
  3. Library Rain by Paper Lanterns — 1.80 | mood match (+1.0); energy similarity (+0.80)
  4. Velvet Smoke by Aria Blue — 1.00 | energy similarity (+1.00)
  5. Dusty Roads by Hank Canyon — 0.95 | energy similarity (+0.95)

Summary: For "I want something upbeat but chill at the same time", the top picks were: Spacewalk Thoughts by Orbit Bloom (score 3.73: genre match (+2.0); mood match (+1.0); energy similarity (+0.73)); Midnight Coding by LoRoom (score 1.87: mood match (+1.0); energy similarity (+0.87)); Library Rain by Paper Lanterns (score 1.80: mood match (+1.0); energy similarity (+0.80)); Velvet Smoke by Aria Blue (score 1.00: energy similarity (+1.00)); Dusty Roads by Hank Canyon (score 0.95: energy similarity (+0.95)).

Attempts taken: 1
Final check: {'passed': True, 'reason': 'healthy'}
Modes used -- plan: offline_fallback, revise: [], explain: offline_fallback
Full trace appended to logs/agent_traces.jsonl
```

```
$ python -m src.agent_main "high energy but sad"
Loaded songs: 20

Request: high energy but sad

  1. Spacewalk Thoughts by Orbit Bloom — 3.38 | genre match (+2.0); mood match (+1.0); energy similarity (+0.38)
  2. Midnight Coding by LoRoom — 1.52 | mood match (+1.0); energy similarity (+0.52)
  3. Library Rain by Paper Lanterns — 1.45 | mood match (+1.0); energy similarity (+0.45)
  4. Storm Runner by Voltline — 0.99 | energy similarity (+0.99)
  5. Neon Pulse by Circuit Drop — 0.98 | energy similarity (+0.98)

Summary: For "high energy but sad", the top picks were: Spacewalk Thoughts by Orbit Bloom (score 3.38: genre match (+2.0); mood match (+1.0); energy similarity (+0.38)); Midnight Coding by LoRoom (score 1.52: mood match (+1.0); energy similarity (+0.52)); Library Rain by Paper Lanterns (score 1.45: mood match (+1.0); energy similarity (+0.45)); Storm Runner by Voltline (score 0.99: energy similarity (+0.99)); Neon Pulse by Circuit Drop (score 0.98: energy similarity (+0.98)).

Attempts taken: 1
Final check: {'passed': True, 'reason': 'healthy'}
Modes used -- plan: offline_fallback, revise: [], explain: offline_fallback
Full trace appended to logs/agent_traces.jsonl
```

**Why neither run triggered a revise, and what that reveals:** the offline `_offline_plan()` heuristic always snaps an unrecognized mood word (like "sad", which isn't in the catalog's mood vocabulary) to the first available catalog mood (`"chill"`) rather than passing it through literally. Since 3 of the 20 songs are tagged `chill`, at least one nearly always survives into the top 5, so `check_results()` reports `no_mood_coverage` far less often here than it would with a real LLM — a live `plan()` call is not restricted to catalog vocabulary and could genuinely output `"mood": "sad"`, exactly like the original (non-agentic) project's manual "Adversarial" experiment demonstrated. **This is a known, documented limitation of the offline fallback**, not a claim that the revise path is untested — `tests/test_agent.py::test_run_agent_revises_once_when_first_attempt_is_weak` exercises the full revise loop directly with a mocked LLM response that returns an out-of-vocabulary profile, and passes.

_If you get a working API key later, re-run the two commands above — `Modes used` will read `llm` instead of `offline_fallback`, and it's worth trying "high energy but sad" again since a real LLM plan() may reproduce the revise path live._

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

Note: all `test_agent.py` tests mock the LLM call (`src.agent.call_llm`), so the full test suite runs without an `ANTHROPIC_API_KEY` and without any network access. The rule-based `check_results()` function is tested directly with real (non-mocked) inputs.

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

## Reliability Testing Summary

**Automated tests:** 8/8 `pytest` tests passed (4 on the original scoring engine, 4 on the agent). The agent tests cover:

| Test Input | Evaluation Criteria | Result |
|---|---|---|
| 5 results with scores 1.02→0.98, no mood matches | `check_results` should flag `thin_margin` and `no_mood_coverage` | Pass |
| 2 results, no mood matches, healthy margin | `check_results` should still flag `no_mood_coverage` alone | Pass |
| 3 results with strong genre/mood/energy matches | `check_results` should report `passed: True, reason: "healthy"` | Pass |
| Empty results list | `check_results` should fail gracefully with `reason: "no_results"`, not crash | Pass |
| Request that maps cleanly onto the catalog (mocked LLM) | Agent should skip the revise step entirely (1 attempt, 2 LLM calls: plan + explain) | Pass |
| Adversarial request with no catalog match (mocked LLM) | Agent should revise once and recover a healthy result (2 attempts, 3 LLM calls: plan + revise + explain) | Pass |

**Confidence scoring:** the `plan()` step asks the LLM to self-report a `confidence` score (0.0–1.0) on how cleanly the request maps to genre/mood/energy; this is stored in every trace entry in `logs/agent_traces.jsonl`. When plan() runs in offline fallback mode instead, it always reports a fixed `confidence: 0.3`, reflecting that keyword-matching is inherently less certain than an LLM read — this is a deliberate, hardcoded signal, not a measured one.

**Real run results (both in offline fallback mode, see Sample Interactions above):**

| Test Input | Mode | Confidence | Attempts | Final Check |
|---|---|---|---|---|
| "I want something upbeat but chill at the same time" | offline_fallback | 0.3 (fixed) | 1 | `passed: True, reason: "healthy"` |
| "high energy but sad" | offline_fallback | 0.3 (fixed) | 1 | `passed: True, reason: "healthy"` |

Both real runs passed on the first attempt without needing a revise — see the "Why neither run triggered a revise" note above for why, and why the revise path is still verified to work (via the mocked unit test, not skipped).

_If a working API key becomes available, re-run and replace this table with real LLM-mode confidence scores, which will vary per request instead of a fixed 0.3._

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
