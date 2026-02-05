import streamlit as st
import pandas as pd
import os
import plotly.express as px
from dotenv import load_dotenv
from steam_api import get_owned_games
from ai_recommender import AIRecommender

# Load environment variables (Friendly for local dev, ignored if file missing on Railway)
load_dotenv()

st.set_page_config(page_title="Steam Library Manager", page_icon="🎮", layout="wide")

# Initialize AI Recommender (lazy load)
@st.cache_resource
def get_ai_recommender(api_key):
    try:
        # Pass the key explicitly to avoid relying solely on env inside the class if not set
        os.environ["GOOGLE_API_KEY"] = api_key
        return AIRecommender()
    except Exception as e:
        print(f"AI Init Error: {e}")
        return None

# Sidebar Configuration
st.sidebar.title("Configuration")

# Steam ID Handling
env_steam_id = os.getenv("STEAM_ID", "")
steam_id_input = st.sidebar.text_input("Steam ID", value=env_steam_id, help="Enter your 17-digit Steam ID")

# API Keys Handling
# Check if keys are present in environment (Railway)
env_steam_key = os.getenv("STEAM_API_KEY")
env_gemini_key = os.getenv("GEMINI_API_KEY")

if env_steam_key:
    st.sidebar.success("✅ Steam API Key Loaded")
    steam_api_key = env_steam_key
else:
    steam_api_key = st.sidebar.text_input("Steam API Key", type="password")

if env_gemini_key:
    st.sidebar.success("✅ Gemini API Key Loaded")
    gemini_api_key = env_gemini_key
else:
    gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password")

refresh_btn = st.sidebar.button("🔄 Refresh Library")

# Main UI
st.title("🎮 Steam Library AI Agent")
st.markdown("Your personal AI game curator powered by Steam & Gemini.")

# Reset Logic
if refresh_btn:
    if "games_data" in st.session_state:
        del st.session_state["games_data"]
    st.rerun()

# Main Logic
if steam_id_input and steam_api_key:
    # Set/Update Env Vars for modules to use
    os.environ["STEAM_API_KEY"] = steam_api_key
    
    # Initialize AI
    ai = None
    if gemini_api_key:
        ai = get_ai_recommender(gemini_api_key)

    if "games_data" not in st.session_state:
        with st.spinner("🚀 Fetching your Steam Library... this might take a moment."):
            try:
                raw_games = get_owned_games(steam_id_input)
                
                if raw_games is None:
                    st.error("❌ Failed to fetch games. Please check your Steam API Key and Steam ID.")
                    st.stop()
                
                if not raw_games:
                    st.warning("⚠️ No games found. Is your Steam Profile public?")
                    st.stop()
                
                # Process Data
                df_raw = pd.DataFrame(raw_games)
                
                # Basic info
                if "playtime_forever" in df_raw.columns:
                    df_raw["playtime_hours"] = (df_raw["playtime_forever"] / 60).round(1)
                else:
                    df_raw["playtime_hours"] = 0.0
                    
                df_raw = df_raw.sort_values(by="playtime_forever", ascending=False)
                
                # Image URL Construction
                # format: http://media.steampowered.com/steamcommunity/public/images/apps/{appid}/{img_icon_url}.jpg
                if "img_icon_url" in df_raw.columns:
                    df_raw["icon_url"] = df_raw.apply(
                        lambda x: f"http://media.steampowered.com/steamcommunity/public/images/apps/{x['appid']}/{x['img_icon_url']}.jpg", axis=1
                    )
                else:
                    df_raw["icon_url"] = ""

                # AI Classification (Top 30 to save time/tokens)
                top_games = df_raw.head(30)
                game_names = top_games["name"].tolist() if "name" in top_games.columns else []
                
                if ai and game_names:
                    with st.spinner("🤖 AI is analyzing your library genres..."):
                        try:
                            classification_res = ai.classify_games(game_names)
                            classified_list = classification_res.get("games", [])
                            
                            # Dictionary for fast lookup
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

    # Dashboard Display
    if "games_data" in st.session_state:
        df = st.session_state["games_data"]
        
        # 1. Statistics
        st.subheader("📊 Library Stats")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Games", len(df))
        c2.metric("Total Playtime", f"{int(df['playtime_hours'].sum())} hrs")
        most_played = df.iloc[0]['name'] if not df.empty else "N/A"
        c3.metric("Most Played", most_played)
        
        # 2. Charts
        if "Genre" in df.columns and not df.empty:
            df_chart = df[df["Genre"] != "Unknown"]
            if not df_chart.empty:
                fig = px.pie(df_chart, names="Genre", title="Your Genre Preference (Top 30)", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        
        # 3. Game Table
        st.subheader("📚 Game Collection")
        st.dataframe(
            df[["name", "playtime_hours", "Genre", "Style", "Vibe"]],
            column_config={
                "name": "Game",
                "playtime_hours": st.column_config.NumberColumn("Hours", format="%.1f h"),
                "Genre": st.column_config.TextColumn("Genre"),
                "Style": st.column_config.TextColumn("Style"),
                "Vibe": st.column_config.TextColumn("Vibe"),
            },
            hide_index=True,
            use_container_width=True,
            height=300
        )
        
        # 4. AI Recommendation Chat
        st.divider()
        st.subheader("💡 AI Game Recommender")
        st.caption("Ask anything like: 'I want a short relaxing game' or 'Something to play with friends'")
        
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        # Display history
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        user_input = st.chat_input("Ask for a recommendation...")
        if user_input:
            if not ai:
                st.error("⚠️ Gemini API Key is missing. Please check configuration.")
            else:
                # Add user message
                st.session_state["chat_history"].append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)
                
                # Generate response
                with st.chat_message("assistant"):
                    with st.spinner("AI is thinking..."):
                        # Context: Top 50 games for recommendation context
                        rec_context = df.head(50).to_string(index=False, columns=["name", "playtime_hours", "Genre", "Style", "Vibe"])
                        response_text = ai.get_recommendation(user_input, rec_context)
                        
                        st.markdown(response_text)
                        st.session_state["chat_history"].append({"role": "assistant", "content": response_text})

else:
    st.info("👈 Please configure your Steam ID and API Keys in the sidebar to begin.")
