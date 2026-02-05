import streamlit as st
import pandas as pd
import os
import plotly.express as px
from dotenv import load_dotenv
from steam_api import get_owned_games
from ai_recommender import AIRecommender
import translations as t

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Steam Library Manager", page_icon="🎮", layout="wide")

# Language & Theme Logic
if "language" not in st.session_state:
    st.session_state["language"] = "ko"
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

# Helper for getting text
def get_text(key_dict):
    return key_dict.get(st.session_state["language"], key_dict["ko"])

# Sidebar: Language & Theme Toggle
st.sidebar.title(t.CONFIG_TITLE[st.session_state["language"]])

col_lang, col_theme = st.sidebar.columns(2)
with col_lang:
    # Dynamic Label Logic
    lang_label = "🇺🇸 English" if st.session_state["language"] == "en" else "🇰🇷 한국어"
    is_english = st.toggle(lang_label, value=(st.session_state["language"] == "en"))
    
    new_lang = "en" if is_english else "ko"
    if new_lang != st.session_state["language"]:
        st.session_state["language"] = new_lang
        st.rerun()

with col_theme:
    # Theme Toggle with Dynamic Label
    theme_label = "🌙 Dark Mode" if st.session_state["theme"] == "dark" else "☀️ Light Mode"
    is_dark = st.toggle(theme_label, value=(st.session_state["theme"] == "dark"))
    
    new_theme = "dark" if is_dark else "light"
    if new_theme != st.session_state["theme"]:
        st.session_state["theme"] = new_theme
        st.rerun()

# Inject Custom CSS for Theme Switching
# Streamlit doesn't support dynamic theme switching natively via Python, 
# so we use CSS variables to override colors on the fly.
if st.session_state["theme"] == "light":
    st.markdown("""
    <style>
        /* Light Mode Overrides */
        [data-testid="stAppViewContainer"] {
            background-color: #ffffff;
            color: #31333F;
        }
        [data-testid="stSidebar"] {
            background-color: #f0f2f6;
        }
        [data-testid="stHeader"] {
            background-color: rgba(255, 255, 255, 0.95);
        }
        .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, span, div, label {
            color: #31333F !important;
        }
        /* Fix Metric Colors in Light Mode */
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
            color: #31333F !important;
        }
    </style>
    """, unsafe_allow_html=True)

# Initialize AI Recommender (lazy load)
@st.cache_resource
def get_ai_recommender(api_key):
    try:
        os.environ["GOOGLE_API_KEY"] = api_key
        return AIRecommender()
    except Exception as e:
        print(f"AI Init Error: {e}")
        return None

# Sidebar Content
env_steam_id = os.getenv("STEAM_ID", "")
steam_id_input = st.sidebar.text_input("Steam ID", value=env_steam_id)

env_steam_key = os.getenv("STEAM_API_KEY")
env_gemini_key = os.getenv("GEMINI_API_KEY")

if env_steam_key:
    if env_gemini_key:
         st.sidebar.caption(get_text(t.KEYS_LOADED_BOTH))
         steam_api_key = env_steam_key
         gemini_api_key = env_gemini_key
    else:
         st.sidebar.caption(get_text(t.KEYS_LOADED_STEAM))
         steam_api_key = env_steam_key
         gemini_api_key = st.sidebar.text_input(get_text(t.INPUT_GEMINI_KEY), type="password")
else:
    steam_api_key = st.sidebar.text_input(get_text(t.INPUT_STEAM_KEY), type="password")
    gemini_api_key = st.sidebar.text_input(get_text(t.INPUT_GEMINI_KEY), type="password")

refresh_btn = st.sidebar.button(get_text(t.REFRESH_BTN))

# Main UI
st.title(get_text(t.TITLE))
st.markdown(get_text(t.SUBTITLE))

# Reset Logic
if refresh_btn:
    if "games_data" in st.session_state:
        del st.session_state["games_data"]
    st.rerun()

