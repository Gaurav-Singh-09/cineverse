import html
import os
import random
import re
from datetime import date, datetime
from urllib.parse import quote

import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Use the AI model already saved on this PC instead of contacting Hugging Face
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# =========================================================
# SETTINGS - the only things you may need to touch
# =========================================================
TMDB_API_KEY = "3a5e87df7d87d89d58680baca2dd5361"
REGION = "IN"  # where-to-watch + now playing region (IN, US, GB ...)

# Optional AI "Vibe Search" files (app still works fully without them)
MOVIE_CSV = r"C:\users\gaurav\Downloads\imdb_merged_final.csv"
FAISS_INDEX = r"C:\users\gaurav\Downloads\movie_index.bin"
USE_OLD_INDEX = True  # True = reuse movie_index.bin; False = only use a freshly built one
ROW_SELECTION = "first"
EMBED_MODEL = "all-MiniLM-L6-v2"

# =========================================================
st.set_page_config(
    page_title="CineVerse | Movie Discovery",
    page_icon="🍿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/"
CURRENT_YEAR = date.today().year
PALETTE = ["#FF2E93", "#00E5FF", "#C6FF3D", "#FFB020", "#B388FF"]

_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='500' height='750'>"
    "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
    "<stop offset='0' stop-color='#7B2CFF'/><stop offset='1' stop-color='#FF2E93'/>"
    "</linearGradient></defs><rect width='500' height='750' fill='url(#g)'/>"
    "<text x='250' y='400' font-size='90' text-anchor='middle'>&#127916;</text></svg>"
)
PLACEHOLDER = "data:image/svg+xml;utf8," + quote(_SVG)

# Official TMDB / SVG Logos for Quick-Search Fallback Icons
FALLBACK_LOGOS = {
    "Netflix": f"{IMG}w92/pbpMk2JmcoNnQwx5JGpXngfoWtp.jpg",
    "JioHotstar": f"{IMG}w92/8Gt1iClBlzTeQs8WQm8UrCoIxnQ.jpg",
    "Prime Video": f"{IMG}w92/dQeAar5H991VYporEjUspolDarG.jpg",
    "YouTube": "data:image/svg+xml;utf8," + quote(
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
        "<rect width='100' height='100' rx='22' fill='#FF0000'/>"
        "<polygon points='38,28 38,72 74,50' fill='#FFFFFF'/></svg>"
    ),
    "JioCinema": f"{IMG}w92/tJqmTmQ8jp9WfyaZfApHK8lSywA.jpg",
    "ZEE5": f"{IMG}w92/vPIW5b0ebTLj9bFCZypoBbF8wSl.jpg",
}

CATEGORIES = {
    "Trending today": "/trending/movie/day",
    "Trending this week": "/trending/movie/week",
    "Now playing": "/movie/now_playing",
    "Popular": "/movie/popular",
    "Top rated": "/movie/top_rated",
    "Coming soon": "/movie/upcoming",
}
LANGS = {
    "Any language": "", "English": "en", "Hindi": "hi", "Marathi": "mr", "Tamil": "ta",
    "Telugu": "te", "Malayalam": "ml", "Korean": "ko", "Japanese": "ja",
    "Spanish": "es", "French": "fr",
}
SORTS = {
    "Most popular": "popularity.desc",
    "Highest rated": "vote_average.desc",
    "Newest first": "primary_release_date.desc",
    "Biggest box office": "revenue.desc",
    "Most voted": "vote_count.desc",
}
PERSIST_KEYS = ["cat", "tpage", "d_genres", "d_years", "d_rating", "d_lang",
                "d_sort", "d_all", "d_page", "q_title", "vibe_q", "vibe_n"]

# =========================================================
# STYLE
# =========================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Unbounded:wght@400;600;800&family=Sora:wght@300;400;600&display=swap');

:root{
  --void:#0A0618; --ultra:#7B2CFF; --hot:#FF2E93; --cyan:#00E5FF;
  --lime:#C6FF3D; --amber:#FFB020; --glass:rgba(255,255,255,.06);
  --line:rgba(255,255,255,.13); --soft:#B9AEDB;
}
html, body, .stApp, [class*="css"]{ font-family:'Sora',sans-serif; }
.stApp{
  color:#F4F0FF;
  background:
    radial-gradient(60rem 40rem at 8% -10%, rgba(123,44,255,.50), transparent 60%),
    radial-gradient(50rem 40rem at 100% 0%, rgba(255,46,147,.36), transparent 60%),
    radial-gradient(60rem 50rem at 50% 115%, rgba(0,229,255,.26), transparent 60%),
    #0A0618;
  background-attachment:fixed;
}
#MainMenu, footer{ visibility:hidden; }
header[data-testid="stHeader"]{ background:transparent; height:0; }
.block-container{ max-width:1400px; padding-top:1.4rem; padding-bottom:3rem; }

/* brand */
.brand{
  font-family:'Unbounded',sans-serif; font-weight:800; line-height:1.05;
  font-size:clamp(2.1rem,5.5vw,3.6rem); letter-spacing:-.02em;
  background:linear-gradient(90deg,var(--hot),var(--ultra),var(--cyan),var(--lime),var(--hot));
  background-size:300% 100%; -webkit-background-clip:text; background-clip:text;
  color:transparent; animation:flow 9s linear infinite;
}
@keyframes flow{ to{ background-position:300% 0; } }
.tagline{ color:var(--soft); margin:6px 0 0; font-weight:300; }

