# 🎧 Model Card: VibeFinder 1.0

## 1. Model Name

**VibeFinder 1.0** — a content-based music recommender simulation built for the AI110 Module 3 Show What You Know project.

---

## 2. Intended Use

VibeFinder 1.0 is designed to demonstrate how a simple content-based filtering algorithm turns user taste preferences into ranked song recommendations. It is intended for classroom exploration and learning, not production deployment.

**It is for:** Students learning how recommendation systems work, developers prototyping scoring logic, anyone curious about how Spotify-style "you might like" lists are constructed.

**It is NOT for:** Real users expecting personalized playlists, systems where fairness or diversity across genres is required, or any production music service.

The system assumes the user can express their taste as a single genre, a mood label, and an energy level between 0 and 1. Users with complex or evolving tastes will get mediocre results because the profile is intentionally simple.

---

## 3. How the Model Works

VibeFinder looks at every song in its catalog and gives each one a "match score" against the user's stated preferences. A higher score means a stronger match. Here's the recipe in plain English:

- If a song's **genre** matches the user's favorite genre, it gets 2 bonus points. Genre is weighted highest because it is the broadest descriptor of musical style.
- If a song's **mood** matches the user's favorite mood (e.g., both are "happy"), it gets 1 bonus point.
- Every song also gets an **energy proximity score** between 0 and 1. A song with exactly the right energy (say, 0.8 for a user who wants 0.8) earns the full 1.0. A song with completely opposite energy (0.0 vs. 0.8) earns only 0.2. This rewards closeness rather than just "high energy" or "low energy."
- If the user says they like acoustic music and a song has a high acousticness rating, it earns a small **acoustic bonus** of 0.5 points.

After scoring every song, the system sorts the list from highest to lowest score and returns the top 5. Each recommendation comes with a plain-English list of reasons (e.g., "genre match (+2.0); energy similarity (+0.97)").

---

## 4. Data

The catalog contains **20 songs** across a wide range of genres: pop, lofi, rock, electronic, hip-hop, classical, country, metal, R&B, reggae, folk, latin, blues, jazz, synthwave, ambient, and indie pop.

Each song has these fields: `id`, `title`, `artist`, `genre`, `mood`, `energy` (0–1), `tempo_bpm`, `valence` (0–1), `danceability` (0–1), and `acousticness` (0–1).

The original 10-song starter was expanded to 20 to add genre diversity. However, the catalog is still very small — many genres have only one representative. There is also no representation of non-English music traditions beyond a single latin track, and mood labels are inconsistent (some songs use "intense," others "energetic" — these are treated as different moods even when the feeling is similar).

