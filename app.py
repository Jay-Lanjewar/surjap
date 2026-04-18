import html
import json
import os
import streamlit as st
from google import genai
from dotenv import load_dotenv
from mood_engine import questions, calculate_scores, build_answer_summary
import re

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)  # remove all HTML tags
    return text.strip()
    data = json.loads(raw.strip())

    for key in ["description", "reason", "vibe"]:
        if key in data:
            data[key] = clean_text(data[key])

    return data, None


load_dotenv()
 
st.set_page_config(
    page_title="Jyani — Music for Your Moment",
    page_icon="🎵",
    layout="centered",
)
 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Syne', sans-serif; }
.stApp { background: #0d0d0d; color: #f0f0f0; }
.main-title {
    font-family: 'Syne', sans-serif; font-size: 3rem; font-weight: 800;
    letter-spacing: -1px;
    background: linear-gradient(135deg, #f0f0f0, #888);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0;
}
.subtitle { color: #666; font-size: 1rem; margin-top: 0.2rem; margin-bottom: 2rem; }
.question-text { font-family: 'Syne', sans-serif; font-size: 1.3rem; font-weight: 700; color: #f0f0f0; margin-bottom: 0.5rem; }
.progress-text { color: #555; font-size: 0.85rem; margin-bottom: 1.5rem; }
.mood-card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 16px; padding: 2rem; margin: 1rem 0; }
.mood-name { font-family: 'Syne', sans-serif; font-size: 2.5rem; font-weight: 800; }
.vibe-text { font-style: italic; color: #888; font-size: 0.95rem; margin-top: 0.5rem; }
.tag { display: inline-block; background: #222; border: 1px solid #333; border-radius: 20px; padding: 4px 14px; font-size: 0.8rem; color: #aaa; margin: 3px; }
div[data-testid="stRadio"] label {
    background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px;
    padding: 10px 16px; margin-bottom: 6px; cursor: pointer;
    color: #ccc; font-size: 0.95rem; width: 100%; display: block;
}
div[data-testid="stRadio"] label:hover { border-color: #555; color: #fff; }
.stButton > button {
    background: #f0f0f0; color: #0d0d0d; border: none; border-radius: 10px;
    padding: 12px 32px; font-family: 'Syne', sans-serif; font-weight: 700;
    font-size: 1rem; width: 100%; cursor: pointer;
}
.stButton > button:hover { opacity: 0.85; }
</style>
""", unsafe_allow_html=True)
 
 
def get_gemini_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY", "")
 
 
def get_recommendation(
    energy,
    valence,
    social,
    answer_summary,
    user_pref,
    era_pref,
    lang_pref,
    reference_songs,
):
    api_key = get_gemini_key()

    # ✅ single fallback (clean)
    if valence < 0:
        fallback_songs = [
            {"title": "Lag Ja Gale", "artist": "Lata Mangeshkar"},
            {"title": "Agar Tum Saath Ho", "artist": "Alka Yagnik"},
            {"title": "Kasoor", "artist": "Prateek Kuhad"},
        ]
    else:
        fallback_songs = [
            {"title": "Ilahi", "artist": "Arijit Singh"},
            {"title": "Safarnama", "artist": "Lucky Ali"},
            {"title": "Phir Se Ud Chala", "artist": "Mohit Chauhan"},
        ]

    fallback = {
        "mood_name": "Safe Mode",
        "emoji": "🎧",
        "description": "Something went wrong, but this should still feel close to your mood.",
        "vibe": "Music still understands you.",
        "reason": "Fallback based on your mood pattern",
        "genres": ["Bollywood", "Soft"],
        "songs": fallback_songs,
    }

    # ✅ if no API → still works
    if not api_key:
        return fallback, None

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""You are a music psychologist and expert recommender specializing in Indian music. A user answered 11 mood questions.

Their answers:
{answer_summary}

Mood scores (scale roughly -16 to +16):
- Energy: {energy} (negative = low energy, positive = high energy)
- Valence: {valence} (negative = sad/tense, positive = happy/content)
- Social: {social} (negative = wants to be alone, positive = wants connection)

User Preferences:
- Familiarity: {user_pref}
- Era: {era_pref}
- Language: {lang_pref}

Reference Songs:
{reference_songs}

Return ONLY a valid JSON object with no extra text, no markdown, no backticks:

{{
  "mood_name": "2-3 word evocative mood name",
  "emoji": "one fitting emoji",
  "description": "2 emotionally accurate, relatable sentences that feel personal and specific to the user's mood. Avoid generic wording.",
  "vibe": "a short relatable thought that feels like something the user might think in this mood",
  "genres": ["genre1", "genre2", "genre3"],
  "reason": "1 short sentence explaining why this music fits their state",
  "songs": [
    {{"title": "Song Name", "artist": "Artist Name"}},
    {{"title": "Song Name", "artist": "Artist Name"}},
    {{"title": "Song Name", "artist": "Artist Name"}},
    {{"title": "Song Name", "artist": "Artist Name"}},
    {{"title": "Song Name", "artist": "Artist Name"}},
    {{"title": "Song Name", "artist": "Artist Name"}}
  ]
}}

Rules:
- Add a "reason" field explaining why these songs match the user's mood.
- The FIRST song must be highly recognizable, emotionally strong, and likely familiar to the user.
- Use the reference songs to understand the user's taste. Recommend songs similar in style, melody, emotion, and era.
- Treat reference songs as the highest-priority taste signal, then balance them with mood, familiarity, era, and language preferences.
- If reference songs are classic Bollywood (Lata, Kishore, etc.), prefer similar artists, eras, and melodic structure.
- Default toward Indian music, but if language = "english", English songs are allowed when they genuinely fit the mood and preference profile.
- User taste changes depending on mood. Do not rigidly stick to one era or style. Adapt dynamically.
- Prefer emotionally relatable songs.
- Prefer songs users are likely to recognize.
- Avoid overly niche or unknown songs unless preference = "new".
- Avoid loud party songs unless energy is high.
- If familiarity = "familiar": choose highly popular, widely recognized songs.
- If familiarity = "mixed": mix popular + moderately known songs.
- If familiarity = "new": include lesser-known but high-quality songs.
- If era = "old": lean towards classic Bollywood, especially 60s–80s songs.
- If era = "mid": lean towards 2000s–2010s songs.
- If era = "modern": lean towards modern songs.
- If era = "dynamic": choose era based on mood. Low energy should lean toward old soft melodic songs, while high energy can lean more modern or upbeat.
- If language = "hindi": prioritize Hindi songs.
- If language = "marathi": include Marathi songs such as bhavgeet, soft Marathi, or Marathi film songs where they fit the mood.
- If language = "english": include English songs matching the mood.
- If language = "mixed": blend languages naturally.
- Keep recommendations dynamic and mood-driven even when applying familiarity, era, and language preferences.
- Examples of good artists: Arijit Singh, Pritam, AP Dhillon, Diljit Dosanjh, Nucleya, When Chai Met Toast, The Local Train, Prateek Kuhad, Ritviz, Anuv Jain, Darshan Raval, B Praak, Jubin Nautiyal, Shreya Ghoshal, Tanishka bahl.
- Match the mood axes precisely — don't recommend upbeat songs for low valence scores.
- Songs must actually exist on YouTube.
- Genres should reflect the actual recommendation mix — e.g. Bollywood, Hindi Indie, Marathi Bhavgeet, Soft Rock, English Pop, Sufi, Lo-fi Hindi, etc.
- Be specific, not generic.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw.strip())
        return data, None

    except Exception:
        return fallback, None


def init_state():
    if "step" not in st.session_state:
        st.session_state.step = 0
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "result" not in st.session_state:
        st.session_state.result = None
    if "error" not in st.session_state:
        st.session_state.error = None
    if "scores" not in st.session_state:
        st.session_state.scores = None
    if "user_pref" not in st.session_state:
        st.session_state.user_pref = None
    if "era_pref" not in st.session_state:
        st.session_state.era_pref = None
    if "lang_pref" not in st.session_state:
        st.session_state.lang_pref = None
    if "reference_songs" not in st.session_state:
        st.session_state.reference_songs = ""
    if "feedback" not in st.session_state:
        st.session_state.feedback = None
 
 
def reset():
    st.session_state.step = 0
    st.session_state.answers = {}
    st.session_state.result = None
    st.session_state.error = None
    st.session_state.scores = None
    st.session_state.user_pref = None
    st.session_state.era_pref = None
    st.session_state.lang_pref = None
    st.session_state.reference_songs = ""
    st.session_state.feedback = None
 
 
def fetch_recommendation():
    energy, valence, social = calculate_scores(st.session_state.answers)
    summary = build_answer_summary(st.session_state.answers)
    user_pref = st.session_state.user_pref or "mixed"
    era_pref = st.session_state.era_pref or "dynamic"
    lang_pref = st.session_state.lang_pref or "mixed"
    reference_songs = (st.session_state.reference_songs or "").strip() or "None provided"
    data, err = get_recommendation(
        energy,
        valence,
        social,
        summary,
        user_pref,
        era_pref,
        lang_pref,
        reference_songs,
    )
    st.session_state.scores = (energy, valence, social)
    st.session_state.error = err
    if err:
        st.session_state.result = None
    else:
        st.session_state.result = data
        st.session_state.feedback = None
 
 
init_state()
 
st.markdown('<p class="main-title">Jyani 🎵</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Answer 11 questions. Get music that fits your moment.</p>', unsafe_allow_html=True)
 
total = len(questions)
 
if st.session_state.result is None and st.session_state.error is None:
    step = st.session_state.step
 
    if step < total:
        q = questions[step]
        st.markdown(f'<p class="progress-text">Question {step + 1} of {total}</p>', unsafe_allow_html=True)
        st.progress(step / total)
        st.markdown(f'<p class="question-text">{q["text"]}</p>', unsafe_allow_html=True)
 
        option_labels = [opt["label"] for opt in q["options"]]
        choice = st.radio("Choose one option", option_labels, key=f"radio_{q['id']}", label_visibility="collapsed")
        if step == total - 1:
            st.text_input(
                "Enter 1-3 songs you like (optional)",
                key="reference_songs",
                placeholder="Example: Lag Jaa Gale, Iktara, Kasoor",
            )
 
        col1, col2 = st.columns([3, 1])
        with col1:
            btn_label = "Next →" if step < total - 1 else "See My Music 🎵"
            if st.button(btn_label):
                selected_index = option_labels.index(choice)
                st.session_state.answers[q["id"]] = selected_index
                selected_option = q["options"][selected_index]
                if q["id"] == "q9":
                    st.session_state.user_pref = selected_option.get("pref")
                if q["id"] == "q10":
                    st.session_state.era_pref = selected_option.get("era")
                if q["id"] == "q11":
                    st.session_state.lang_pref = selected_option.get("lang")
                if step < total - 1:
                    st.session_state.step += 1
                else:
                    with st.spinner("Reading your mood..."):
                        fetch_recommendation()
                st.rerun()
        with col2:
            if step > 0:
                if st.button("← Back"):
                    st.session_state.step -= 1
                    if questions[step]["id"] in st.session_state.answers:
                        del st.session_state.answers[questions[step]["id"]]
                    if questions[step]["id"] == "q9":
                        st.session_state.user_pref = None
                    if questions[step]["id"] == "q10":
                        st.session_state.era_pref = None
                    if questions[step]["id"] == "q11":
                        st.session_state.lang_pref = None
                    st.rerun()
 
elif st.session_state.error:
    st.error(st.session_state.error)
    if st.button("Try Again"):
        reset()
        st.rerun()
 
else:
    profile = st.session_state.result
    energy, valence, social = st.session_state.scores
 
    emoji = profile.get('emoji', '🎵')
    mood_name = profile.get('mood_name', 'Your Mood')
    desc = clean_text(profile.get('description', ''))
    reason = clean_text(profile.get('reason', ''))
    vibe = clean_text(profile.get('vibe', ''))
 
    st.markdown(f"""
    <div class="mood-card">
        <div style="font-size: 3rem;">{emoji}</div>
        <div class="mood-name">{mood_name}</div>
 
        <p style="color: #aaa; margin-top: 0.5rem;">
            {desc}
        </p>
 
        <p style="color: #888; font-size: 0.9rem; margin-top: 0.4rem;">
            💡 {reason}
        </p>
 
        <p class="vibe-text">"{vibe}"</p>
    </div>
    """, unsafe_allow_html=True)
 
    genres = profile.get("genres", [])
    if genres:
        st.markdown("#### 🎧 Genres for you")
        genres_html = " ".join([f'<span class="tag">{html.escape(g)}</span>' for g in genres])
        st.markdown(genres_html, unsafe_allow_html=True)
 
    songs = profile.get("songs", [])
    if songs:
        st.markdown("#### 🎵 Songs to listen to right now")
        for song in songs:
            title = song.get("title", "")
            artist = song.get("artist", "")
            query = f"{title} {artist}".replace(" ", "+")
            yt_url = f"https://www.youtube.com/results?search_query={query}"
            st.markdown(
                f'<a href="{yt_url}" target="_blank" style="text-decoration:none;">'
                f'<div style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;'
                f'padding:10px 16px;margin:5px 0;display:flex;justify-content:space-between;align-items:center;">'
                f'<div><span style="color:#f0f0f0;font-weight:500;">{html.escape(title)}</span>'
                f'<span style="color:#666;font-size:0.85rem;"> — {html.escape(artist)}</span></div>'
                f'<span style="color:#ff4444;font-size:1.1rem;">▶</span>'
                f'</div></a>',
                unsafe_allow_html=True,
            )
 
    with st.expander("See your mood scores"):
        e_bar = (energy + 16) / 32
        v_bar = (valence + 16) / 32
        s_bar = (social + 16) / 32
        st.write(f"**Energy** {'▓' * int(e_bar * 10)}{'░' * (10 - int(e_bar * 10))} ({energy:+d})")
        st.write(f"**Valence** {'▓' * int(v_bar * 10)}{'░' * (10 - int(v_bar * 10))} ({valence:+d})")
        st.write(f"**Social** {'▓' * int(s_bar * 10)}{'░' * (10 - int(s_bar * 10))} ({social:+d})")
 
    feedback_col1, feedback_col2, feedback_col3 = st.columns(3)
    with feedback_col1:
        if st.button("👍 Matched my vibe"):
            st.session_state.feedback = "Glad it matched!"
            st.rerun()
    with feedback_col2:
        if st.button("😐 Kinda okay"):
            st.session_state.feedback = "Got it, we can improve this."
            st.rerun()
    with feedback_col3:
        if st.button("👎 Not really"):
            st.session_state.feedback = "Let's refine it."
            st.rerun()
 
    if st.session_state.feedback:
        st.caption(st.session_state.feedback)
 
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔁 Try Different Songs"):
        with st.spinner("Finding a different set for the same mood..."):
            fetch_recommendation()
        st.rerun()
 
    if st.button("🔄 Try Again"):
        reset()
        st.rerun()
