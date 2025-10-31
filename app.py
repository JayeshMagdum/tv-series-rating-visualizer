import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import time
from matplotlib.patches import Patch
from tqdm.notebook import tqdm
import plotly.express as px

# -----------------
# Put your OMDb API key here
OMDB_API_KEY = "c82d4fa6"

st.title("TV Series Episode Ratings Heatmap (OMDb)")

# User input for series
series_name = st.text_input("Enter TV Series Name:", "Game of Thrones")

# Fetch button
if st.button("Fetch & Show Heatmap"):
    
    @st.cache_data  # caches results to avoid repeated API calls
    def fetch_season(series_title, season_num, api_key=OMDB_API_KEY, timeout=10):
        params = {"t": series_title, "Season": season_num, "apikey": api_key}
        try:
            r = requests.get("http://www.omdbapi.com/", params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            if data.get("Response", "False") == "True" and "Episodes" in data:
                return data
            else:
                return None
        except Exception as e:
            st.warning(f"Error fetching {series_title} S{season_num}: {e}")
            return None

    @st.cache_data
    def fetch_all_seasons(series_title, api_key=OMDB_API_KEY, max_seasons=50, delay=0.5):
        records = []
        for s in range(1, max_seasons + 1):
            data = fetch_season(series_title, s, api_key)
            if not data:
                break
            for ep in data.get("Episodes", []):
                rating = ep.get("imdbRating")
                rating_val = float(rating) if rating and rating != "N/A" else np.nan
                votes = ep.get("imdbVotes")
                records.append({
                    "series": series_title,
                    "season": int(s),
                    "episode": int(ep.get("Episode", 0)),
                    "title": ep.get("Title"),
                    "imdbRating": rating_val,
                    "imdbVotes": votes
                })
            time.sleep(delay)
        return pd.DataFrame(records)

    # Fetch the data
    df_eps = fetch_all_seasons(series_name)
    
    if df_eps.empty:
        st.warning("No data found. Check series name or API key.")
    else:
        st.success(f"Fetched {len(df_eps)} episodes!")

        # Pivot
        pivot = df_eps.pivot(index='episode', columns='season', values='imdbRating')

        # Rating categories
        def rating_category(r):
            if pd.isna(r): return "NoData"
            if r >= 9.0: return "Awesome"
            if r >= 8.0: return "Great"
            if r >= 7.0: return "Good"
            if r >= 6.0: return "Regular"
            if r >= 5.0: return "Bad"
            return "Garbage"

        categories = ["Awesome","Great","Good","Regular","Bad","Garbage","NoData"]
        colors = {
            "Awesome": "#006400", "Great":"#2E8B57", "Good":"#9ACD32",
            "Regular":"#FFDA6B","Bad":"#FF6B6B","Garbage":"#6B1B1B","NoData":"#EEEEEE"
        }
        cat_grid = pivot.applymap(rating_category)

        # ------------------------
        # Matplotlib heatmap
        fig, ax = plt.subplots(figsize=(1.6 * max(4, pivot.shape[1]), 0.9 * max(6, pivot.shape[0])))
        for i, epi in enumerate(cat_grid.index):
            for j, seas in enumerate(cat_grid.columns):
                cat = cat_grid.loc[epi, seas]
                face = colors.get(cat, "#FFFFFF")
                ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=face, edgecolor='white'))
                val = pivot.loc[epi, seas]
                if not pd.isna(val):
                    ax.text(j+0.5, i+0.5, f"{val:.1f}", ha='center', va='center', fontsize=10)

        ax.set_xticks(np.arange(len(pivot.columns))+0.5)
        ax.set_xticklabels(pivot.columns, rotation=0)
        ax.set_yticks(np.arange(len(pivot.index))+0.5)
        ax.set_yticklabels(pivot.index, rotation=0)
        ax.set_xlabel("Season")
        ax.set_ylabel("Episode")
        ax.set_title(f"{series_name} — Episode Ratings Heatmap")
        ax.invert_yaxis()
        ax.set_xlim(0, len(pivot.columns))
        ax.set_ylim(0, len(pivot.index))

        legend_handles = [Patch(facecolor=colors[c], label=c) for c in categories]
        ax.legend(handles=legend_handles, bbox_to_anchor=(1.02,1), loc='upper left')
        plt.tight_layout()

        st.pyplot(fig)

        # ------------------------
        # Optional Plotly interactive heatmap
        df_plotly = df_eps.copy()
        df_plotly['rating_text'] = df_plotly['imdbRating'].apply(lambda x: f"{x:.1f}" if not pd.isna(x) else "N/A")
        fig_p = px.density_heatmap(df_plotly, x='season', y='episode', z='imdbRating',
                                   hover_data=['title','imdbRating'], color_continuous_scale='RdYlGn',
                                   nbinsx=len(df_plotly['season'].unique()),
                                   title=f"{series_name} Episode Ratings (Interactive)")
        fig_p.update_yaxes(autorange='reversed')
        st.plotly_chart(fig_p)