# Main Logic
if steam_id_input and steam_api_key:
    os.environ["STEAM_API_KEY"] = steam_api_key
    
    ai = None
    if gemini_api_key:
        ai = get_ai_recommender(gemini_api_key)

    if "games_data" not in st.session_state:
        with st.spinner(get_text(t.LOADING_MSG)):
            try:
                raw_games = get_owned_games(steam_id_input)
                
                if raw_games is None:
                    st.error(get_text(t.NO_API_KEY_STEAM))
                    st.stop()
                
                if not raw_games:
                    st.warning(get_text(t.NO_GAMES_FOUND))
                    st.stop()
                
                df_raw = pd.DataFrame(raw_games)
                
                if "playtime_forever" in df_raw.columns:
                    df_raw["playtime_hours"] = (df_raw["playtime_forever"] / 60).round(1)
                else:
                    df_raw["playtime_hours"] = 0.0
                    
                df_raw = df_raw.sort_values(by="playtime_forever", ascending=False)
                
                if "img_icon_url" in df_raw.columns:
                    df_raw["icon_url"] = df_raw.apply(
                        lambda x: f"http://media.steampowered.com/steamcommunity/public/images/apps/{x['appid']}/{x['img_icon_url']}.jpg", axis=1
                    )
                else:
                    df_raw["icon_url"] = ""

                if "ai_limit" not in st.session_state:
                    st.session_state["ai_limit"] = 50

                games_to_classify = df_raw.head(st.session_state["ai_limit"])
                game_names = games_to_classify["name"].tolist() if "name" in games_to_classify.columns else []
                
                if ai and game_names:
                    with st.spinner(get_text(t.AI_ANALYZING).format(len(game_names))):
                        try:
                            classification_res = ai.classify_games(game_names)
                            classified_list = classification_res.get("games", [])
                            genre_map = {item["game_name"]: item for item in classified_list}
                            
                            def get_ai_metadata(game_name, field):
                                return genre_map.get(game_name, {}).get(field, "Unclassified")
                                
                            df_raw["Genre"] = df_raw["name"].apply(lambda x: get_ai_metadata(x, "genre"))
                            df_raw["Style"] = df_raw["name"].apply(lambda x: get_ai_metadata(x, "play_style"))
                            df_raw["Vibe"] = df_raw["name"].apply(lambda x: get_ai_metadata(x, "vibe"))
                        except Exception as e:
                            st.warning(f"AI Classification partial failure: {e}")
                            df_raw["Genre"] = "Unknown"
                            df_raw["Style"] = "Unknown"
                            df_raw["Vibe"] = "Unknown"
                else:
                    df_raw["Genre"] = "Unknown"
                    df_raw["Style"] = "Unknown"
                    df_raw["Vibe"] = "Unknown"
                
                st.session_state["games_data"] = df_raw

            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
                st.stop()

    if "games_data" in st.session_state:
        df = st.session_state["games_data"]
        
        # 1. Statistics
        st.subheader(f"📊 {get_text(t.STATS_TOTAL_GAMES)}: {len(df)}")
        # No, let's keep original 3-column layout
        # st.subheader("📊 Library Stats")
        c1, c2, c3 = st.columns(3)
        c1.metric(get_text(t.STATS_TOTAL_GAMES), len(df))
        c2.metric(get_text(t.STATS_PLAYTIME), f"{int(df['playtime_hours'].sum())} hrs")
        most_played = df.iloc[0]['name'] if not df.empty else "N/A"
        c3.metric(get_text(t.STATS_MOST_PLAYED), most_played)
        
        # 2. Charts
        if "Genre" in df.columns and not df.empty:
            st.subheader(get_text(t.CHART_TITLE))
            
            df_chart = df[df["Genre"] != "Unknown"]
            df_chart = df_chart[df_chart["Genre"] != "Unclassified"]
            
            if not df_chart.empty:
                genre_counts = df_chart["Genre"].value_counts(normalize=True)
                threshold = 0.03
                mask = genre_counts < threshold
                others_genres = genre_counts[mask].index.tolist()
                
                df_chart["Genre_Visual"] = df_chart["Genre"].apply(lambda x: "Others" if x in others_genres else x)
                
                fig = px.pie(
                    df_chart, 
                    names="Genre_Visual", 
                    title=f"{get_text(t.CHART_TITLE)} (Top {st.session_state['ai_limit']})", 
                    hole=0.4
                )
                fig.update_traces(textposition='outside', textinfo='percent+label')
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough data classified yet.")
        
        # 3. Game Collection Toolbar
        col_header, col_btn1, col_btn2 = st.columns([6, 1.5, 1.5], vertical_alignment="bottom")
        
        with col_header:
            st.subheader(get_text(t.TABLE_TITLE))
        
        with col_btn1:
            if st.session_state['ai_limit'] < 100:
                if st.button(get_text(t.BTN_TOP_100), use_container_width=True):
                    st.session_state["ai_limit"] = 100
                    del st.session_state["games_data"]
                    st.rerun()
        
        with col_btn2:
             if st.session_state['ai_limit'] < len(df):
                 if st.button(get_text(t.BTN_ALL), use_container_width=True):
                    st.session_state["ai_limit"] = len(df)
                    del st.session_state["games_data"]
                    st.rerun()
        
        st.caption(get_text(t.TABLE_CAPTION).format(st.session_state['ai_limit']))

        current_limit = st.session_state["ai_limit"]
        st.dataframe(
            df.head(current_limit)[["name", "playtime_hours", "Genre", "Style", "Vibe"]],
            column_config={
                "name": get_text(t.COL_GAME),
                "playtime_hours": st.column_config.NumberColumn(get_text(t.COL_HOURS), format="%.1f h"),
                "Genre": st.column_config.TextColumn(get_text(t.COL_GENRE)),
                "Style": st.column_config.TextColumn(get_text(t.COL_STYLE)),
                "Vibe": st.column_config.TextColumn(get_text(t.COL_VIBE)),
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        # 4. AI Recommendation Chat
        st.divider()
        st.subheader(get_text(t.CHAT_HEADER))
        st.caption(get_text(t.CHAT_CAPTION))
        
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        user_input = st.chat_input(get_text(t.CHAT_PLACEHOLDER))
        if user_input:
            if not ai:
                st.error(get_text(t.ERR_MISSING_KEY))
            else:
                st.session_state["chat_history"].append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)
                
                with st.chat_message("assistant"):
                    with st.spinner(get_text(t.AI_THINKING)):
                        rec_context = df.head(50).to_string(index=False, columns=["name", "playtime_hours", "Genre", "Style", "Vibe"])
                        # Pass language for appropriate response
                        response_text = ai.get_recommendation(user_input, rec_context, language=st.session_state["language"])
                        
                        st.markdown(response_text)
                        st.session_state["chat_history"].append({"role": "assistant", "content": response_text})

else:
    st.info(get_text(t.INFO_SIDEBAR))