Key things missing: lyrics, artist popularity, listener demographic data, temporal trends (what's popular right now), and language metadata.

---

## 5. Strengths

- Works well for users with a **clear genre preference** and a matching song in the catalog. For example, the rock fan always gets Storm Runner at the top, and the score explanation makes it obvious why.
- The **energy proximity scoring** is genuinely useful — it means a chill lofi user doesn't get blasted with high-energy EDM just because they share a "chill" mood tag with an electronic song.
- The **acoustic bonus** adds a nice secondary preference signal that rewards multi-dimensional matches.
- Every recommendation comes with an explanation, which is something many real systems don't provide.

---

## 6. Limitations and Bias

**Filter bubble:** Because genre carries the biggest weight, the system reliably surfaces the same 2–3 genre-matching songs for any given user type. Users will never discover music outside their stated genre unless no matching songs exist.

**Mood vocabulary mismatch:** The catalog uses mood labels like "nostalgic," "confident," and "peaceful" that are unlikely to appear as user preferences. A user saying "mood: confident" would get zero mood bonus points for any song, effectively making the mood feature invisible for that user.

**Pop over-representation in results:** Pop songs (Sunrise City, Gym Hero) have high energy scores that land them in many ranked lists even for non-pop profiles, because high energy is a common denominator across multiple user types.

**Dataset skew:** 20 songs is too small. Out of 17 genres represented, 13 have only one track. This means genre diversity is an illusion — there's really just one song to recommend per non-pop genre.

**No temporal context:** The system has no way to know if a user is in the mood for something different today than they were last week.

---

## 7. Evaluation

**Profiles tested:**

1. **High-Energy Pop** (`genre=pop, mood=happy, energy=0.85`) — Results felt exactly right. Sunrise City appeared first because it matched all three signals. Gym Hero came second despite not matching mood, because its genre and energy were strong enough.

2. **Chill Lofi (Acoustic Fan)** (`genre=lofi, mood=chill, energy=0.4, likes_acoustic=True`) — Very strong results. The top 3 were all lofi tracks, with acoustic bonus pushing them up. This profile benefits most from the acoustic signal.

3. **Deep Intense Rock** (`genre=rock, mood=intense, energy=0.9`) — Storm Runner scored almost 4.0 and was the clear winner. The next results (Gym Hero, Iron Fist) both shared the "intense" mood but different genres, which is reasonable.

4. **Adversarial: High Energy + Sad Mood** (`genre=ambient, mood=sad, energy=0.95`) — Interesting failure case. Spacewalk Thoughts ranked first because of the genre match, even though its energy (0.28) is almost the opposite of what the user asked for. No song in the catalog has a "sad" mood tag, so that dimension silently dropped out. This shows the system can be "tricked" by genre weight when mood has no coverage.

**Comparing Pop vs Rock profiles:** Both are high-energy, but the Rock profile gets metal and rock songs while the Pop profile stays in bubbly territory — that's the genre weight doing its job. The energy dimension alone would merge these two profiles; genre keeps them separate.

**Comparing Lofi vs Ambient:** Both prefer low energy, but the Lofi profile gets acoustic lofi tracks while Ambient only has one match (Spacewalk Thoughts) and then falls back to energy-only rankings. This shows how catalog size limits the quality of less-popular genres.

---

## 8. Future Work

1. **Add valence and tempo to the scoring function.** Both fields are already in the CSV but unused. A user who wants "upbeat" songs could benefit from high valence scoring; a runner who wants ~150 BPM songs could benefit from tempo proximity.

2. **Introduce a diversity penalty.** If the top 5 results are all the same genre, randomly replace one with the highest-scoring song from a different genre. This breaks the filter bubble without changing the core algorithm.

3. **Expand the catalog significantly.** A real test of this system needs at least 50–100 songs per genre so genre-matching doesn't trivially solve the ranking.

4. **Support multi-value preferences.** Real users like more than one genre. Allowing `genres: ["pop", "indie pop"]` with different weights would better capture taste complexity.

---

## 9. Personal Reflection

Building VibeFinder made the abstraction of "recommendation" very concrete. Before this project, "Spotify recommends songs" felt like magic. Now it's clear that at its simplest, it's just a loop: pick features, assign weights, score everything, sort. The surprising part was how much the *choice of weights* determines whether the system feels "smart" — a tiny change from 2.0 to 3.0 on genre makes the system feel almost single-minded about genre matching.

The most useful role AI played was helping design the energy proximity formula. I initially thought about just awarding points for "high energy" or "low energy" songs, but when I described the problem to the AI, it correctly pointed out that a user who wants energy=0.7 isn't well served by a song with energy=1.0 any more than by one with energy=0.3. The `1.0 - abs(difference)` formula was the AI's suggestion, and it's genuinely better than what I would have written instinctively.

I also had to double-check the AI's first scoring implementation — it initially returned `score` without ever building the `reasons` list, which would have broken the explainability feature. That's a good reminder that AI-generated code needs review, not just testing.

This project changed how I think about algorithmic bias. It's not usually about the algorithm being "evil" — it's about the dataset being lopsided and the weights being chosen for convenience rather than fairness. Our pop-heavy catalog isn't discriminating intentionally; it's just the result of whoever built the starter CSV thinking in terms of familiar genres. That same dynamic plays out at scale in every commercial recommender system.
