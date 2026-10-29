import streamlit as st
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

st.set_page_config(page_title="Cineverse - Movie Recommendation", layout="wide")

@st.cache_resource
def load_data_and_model():
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    index = faiss.read_index("movie_index.bin")
    movies = pd.read_parquet("movies_subset.parquet")
    return model, index, movies

model, index, movies = load_data_and_model()

st.title("?? Cineverse Movie Recommendation Engine")
st.write("Search for movies using exact titles or semantic descriptions!")

query = st.text_input("Enter a movie title or description:", "")

if query:
    exact_matches = movies[movies["primaryTitle"].str.contains(query, case=False, na=False)]
    
    if not exact_matches.empty:
        st.subheader(f"Exact Keyword Matches for '{query}'")
        results = exact_matches[["primaryTitle", "startYear", "genres", "averageRating"]].head(9)
        st.dataframe(results, use_container_width=True)
    else:
        st.subheader(f"FAISS Semantic Matches for '{query}'")
        q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        D, I = index.search(q_emb, 9)
        results = movies.iloc[I[0]].copy()
        results["score"] = D[0]
        st.dataframe(results[["primaryTitle", "startYear", "genres", "averageRating", "score"]], use_container_width=True)