/* ticker */
.ticker{ overflow:hidden; white-space:nowrap; margin:18px 0 22px; padding:9px 0;
  border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
.ticker>div{ display:inline-block; padding-left:100%; animation:tick 70s linear infinite;
  font-family:'Unbounded',sans-serif; font-size:.82rem; color:#E7DFFF; }
.ticker i{ color:var(--hot); font-style:normal; margin:0 18px; }
@keyframes tick{ to{ transform:translateX(-100%); } }

/* hero */
.hero{ position:relative; border-radius:28px; overflow:hidden; min-height:440px;
  display:flex; align-items:flex-end; background-size:cover; background-position:center 20%;
  border:1px solid var(--line); box-shadow:0 30px 90px rgba(123,44,255,.38); }
.hero::before{ content:""; position:absolute; inset:0;
  background:linear-gradient(90deg,rgba(10,6,24,.96) 0%,rgba(10,6,24,.6) 55%,rgba(10,6,24,.1) 100%),
              linear-gradient(0deg,rgba(10,6,24,.92),transparent 55%); }
.hero::after{ content:""; position:absolute; inset:0; mix-blend-mode:screen;
  background:linear-gradient(120deg,rgba(255,46,147,.28),rgba(0,229,255,.18)); }
.hero-in{ position:relative; z-index:2; padding:clamp(20px,4vw,56px); max-width:780px; }
.h-title{ font-family:'Unbounded',sans-serif; font-weight:800; line-height:1.05;
  font-size:clamp(1.8rem,4.6vw,3.6rem); margin:10px 0 12px; }
.h-meta{ display:flex; gap:16px; font-weight:600; color:#E7DFFF; margin-bottom:10px; }
.h-ov{ color:#DCD3F7; line-height:1.65; max-width:62ch; margin:0; }

/* chips */
.chip{ display:inline-block; padding:5px 13px; border-radius:999px; font-size:.78rem;
  font-weight:600; margin:0 7px 7px 0; border:1px solid var(--c,#fff);
  color:var(--c,#fff); background:rgba(10,6,24,.55); box-shadow:0 0 14px -4px var(--c,#fff); }
.chip.plain{ --c:#CFC4F5; box-shadow:none; font-weight:400; }

/* unreleased banner */
.unrel-banner{
  display:inline-flex; align-items:center; gap:8px;
  padding:8px 16px; border-radius:12px; margin:8px 0 14px;
  background:linear-gradient(135deg, rgba(255,46,147,.25), rgba(123,44,255,.3));
  border:1px solid var(--hot); color:#fff; font-weight:700; font-size:.9rem;
  box-shadow:0 0 22px rgba(255,46,147,.4);
}
.unrel-under-poster{
  margin: 0 8px 8px; padding: 4px 6px; border-radius: 6px;
  background: rgba(255,46,147,.2); border: 1px solid var(--hot);
  color: #FF2E93; font-size: .7rem; font-weight: 700; text-align: center;
}
.dposter-wrap{ display:flex; flex-direction:column; align-items:center; gap:10px; }
.dposter-unrel{
  width: 240px; max-width: 42vw; padding: 7px 10px; border-radius: 12px;
  background: linear-gradient(90deg, #FF2E93, #7B2CFF); color: #fff;
  font-weight: 700; font-size: .8rem; text-align: center;
  box-shadow: 0 0 20px rgba(255,46,147,.5);
}

/* section headings */
.sec{ font-family:'Unbounded',sans-serif; font-weight:600; font-size:1.1rem;
  margin:36px 0 14px; display:flex; align-items:center; gap:10px; }
.sec::before{ content:""; width:10px; height:26px; border-radius:6px;
  background:linear-gradient(var(--hot),var(--cyan)); }

/* cards with cinematic blur/overlay hover */
.card{ border-radius:18px; overflow:hidden; background:var(--glass);
  border:1px solid var(--line); margin-bottom:4px;
  transition:transform .25s ease, box-shadow .25s ease; }
.card:hover{ transform:translateY(-4px);
  box-shadow:0 0 0 1px var(--hot),0 14px 30px rgba(255,46,147,.25); }
.pwrap{ position:relative; aspect-ratio:2/3; background:#1a1233; overflow:hidden; }
.pwrap img{ width:100%; height:100%; object-fit:cover; display:block; transition:transform 0.3s ease; }
.card:hover .pwrap img { transform: scale(1.05); filter: blur(4px) brightness(0.4); }

/* Hover synopsis overlay card */
.pwrap .synopsis-overlay {
  position: absolute; inset: 0; padding: 14px;
  background: rgba(10, 6, 24, 0.85); backdrop-filter: blur(8px);
  color: #F4F0FF; font-size: 0.78rem; line-height: 1.5;
  display: flex; flex-direction: column; justify-content: center;
  opacity: 0; transition: opacity 0.3s ease; text-align: left;
  overflow-y: auto;
}
.card:hover .synopsis-overlay { opacity: 1; }

.badge{ position:absolute; top:10px; right:10px; padding:2px 10px; border-radius:999px;
  background:rgba(10,6,24,.82); border:2px solid var(--c); color:var(--c);
  font-weight:600; font-size:.8rem; box-shadow:0 0 14px var(--c); z-index:3; }
.ct{ padding:8px 10px 0; font-weight:600; font-size:.85rem; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis; }
.cy{ padding:0 10px 6px; color:var(--soft); font-size:.75rem; }

/* uniform buttons */
.stButton>button{ width:100%; border-radius:10px; border:1px solid var(--line); color:#fff;
  font-weight:600; font-size:0.8rem; padding:6px 10px;
  background:linear-gradient(135deg,rgba(123,44,255,.6),rgba(255,46,147,.6));
  transition:filter .2s, box-shadow .2s, transform .2s; }
.stButton>button p{ color:#fff; }
.stButton>button:hover{ filter:brightness(1.25); border-color:var(--cyan);
  box-shadow:0 0 20px rgba(0,229,255,.4); transform:translateY(-1px); }

/* tabs */
button[data-baseweb="tab"]{ font-family:'Unbounded',sans-serif; font-size:.82rem; color:#CFC4F5; }
button[data-baseweb="tab"][aria-selected="true"]{ color:var(--lime); }
div[data-baseweb="tab-highlight"]{ background:linear-gradient(90deg,var(--hot),var(--cyan)); height:3px; }
div[data-baseweb="tab-border"]{ background:var(--line); }

/* inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
div[data-baseweb="select"]>div{
  background:rgba(255,255,255,.07)!important; color:#fff!important;
  border:1px solid var(--line)!important; border-radius:12px!important; }
[data-testid="stWidgetLabel"] p{ color:#CFC4F5; }

/* detail page */
.dhero{ position:relative; border-radius:28px; overflow:hidden; background-size:cover;
  background-position:center 20%; border:1px solid var(--line);
  box-shadow:0 30px 90px rgba(123,44,255,.4); }
.dhero::before{ content:""; position:absolute; inset:0;
  background:linear-gradient(90deg,rgba(10,6,24,.97),rgba(10,6,24,.78) 50%,rgba(10,6,24,.4)),
              linear-gradient(0deg,rgba(10,6,24,.9),transparent 60%); }
.dhero-in{ position:relative; display:flex; gap:32px; flex-wrap:wrap; align-items:flex-end;
  padding:clamp(18px,3.5vw,44px); }
.dposter{ width:240px; max-width:42vw; border-radius:18px; border:1px solid var(--line);
  box-shadow:0 0 0 2px var(--hot),0 0 50px rgba(255,46,147,.5); display:block; }
.dmeta{ flex:1 1 320px; min-width:260px; }
.d-title{ font-family:'Unbounded',sans-serif; font-weight:800; line-height:1.08;
  font-size:clamp(1.7rem,4vw,3rem); margin:4px 0 8px; }
.d-tag{ color:var(--cyan); font-style:italic; margin-bottom:12px; }
.d-sub{ color:#E7DFFF; font-weight:600; margin-bottom:12px; }
.d-ov{ color:#DCD3F7; line-height:1.7; max-width:70ch; }
.rrow{ display:flex; align-items:center; gap:14px; margin:14px 0; }
.ring{ width:84px; height:84px; border-radius:50%; display:grid; place-items:center;
  position:relative; box-shadow:0 0 28px var(--c);
  background:conic-gradient(var(--c) calc(var(--p) * 1%), rgba(255,255,255,.14) 0); }
.ring::before{ content:""; position:absolute; inset:7px; background:#0A0618; border-radius:50%; }
.ring span{ position:relative; font-family:'Unbounded',sans-serif; font-weight:600; font-size:1.15rem; }
.rtxt b{ display:block; } .rtxt small{ color:var(--soft); }

.facts{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-top:22px; }
.tile{ background:var(--glass); border:1px solid var(--line); border-radius:16px; padding:14px 16px; }
.tile small{ color:#A99ED0; display:block; font-size:.74rem; margin-bottom:3px; }
.tile b{ font-size:1rem; }

.cast{ display:flex; gap:16px; overflow-x:auto; padding:6px 4px 14px; }
.cm{ flex:0 0 116px; text-align:center; }
.cm img{ width:112px; height:112px; border-radius:50%; object-fit:cover;
  border:2px solid var(--hot); box-shadow:0 0 18px rgba(255,46,147,.4); }
.cm b{ display:block; font-size:.8rem; margin-top:8px; }
.cm span{ font-size:.72rem; color:#A99ED0; }

.prov{ display:flex; flex-wrap:wrap; gap:12px; margin:8px 0 16px; }
.prov-logo{
  width:54px; height:54px; border-radius:14px;
  background-size:cover; background-position:center; background-repeat:no-repeat;
  border:1.5px solid var(--line); display:inline-block; text-decoration:none!important;
  box-shadow:0 6px 16px rgba(0,0,0,.45);
  transition:transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}
.prov-logo:hover{
  transform:translateY(-4px) scale(1.1); border-color:var(--cyan);
  box-shadow:0 0 22px rgba(0,229,255,.55);
}

.plabel{ color:var(--soft); font-size:.8rem; margin-top:10px; }
.lnk{ display:inline-block; margin:0 10px 10px 0; padding:8px 16px; border-radius:12px;
  color:#fff!important; text-decoration:none!important; font-weight:600; font-size:.85rem;
  border:1px solid var(--cyan); box-shadow:0 0 16px rgba(0,229,255,.25); }
.lnk:hover{ background:rgba(0,229,255,.18); }
.note{ color:var(--soft); font-size:.74rem; margin-top:30px; text-align:center; }
</style>
"""

# =========================================================
# HELPERS
# =========================================================
def esc(x):
    return html.escape(str(x if x is not None else ""))


def img(path, size="w500"):
    return f"{IMG}{size}{path}" if path else PLACEHOLDER


def rating_color(r):
    if not r:
        return "#8C84AD"
    if r >= 7.5:
        return "#C6FF3D"
    if r >= 6:
        return "#00E5FF"
    if r >= 4.5:
        return "#FFB020"
    return "#FF2E93"


def money(n):
    if not n:
        return "-"
    if n >= 1e9:
        return f"${n / 1e9:.2f}B"
    if n >= 1e6:
        return f"${n / 1e6:.1f}M"
    return f"${n:,.0f}"


def runtime(m):
    return f"{m // 60}h {m % 60}m" if m else ""


def pretty_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        return s or "-"


def get_release_status(release_date_str, status_str=""):
    today = date.today()
    if release_date_str:
        try:
            r_date = datetime.strptime(release_date_str, "%Y-%m-%d").date()
            if r_date > today:
                fmt = r_date.strftime("%d %b %Y")
                return True, f"🚀 Unreleased • {fmt}", f"🚀 Not Released Yet • Releases on {fmt}"
        except Exception:
            pass
    if status_str and status_str.lower() in ("rumored", "planned", "in production", "post production"):
        if release_date_str:
            fmt = pretty_date(release_date_str)
            return True, f"🚀 Unreleased • {fmt}", f"🚀 Not Released Yet ({status_str}) • Expected on {fmt}"
        return True, "🚀 Unreleased (TBA)", f"🚀 Not Released Yet • Status: {status_str} (Release date TBA)"
    if not release_date_str:
        return True, "🚀 Unreleased (TBA)", "🚀 Not Released Yet • Release Date TBA"
    return False, "", f"Released on {pretty_date(release_date_str)}"


def provider_search_url(pname, movie_title, year=""):
    q = quote(f"{movie_title} {year}".strip())
    q_title = quote(movie_title.strip())
    p_low = pname.lower()
    if "youtube" in p_low:
        return f"https://www.youtube.com/results?search_query={q}+full+movie"
    if "jiohotstar" in p_low or "hotstar" in p_low:
        return f"https://www.hotstar.com/in/explore?search_query={q_title}"
    if "jiocinema" in p_low or "jio" in p_low:
        return f"https://www.jiocinema.com/search/{q_title}"
    if "netflix" in p_low:
        return f"https://www.netflix.com/search?q={q_title}"
    if "prime" in p_low or "amazon" in p_low:
        return f"https://www.primevideo.com/search/ref=atv_nb_sr?phrase={q_title}"
    if "zee5" in p_low:
        return f"https://www.zee5.com/search?q={q_title}"
    if "sonyliv" in p_low or "sony" in p_low:
        return f"https://www.sonyliv.com/search?q={q_title}"
    if "apple" in p_low:
        return f"https://tv.apple.com/in/search?term={q_title}"
    if "google play" in p_low:
        return f"https://play.google.com/store/search?q={q_title}&c=movies"
    return f"https://www.google.com/search?q=watch+{q}+on+{quote(pname)}"


def _make_session(use_system_proxy):
    s = requests.Session()
    s.trust_env = use_system_proxy
    retry = Retry(total=3, connect=3, read=3, backoff_factor=0.8,
                  status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


@st.cache_resource
def _sessions():
    return _make_session(True), _make_session(False)


@st.cache_data(ttl=3600, show_spinner=False)
def _tmdb(path, key, items):
    params = dict(items)
    headers = {"User-Agent": "Mozilla/5.0 CineVerse"}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    else:
        params["api_key"] = key
    params.setdefault("language", "en-US")
    normal, direct = _sessions()
    try:
        r = normal.get(API + path, params=params, headers=headers, timeout=(10, 25))
    except (requests.ConnectionError, requests.Timeout):
        r = direct.get(API + path, params=params, headers=headers, timeout=(10, 25))
    r.raise_for_status()
    return r.json()


def tmdb(path, **params):
    clean = tuple(sorted((k, str(v)) for k, v in params.items() if v not in (None, "")))
    try:
        return _tmdb(path, TMDB_API_KEY.strip(), clean)
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        return {"_error": "Invalid TMDB key (401)" if code == 401 else f"TMDB error {code}"}
    except Exception as e:
        return {"_error": f"Network problem ({type(e).__name__}). TMDB could not be reached"}


@st.cache_data(ttl=86400, show_spinner=False)
def _genres(key):
    return _tmdb("/genre/movie/list", key, ())


def genre_map():
    try:
        return {g["id"]: g["name"] for g in _genres(TMDB_API_KEY.strip()).get("genres", [])}
    except Exception:
        return {}


# ----------------------------- state callbacks -----------------------------
def open_movie(mid):
    st.session_state.selected = mid


def close_movie():
    st.session_state.selected = None


def shuffle_hero():
    st.session_state.hero_idx = random.randrange(8)


def surprise():
    data = tmdb("/discover/movie", sort_by="popularity.desc", page=random.randint(1, 15),
                **{"vote_average.gte": 7, "vote_count.gte": 500})
    res = data.get("results", [])
    if res:
        st.session_state.selected = random.choice(res)["id"]


def set_vibe(text):
    st.session_state.vibe_q = text


# ----------------------------- UI pieces -----------------------------
def card_html(m):
    title = esc(m.get("title") or m.get("name") or "Untitled")
    rel_str = m.get("release_date") or ""
    year = esc(rel_str[:4])
    is_unrel, short_unrel, _ = get_release_status(rel_str)
    r = m.get("vote_average") or 0
    label = f"{r:.1f}" if r else "NR"
    unrel_bar = f'<div class="unrel-under-poster">{esc(short_unrel)}</div>' if is_unrel else ""
    
    overview = m.get("overview") or "No summary available."
    if len(overview) > 220:
        overview = overview[:217] + "..."
    
    return (
        '<div class="card"><div class="pwrap">'
        f'<img src="{img(m.get("poster_path"))}" alt="{title}" loading="lazy">'
        f'<div class="synopsis-overlay"><b>{title}</b><br><br>{esc(overview)}</div>'
        f'<span class="badge" style="--c:{rating_color(r)}">{label}</span></div>'
        f'<div class="ct" title="{title}">{title}</div>'
        f'<div class="cy">{year or "TBA"}</div>'
        f'{unrel_bar}</div>'
    )


def grid(movies, prefix, cols=6):
    movies = [m for m in movies if m.get("id")]
    if not movies:
        st.info("Nothing here yet. Try loosening a filter.")
        return
    for i in range(0, len(movies), cols):
        row = st.columns(cols)
        for j, (col, m) in enumerate(zip(row, movies[i:i + cols])):
            with col:
                st.markdown(card_html(m), unsafe_allow_html=True)
                st.button("Details", key=f"{prefix}_{i}_{j}_{m['id']}",
                          on_click=open_movie, args=(m["id"],))


def section(title):
    st.markdown(f'<div class="sec">{esc(title)}</div>', unsafe_allow_html=True)


def certification(d):
    results = (d.get("release_dates") or {}).get("results", [])
    for country in (REGION, "US"):
        for r in results:
            if r.get("iso_3166_1") == country:
                for rd in r.get("release_dates", []):
                    if rd.get("certification"):
                        return rd["certification"]
    return ""


# ----------------------------- AI vibe search (optional) -----------------------------
LOCAL_INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cineverse_index.bin")


@st.cache_resource(show_spinner="Waking up the AI brain...")
def load_ai():
    try:
        import pandas as pd
        import faiss
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        return {"error": f"AI libraries are missing ({e}). Run: pip install sentence-transformers faiss-cpu pandas"}
    if not os.path.exists(MOVIE_CSV):
        return {"error": f"CSV not found at {MOVIE_CSV}"}
    try:
        df = pd.read_csv(MOVIE_CSV)
        model = SentenceTransformer(EMBED_MODEL)
    except Exception as e:
        return {"error": f"Could not load AI files: {e}."}

    dim = model.get_sentence_embedding_dimension()
    cols = {c.lower().replace(" ", "").replace("_", ""): c for c in df.columns}

    def pick(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return None

    votes_col = pick("numvotes", "votes", "votecount")
    index, index_path = None, None
    for path in [LOCAL_INDEX] + ([FAISS_INDEX] if USE_OLD_INDEX else []):
        if not os.path.exists(path):
            continue
        try:
            cand = faiss.read_index(path)
        except Exception:
            continue
        if cand.d != dim:
            continue
        if path == FAISS_INDEX and cand.ntotal < len(df):
            if ROW_SELECTION == "votes" and votes_col:
                df = df.sort_values(votes_col, ascending=False).head(cand.ntotal).reset_index(drop=True)
            else:
                df = df.head(cand.ntotal).reset_index(drop=True)
        if cand.ntotal == len(df):
            index, index_path = cand, path
            break

    title = pick("title", "primarytitle", "movietitle", "name", "seriestitle", "originaltitle")
    text_cols = list(dict.fromkeys(c for c in (
        title, pick("genres", "genre"),
        pick("overview", "plot", "description", "storyline", "summary"),
        pick("tagline"), pick("keywords"), pick("director", "directors"),
        pick("cast", "stars", "actors")) if c))
    return {
        "df": df, "index": index, "index_path": index_path, "model": model, "faiss": faiss,
        "title": title,
        "year": pick("year", "startyear", "releaseyear", "releasedate"),
        "tmdb": pick("tmdbid", "tmdb"),
        "rating": pick("rating", "averagerating", "imdbrating", "voteaverage", "score"),
        "votes": pick("numvotes", "votes", "votecount"),
        "alt": pick("alternatetitles", "alttitles", "akas"),
        "overview": pick("overview", "plot", "description", "storyline", "summary"),
        "genres": pick("genres", "genre"),
        "poster": pick("posterpath", "poster", "posterurl", "image", "imageurl"),
        "text_cols": text_cols,
    }


def ai_search(query, k):
    ai = load_ai()
    if ai.get("error"):
        return None, ai["error"]
    if not ai["title"]:
        return None, "Could not find a title column in your CSV."
    if ai["index"] is None:
        return None, "No trusted search index yet."
    faiss = ai["faiss"]
    normalize = ai["index"].metric_type == faiss.METRIC_INNER_PRODUCT
    vec = ai["model"].encode([query], normalize_embeddings=normalize).astype("float32")
    _, ids = ai["index"].search(vec, k)
    df, found, seen = ai["df"], [], set()
    for i in ids[0]:
        if i < 0 or i >= len(df):
            continue
        row = df.iloc[int(i)]
        movie = None
        if ai["tmdb"]:
            try:
                d = tmdb(f"/movie/{int(row[ai['tmdb']])}")
                movie = d if d.get("id") else None
            except Exception:
                movie = None
        if movie is None:
            title = str(row[ai["title"]]).strip()
            year = ""
            if ai["year"]:
                mt = re.search(r"(19|20)\d{2}", str(row[ai["year"]]))
                year = mt.group(0) if mt else ""
            res = tmdb("/search/movie", query=title, year=year).get("results", [])
            if not res and year:
                res = tmdb("/search/movie", query=title).get("results", [])
            movie = res[0] if res else None
        if movie and movie["id"] not in seen:
            seen.add(movie["id"])
            found.append(movie)
    return found, None


# =========================================================
# DETAIL PAGE
# =========================================================
def detail_view(mid):
    st.button("<  Back to CineVerse", on_click=close_movie, key="back_top")
    d = tmdb(f"/movie/{mid}",
             append_to_response="credits,videos,watch/providers,recommendations,external_ids,release_dates",
             include_video_language="en,hi,null")
    if not d or d.get("_error"):
        st.error(f"Could not load this movie. {d.get('_error', '')}")
        return

    rating = d.get("vote_average") or 0
    col = rating_color(rating)
    rel_date_str = d.get("release_date") or ""
    status_str = d.get("status") or ""
    year = rel_date_str[:4]
    cert = certification(d)

    is_unreleased, short_unrel, release_msg = get_release_status(rel_date_str, status_str)
    unrel_html = f'<div class="unrel-banner">{esc(release_msg)}</div>' if is_unreleased else ""
    poster_under_html = f'<div class="dposter-unrel">{esc(short_unrel)}</div>' if is_unreleased else ""

    chips = "".join(
        f'<span class="chip" style="--c:{PALETTE[i % len(PALETTE)]}">{esc(g["name"])}</span>'
        for i, g in enumerate(d.get("genres", []))
    )
    sub = " &nbsp;|&nbsp; ".join(esc(x) for x in [cert, pretty_date(rel_date_str) if rel_date_str else "TBA", runtime(d.get("runtime"))] if x)
    tagline = f'<div class="d-tag">&ldquo;{esc(d["tagline"])}&rdquo;</div>' if d.get("tagline") else ""
    bg = f"background-image:url('{img(d.get('backdrop_path') or d.get('poster_path'), 'original')}')"

    st.markdown(
        f'<div class="dhero" style="{bg}"><div class="dhero-in">'
        f'<div class="dposter-wrap"><img class="dposter" src="{img(d.get("poster_path"))}" alt="Poster">{poster_under_html}</div>'
        '<div class="dmeta">'
        f'{unrel_html}'
        f'<div class="d-title">{esc(d.get("title"))}</div>{tagline}'
        f'<div class="d-sub">{sub}</div><div>{chips}</div>'
        f'<div class="rrow"><div class="ring" style="--p:{int(round(rating * 10))};--c:{col}">'
        f'<span>{rating:.1f}</span></div>'
        f'<div class="rtxt"><b>{(d.get("vote_count") or 0):,} votes</b><small>TMDB audience score</small></div></div>'
        f'<div class="d-ov">{esc(d.get("overview") or "No synopsis available yet.")}</div>'
        '</div></div></div>',
        unsafe_allow_html=True,
    )

    credits = d.get("credits") or {}
    crew = credits.get("crew", [])

    def names(jobs, n=3):
        out = []
        for c in crew:
            if c.get("job") in jobs and c["name"] not in out:
                out.append(c["name"])
        return ", ".join(out[:n])

    langs = d.get("spoken_languages") or []
    language = langs[0].get("english_name") if langs else (d.get("original_language") or "").upper()
    tiles = [
        ("Release Status", "Not Released Yet" if is_unreleased else "Released"),
        ("Release Date", pretty_date(rel_date_str) if rel_date_str else "TBA"),
        ("Language", language),
        ("Directed by", names({"Director"})),
        ("Written by", names({"Writer", "Screenplay", "Story"})),
        ("Music", names({"Original Music Composer"}, 2)),
        ("Cinematography", names({"Director of Photography"}, 2)),
        ("Budget", money(d.get("budget"))),
        ("Box office", money(d.get("revenue"))),
        ("Popularity", f"{d.get('popularity', 0):.0f}"),
        ("Part of", (d.get("belongs_to_collection") or {}).get("name")),
        ("Studios", ", ".join(c["name"] for c in d.get("production_companies", [])[:2])),
    ]
    st.markdown(
        '<div class="facts">' + "".join(
            f'<div class="tile"><small>{esc(k)}</small><b>{esc(v)}</b></div>'
            for k, v in tiles if v and v != "-"
        ) + "</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 2])
    with left:
        section("Trailer")
        vids = [v for v in (d.get("videos") or {}).get("results", []) if v.get("site") == "YouTube"]
        vids.sort(key=lambda v: (v.get("type") != "Trailer", v.get("type") != "Teaser",
                                   not v.get("official")))
        if vids:
            st.video(f"https://www.youtube.com/watch?v={vids[0]['key']}")
        else:
            st.info("No trailer on TMDB for this one yet.")
    with right:
        section("Where to watch")
        if is_unreleased:
            st.markdown(f'<div class="unrel-banner">🗓️ {esc(release_msg)}</div>', unsafe_allow_html=True)

        prov = ((d.get("watch/providers") or {}).get("results") or {}).get(REGION, {})
        shown = False
        m_title = d.get("title") or ""
        for key, label in (("flatrate", "Stream"), ("free", "Free"), ("rent", "Rent"), ("buy", "Buy")):
            items = prov.get(key, [])
            if items:
                shown = True
                logo_links = []
                for p in items[:8]:
                    pname = p.get("provider_name", "")
                    plogo = img(p.get("logo_path"), "w92")
                    p_url = provider_search_url(pname, m_title, year)
                    logo_links.append(
                        f'<a class="prov-logo" href="{esc(p_url)}" target="_blank" rel="noopener noreferrer" '
                        f'title="Watch on {esc(pname)}" style="background-image:url(\'{plogo}\')">&nbsp;</a>'
                    )
                st.markdown(
                    f'<div class="plabel">{label}</div>'
                    f'<div class="prov">{"".join(logo_links)}</div>',
                    unsafe_allow_html=True,
                )
        if not shown:
            if is_unreleased:
                st.markdown('<div class="plabel">This movie has not been released on streaming platforms yet. Quick search:</div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="plabel">Quick search on streaming platforms:</div>',
                            unsafe_allow_html=True)
            fallback_logos_html = []
            for pname, plogo in FALLBACK_LOGOS.items():
                p_url = provider_search_url(pname, m_title, year)
                fallback_logos_html.append(
                    f'<a class="prov-logo" href="{esc(p_url)}" target="_blank" rel="noopener noreferrer" '
                    f'title="Search on {esc(pname)}" style="background-image:url(\'{plogo}\')">&nbsp;</a>'
                )
            st.markdown(f'<div class="prov">{"".join(fallback_logos_html)}</div>', unsafe_allow_html=True)

        links = []
        imdb = (d.get("external_ids") or {}).get("imdb_id")
        if imdb:
            links.append(("IMDb", f"https://www.imdb.com/title/{imdb}/"))
        links.append(("TMDB", f"https://www.themoviedb.org/movie/{mid}"))
        if d.get("homepage"):
            links.append(("Official site", d["homepage"]))
        st.markdown(
            '<div style="margin-top:14px">' + "".join(
                f'<a class="lnk" href="{esc(u)}" target="_blank" rel="noopener">{esc(n)}</a>'
                for n, u in links) + "</div>"
            '<div class="plabel">Streaming data by JustWatch • Click any logo above to open</div>',
            unsafe_allow_html=True,
        )

    cast = credits.get("cast", [])[:14]
    if cast:
        section("Cast")
        st.markdown(
            '<div class="cast">' + "".join(
                f'<div class="cm"><img src="{img(c.get("profile_path"), "w185")}" alt="{esc(c["name"])}">'
                f'<b>{esc(c["name"])}</b><span>{esc(c.get("character"))}</span></div>' for c in cast
            ) + "</div>",
            unsafe_allow_html=True,
        )

    recs = (d.get("recommendations") or {}).get("results", [])
    if not recs:
        recs = tmdb(f"/movie/{mid}/similar").get("results", [])
    if recs:
        section("If you liked this")
        grid(recs[:12], "rec")


# =========================================================
# OFFLINE MODE
# =========================================================
def diagnose():
    import socket
    out = []
    try:
        ip = socket.gethostbyname("api.themoviedb.org")
        out.append(f"DNS: api.themoviedb.org resolves to {ip}")
        try:
            socket.create_connection((ip, 443), timeout=6).close()
            out.append("Port 443: connects OK")
        except Exception as e:
            out.append(f"Port 443: FAILED ({type(e).__name__})")
    except Exception as e:
        out.append(f"DNS: FAILED ({type(e).__name__})")
    return out


def ai_rows(query, k):
    ai = load_ai()
    faiss = ai["faiss"]
    normalize = ai["index"].metric_type == faiss.METRIC_INNER_PRODUCT
    vec = ai["model"].encode([query], normalize_embeddings=normalize).astype("float32")
    _, ids = ai["index"].search(vec, k)
    df = ai["df"]
    return [df.iloc[int(i)] for i in ids[0] if 0 <= i < len(df)]


def csv_card(ai, row):
    def val(col):
        if not col:
            return ""
        v = row.get(col, "")
        return "" if v != v else str(v)

    title = esc(val(ai["title"]) or "Untitled")
    ym = re.search(r"(19|20)\d{2}", val(ai["year"]))
    year = ym.group(0) if ym else ""
    poster = val(ai["poster"])
    if poster.startswith("/"):
        poster = IMG + "w500" + poster
    elif not poster.startswith("http"):
        poster = PLACEHOLDER
    try:
        r = float(val(ai["rating"]))
    except ValueError:
        r = 0
    label = f"{r:.1f}" if r else "NR"
    is_unrel = int(year) > CURRENT_YEAR if year.isdigit() else False
    unrel_bar = f'<div class="unrel-under-poster">🚀 Not Released Yet • {esc(year)}</div>' if is_unrel else ""
    
    overview = val(ai["overview"]) or "No summary available."
    if len(overview) > 220:
        overview = overview[:217] + "..."

    st.markdown(
        '<div class="card"><div class="pwrap">'
        f'<img src="{esc(poster)}" alt="{title}" loading="lazy">'
        f'<div class="synopsis-overlay"><b>{title}</b><br><br>{esc(overview)}</div>'
        f'<span class="badge" style="--c:{rating_color(r)}">{label}</span></div>'
        f'<div class="ct" title="{title}">{title}</div>'
        f'<div class="cy">{esc(year)}</div>'
        f'{unrel_bar}</div>',
        unsafe_allow_html=True,
    )
    with st.expander("Plot"):
        if is_unrel:
            st.markdown(f'<div class="unrel-banner">🚀 Not Released Yet • Expected in {esc(year)}</div>', unsafe_allow_html=True)
        if val(ai["genres"]):
            st.write(val(ai["genres"]))
        if val(ai["overview"]):
            st.write(val(ai["overview"]))
        st.json({str(k): str(v)[:300] for k, v in row.dropna().items()})


def offline_mode(err):
    st.markdown('<div class="brand">CineVerse</div>'
                '<p class="tagline">Offline mode: TMDB is unreachable, so trailers, cast and streaming info '
                'are switched off. Search still works from your own movie data.</p>',
                unsafe_allow_html=True)
    st.error(err)
    with st.expander("Connection check: what exactly is blocked?", expanded=True):
        for line in diagnose():
            st.write(line)
    st.button("Retry TMDB", key="retry")

    ai = load_ai()
    if ai.get("error"):
        st.warning(ai["error"])
        return
    index_tools(ai)
    if ai["index"] is None:
        return
    section("Find a movie")
    q = st.text_input("Movie title, or describe a mood or plot", key="off_q",
                      placeholder="e.g. Inception, or: heist movie with a clever twist")
    n = st.slider("Results", 5, 25, 10, 5, key="off_n")

    def show_rows(rows):
        for i in range(0, len(rows), 5):
            for c, row in zip(st.columns(5), rows[i:i + 5]):
                with c:
                    try:
                        csv_card(ai, row)
                    except Exception as e:
                        st.error(f"Could not draw a card: {type(e).__name__}: {e}")

    if q.strip():
        df = ai["df"]
        qs = q.strip()
        mask = df[ai["title"]].astype(str).str.contains(qs, case=False, na=False, regex=False)
        if ai["alt"]:
            mask |= df[ai["alt"]].astype(str).str.contains(qs, case=False, na=False, regex=False)
        hits = df[mask]
        if ai["votes"]:
            hits = hits.sort_values(ai["votes"], ascending=False)
        if len(hits):
            section("Exact title matches")
            show_rows([r for _, r in hits.head(10).iterrows()])
        try:
            with st.spinner("Searching by mood and plot..."):
                rows = ai_rows(q.strip(), n)
        except Exception as e:
            st.error(f"Search failed: {type(e).__name__}: {e}")
            return
        section("Similar by mood and plot")
        show_rows(rows)


# =========================================================
# MAIN
# =========================================================
st.session_state.setdefault("selected", None)
st.markdown(CSS, unsafe_allow_html=True)

if "PASTE_YOUR" in TMDB_API_KEY or not TMDB_API_KEY.strip():
    st.markdown('<div class="brand">CineVerse</div>', unsafe_allow_html=True)
    st.warning("Almost there. Open this file, paste your TMDB API key on the "
               "`TMDB_API_KEY = ...` line near the top, save, and refresh this page.")
    st.stop()

probe = tmdb("/trending/movie/day")
if probe.get("_error"):
    st.error(f"Could not reach TMDB: {probe['_error']}")
    st.stop()

FOOTER = ('<div class="note">This product uses the TMDB API but is not endorsed or certified by TMDB.</div>')

if st.session_state.selected:
    for k in PERSIST_KEYS:
        if k in st.session_state:
            st.session_state[k] = st.session_state[k]
    detail_view(st.session_state.selected)
    st.button("<  Back to CineVerse", on_click=close_movie, key="back_bottom")
    st.markdown(FOOTER, unsafe_allow_html=True)
    st.stop()

GENRES = genre_map()
trending = probe.get("results", [])

head_l, head_r = st.columns([5, 1])
with head_l:
    st.markdown('<div class="brand">CineVerse</div>'
                '<p class="tagline">Find your next obsession. Trailers, cast, and where to watch, all in one place.</p>',
                unsafe_allow_html=True)
with head_r:
    st.write("")
    st.button("Surprise me", on_click=surprise, key="surprise")

if trending:
    ticker = "<i>&#10022;</i>".join(esc(m.get("title")) for m in trending[:14])
    st.markdown(f'<div class="ticker"><div>{ticker}<i>&#10022;</i>{ticker}</div></div>',
                unsafe_allow_html=True)

    pool = [m for m in trending[:8] if m.get("backdrop_path")] or trending[:8]
    st.session_state.setdefault("hero_idx", random.randrange(len(pool)))
    hero = pool[st.session_state.hero_idx % len(pool)]
    hr = hero.get("vote_average") or 0
    hero_chips = "".join(
        f'<span class="chip" style="--c:{PALETTE[i % len(PALETTE)]}">{esc(GENRES.get(g, ""))}</span>'
        for i, g in enumerate(hero.get("genre_ids", [])[:3]) if GENRES.get(g)
    )
    overview = hero.get("overview") or ""
    if len(overview) > 280:
        overview = overview[:277].rsplit(" ", 1)[0] + "..."
    hero_bg = f"background-image:url('{img(hero.get('backdrop_path') or hero.get('poster_path'), 'original')}')"
    hero_unrel, _, hero_rel_msg = get_release_status(hero.get("release_date") or "")
    hero_rel_tag = f'<span style="color:#FF2E93">{esc(hero_rel_msg)}</span>' if hero_unrel else f'<span>{esc((hero.get("release_date") or "")[:4])}</span>'
    st.markdown(
        f'<div class="hero" style="{hero_bg}"><div class="hero-in">{hero_chips}'
        f'<div class="h-title">{esc(hero.get("title"))}</div>'
        f'<div class="h-meta"><span style="color:{rating_color(hr)}">&#9733; {hr:.1f}</span>'
        f'{hero_rel_tag}<span>Trending today</span></div>'
        f'<p class="h-ov">{esc(overview)}</p></div></div>',
        unsafe_allow_html=True,
    )
    b1, b2, _ = st.columns([1, 1, 4])
    b1.button("Open details", on_click=open_movie, args=(hero["id"],), key="hero_open")
    b2.button("Next spotlight", on_click=shuffle_hero, key="hero_next")

st.write("")
tab_browse, tab_discover, tab_vibe, tab_search = st.tabs(
    ["Browse", "Discover", "Vibe Search (AI)", "Find a title"]
)

with tab_browse:
    c1, c2 = st.columns([5, 1])
    cat = c1.radio("Collection", list(CATEGORIES), horizontal=True, key="cat",
                    label_visibility="collapsed")
    page = c2.number_input("Page", min_value=1, max_value=20, value=1, step=1, key="tpage")
    data = tmdb(CATEGORIES[cat], page=page, region=REGION)
    grid(data.get("results", [])[:18], "browse")

with tab_discover:
    section("Build your own movie night")
    f1, f2, f3 = st.columns(3)
    sel_genres = f1.multiselect("Genres", list(GENRES.values()), key="d_genres")
    years = f2.slider("Release years", 1950, CURRENT_YEAR + 2, (2000, CURRENT_YEAR + 1), key="d_years")
    min_rating = f3.slider("Minimum rating", 0.0, 10.0, 6.5, 0.5, key="d_rating")
    f4, f5, f6, f7 = st.columns([2, 2, 2, 1])
    lang = f4.selectbox("Language", list(LANGS), key="d_lang")
    sort = f5.selectbox("Sort by", list(SORTS), key="d_sort")
    all_genres = f6.checkbox("Must match every genre", key="d_all")
    dpage = f7.number_input("Page", min_value=1, max_value=50, value=1, step=1, key="d_page")

    name_to_id = {v: k for k, v in GENRES.items()}
    params = {
        "sort_by": SORTS[sort], "include_adult": "false", "page": dpage,
        "primary_release_date.gte": f"{years[0]}-01-01",
        "primary_release_date.lte": f"{years[1]}-12-31",
        "vote_average.gte": min_rating,
        "vote_count.gte": 0 if years[1] > CURRENT_YEAR else (300 if SORTS[sort].startswith("vote_average") else 50),
        "with_original_language": LANGS[lang],
        "with_genres": ("," if all_genres else "|").join(str(name_to_id[g]) for g in sel_genres),
    }
    grid(tmdb("/discover/movie", **params).get("results", [])[:18], "disc")

with tab_vibe:
    section("Describe the mood, we find the movie")
    st.text_input("What are you in the mood for?", key="vibe_q",
                  placeholder="e.g. mind-bending sci-fi with a bittersweet ending")
    ex = st.columns(4)
    examples = ["Heist movie with a clever twist", "Feel-good road trip comedy",
                "Dark psychological thriller", "Space survival against all odds"]
    for col_, text in zip(ex, examples):
        col_.button(text, on_click=set_vibe, args=(text,), key=f"ex_{text}")
    n = st.slider("How many results", 6, 24, 12, 6, key="vibe_n")

    if st.button("Find my movies", key="vibe_go"):
        q = (st.session_state.get("vibe_q") or "").strip()
        if not q:
            st.warning("Type a mood first.")
        else:
            with st.spinner("Scanning the multiverse..."):
                results, err = ai_search(q, n)
                if err:
                    st.session_state.vibe_notice = err
                    results = tmdb("/search/movie", query=q).get("results", [])[:n]
                else:
                    st.session_state.vibe_notice = None
                st.session_state.vibe_results = results

    if st.session_state.get("vibe_notice"):
        st.info(f"AI search is not active: {st.session_state.vibe_notice}\n\n"
                "Showing plain TMDB keyword results instead.")
        _ai = load_ai()
        if not _ai.get("error"):
            index_tools(_ai)
    if st.session_state.get("vibe_results"):
        grid(st.session_state.vibe_results, "vibe")

with tab_search:
    section("Search any movie")
    q = st.text_input("Movie title", key="q_title", placeholder="Interstellar, Dangal, Parasite...")
    if q.strip():
        res = tmdb("/search/movie", query=q.strip(), include_adult="false").get("results", [])
        if res:
            grid(res[:18], "search")
        else:
            st.info("No matches. Check the spelling or try a shorter title.")
    else:
        st.caption("Start typing a title and results appear here.")

st.markdown(FOOTER, unsafe_allow_html=True)