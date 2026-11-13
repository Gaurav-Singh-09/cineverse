# 🎬 Cineverse — Semantic Movie Recommendation Engine

An interactive **Streamlit** application powered by **SentenceTransformers** and **FAISS** vector search that delivers hybrid movie discovery—combining instant exact-title matching with dense semantic similarity search.

---

## ✨ Key Features

- **Hybrid Search Architecture:** Automatically checks for case-insensitive exact title matches first; if none are found, falls back seamlessly to dense vector similarity search.
- **Semantic Natural-Language Queries:** Search by plot themes, moods, or descriptions (e.g., *"mind-bending sci-fi about dreams"*) using `all-MiniLM-L6-v2` embeddings.
- **Sub-Millisecond Vector Retrieval:** Uses a pre-built **FAISS** index (`movie_index.bin`) with normalized embeddings to surface the top 9 most relevant titles alongside cosine similarity scores.
- **Fast Columnar Data Loading:** Reads movie metadata (`primaryTitle`, `startYear`, `genres`, `averageRating`) efficiently from Apache Parquet (`movies_subset.parquet`) with Streamlit resource caching (`@st.cache_resource`).
- **Git LFS Ready:** Configured via `.gitattributes` to track large binary index and Parquet artifacts cleanly.

---

## 🛠️ Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io/)
- **Embeddings:** [SentenceTransformers](https://www.sbert.net/) (`sentence-transformers/all-MiniLM-L6-v2`)
- **Vector Search:** [FAISS](https://github.com/facebookresearch/faiss) (`faiss-cpu`)
- **Data Storage & Processing:** [Pandas](https://pandas.pydata.org/), [PyArrow](https://arrow.apache.org/docs/python/), [NumPy](https://numpy.org/)

---

## 📁 Project Structure

```text
├── app.py                  # Main Streamlit application
├── movie_index.bin         # Pre-computed FAISS vector index (Git LFS)
├── movies_subset.parquet   # Movie metadata dataset (Git LFS)
├── .gitattributes          # Git LFS tracking configuration
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
