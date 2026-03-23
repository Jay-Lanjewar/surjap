import json
import os
import streamlit as st
from google import genai
from dotenv import load_dotenv
from mood_engine import questions, calculate_scores, build_answer_summary
 
load_dotenv()
 
st.set_page_config(
    page_title="Surjap — Music for Your Moment",
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
 
 
def get_recommendation(energy, valence, social, answer_summary):
    api_key = get_gemini_key()
    if not api_key:
        return None, "No API key found. Add GEMINI_API_KEY to your .env file."
 
    try:
        client = genai.Client(api_key=api_key)
 
        prompt = f"""You are a music psychologist and expert recommender specializing in Indian music. A user answered 8 mood questions.
 
Their answers:
{answer_summary}
 
Mood scores (scale roughly -16 to +16):
- Energy: {energy} (negative = low energy, positive = high energy)
- Valence: {valence} (negative = sad/tense, positive = happy/content)
- Social: {social} (negative = wants to be alone, positive = wants connection)
 
Return ONLY a valid JSON object with no extra text, no markdown, no backticks:
 
{{
  "mood_name": "2-3 word evocative mood name",
  "emoji": "one fitting emoji",
  "description": "2 sentences about their current emotional state, speak directly to them",
  "vibe": "one short poetic line about the music vibe",
  "genres": ["genre1", "genre2", "genre3"],
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
- ALL songs must be Indian — Bollywood, Hindi indie, Punjabi pop, or regional Indian music only. No western/international songs.
- Pick songs that are popular and well known in India, that a typical Indian teenager or young adult would recognise and love.
- Examples of good artists: Arijit Singh, Pritam, AP Dhillon, Diljit Dosanjh, Nucleya, When Chai Met Toast, The Local Train, Prateek Kuhad, Ritviz, Anuv Jain, Darshan Raval, B Praak, Jubin Nautiyal, Shreya Ghoshal, Tanishka bahl.
- Match the mood axes precisely — don't recommend upbeat songs for low valence scores.
- Songs must actually exist on YouTube.
- Genres should also be Indian — e.g. Bollywood, Hindi Indie, Punjabi Pop, Sufi, Lo-fi Hindi, etc.
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
 
    except Exception as e:
        return None, f"Error from Gemini: {str(e)}"
 
 
def init_state():
    if "step" not in st.session_state:
        st.session_state.step = 0
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "result" not in st.session_state:
        st.session_state.result = None
    if "error" not in st.session_state:
        st.session_state.error = None
 
 
def reset():
    st.session_state.step = 0
    st.session_state.answers = {}
    st.session_state.result = None
    st.session_state.error = None
 
 
init_state()
 
st.markdown('<p class="main-title">Surjap 🎵</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Answer 8 questions. Get music that fits your moment.</p>', unsafe_allow_html=True)
 
total = len(questions)
 
if st.session_state.result is None and st.session_state.error is None:
    step = st.session_state.step
 
    if step < total:
        q = questions[step]
        st.markdown(f'<p class="progress-text">Question {step + 1} of {total}</p>', unsafe_allow_html=True)
        st.progress(step / total)
        st.markdown(f'<p class="question-text">{q["text"]}</p>', unsafe_allow_html=True)
 
        option_labels = [opt["label"] for opt in q["options"]]
        choice = st.radio("", option_labels, key=f"radio_{q['id']}", label_visibility="collapsed")
 
        col1, col2 = st.columns([3, 1])
        with col1:
            btn_label = "Next →" if step < total - 1 else "See My Music 🎵"
            if st.button(btn_label):
                selected_index = option_labels.index(choice)
                st.session_state.answers[q["id"]] = selected_index
                if step < total - 1:
                    st.session_state.step += 1
                else:
                    with st.spinner("Reading your mood..."):
                        energy, valence, social = calculate_scores(st.session_state.answers)
                        summary = build_answer_summary(st.session_state.answers)
                        data, err = get_recommendation(energy, valence, social, summary)
                        if err:
                            st.session_state.error = err
                        else:
                            st.session_state.result = data
                            st.session_state.scores = (energy, valence, social)
                st.rerun()
        with col2:
            if step > 0:
                if st.button("← Back"):
                    st.session_state.step -= 1
                    if questions[step]["id"] in st.session_state.answers:
                        del st.session_state.answers[questions[step]["id"]]
                    st.rerun()
 
elif st.session_state.error:
    st.error(st.session_state.error)
    if st.button("Try Again"):
        reset()
        st.rerun()
 
else:
    profile = st.session_state.result
    energy, valence, social = st.session_state.scores
 
    st.markdown(f"""
    <div class="mood-card">
        <div style="font-size: 3rem;">{profile.get('emoji','🎵')}</div>
        <div class="mood-name">{profile.get('mood_name','Your Mood')}</div>
        <p style="color: #aaa; margin-top: 0.5rem;">{profile.get('description','')}</p>
        <p class="vibe-text">"{profile.get('vibe','')}"</p>
    </div>
    """, unsafe_allow_html=True)
 
    genres = profile.get("genres", [])
    if genres:
        st.markdown("#### 🎧 Genres for you")
        genres_html = " ".join([f'<span class="tag">{g}</span>' for g in genres])
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
                f'<div><span style="color:#f0f0f0;font-weight:500;">{title}</span>'
                f'<span style="color:#666;font-size:0.85rem;"> — {artist}</span></div>'
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
 
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Try Again"):
        reset()
        st.rerun()