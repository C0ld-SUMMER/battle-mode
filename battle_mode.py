import streamlit as st
from notion_client import Client

# ---------------------------
# 1. DATA FETCHING (NOTION)
# ---------------------------

@st.cache_data(show_spinner="Connecting to Notion...")
def get_battle_eligible_films():
    try:
        token = st.secrets["NOTION_TOKEN"]
        db_id = st.secrets["DATABASE_ID"]
        client = Client(auth=token)
        
        # We use the standard query method. 
        # If this fails, we'll catch it and show a helpful message.
        response = client.databases.query(database_id=db_id)
        results = response.get('results', [])
    except Exception as e:
        st.error(f"⚠️ Notion Connection Failed: {e}")
        return None  # Return None so we can distinguish between 'Error' and 'Empty'

    films = []
    for page in results:
        props = page.get('properties', {})
        
        # 1. Check Eligibility (Battle Eligible checkbox/formula)
        is_eligible = False
        eligible_prop = props.get('Battle Eligible', {})
        p_type = eligible_prop.get('type')
        
        if p_type == 'formula':
            is_eligible = eligible_prop.get('formula', {}).get('checkbox', False)
        elif p_type == 'checkbox':
            is_eligible = eligible_prop.get('checkbox', False)
        
        if is_eligible:
            # 2. Get Title (Search common property names if 'Film Title' is missing)
            title_prop = props.get('Film Title', {}) or props.get('Name', {}) or props.get('Title', {})
            title_list = title_prop.get('title', [])
            title = title_list[0]['plain_text'] if title_list else "Untitled Film"
            
            # 3. Get Image URL
            img_data = props.get('Default Image', {}).get('files', [])
            img_url = None
            if img_data:
                file_obj = img_data[0]
                img_url = file_obj.get('file', {}).get('url') or file_obj.get('external', {}).get('url')

            films.append({"id": page['id'], "title": title, "image": img_url})
            
    return films

# ---------------------------
# 2. INITIALIZATION
# ---------------------------

st.set_page_config(page_title="Film Battle Mode", layout="centered")
st.title("🎬 Film Battle Mode")

# Initialize Session State
if 'ranked_list' not in st.session_state:
    all_films = get_battle_eligible_films()
    
    # CRITICAL: If data load failed or is empty, STOP the app here
    if all_films is None:
        st.warning("Could not connect to Notion. Please check your secrets and library versions.")
        st.stop()
    elif len(all_films) == 0:
        st.info("No films found! Ensure 'Battle Eligible' is checked in your Notion database.")
        st.stop()
    elif len(all_films) < 2:
        st.warning("You need at least 2 eligible films to start a battle.")
        st.stop()

    # Setup the tournament
    st.session_state.ranked_list = [all_films[0]]
    st.session_state.unranked_queue = all_films[1:]
    st.session_state.current_challenger = None
    st.session_state.low = 0
    st.session_state.high = 0

# ---------------------------
# 3. THE BATTLE ENGINE
# ---------------------------

# Check if we are finished (Only if we actually have ranked items)
if not st.session_state.unranked_queue and st.session_state.current_challenger is None:
    st.balloons()
    st.success("🏆 All battles complete!")
else:
    # Pick a challenger
    if st.session_state.current_challenger is None and st.session_state.unranked_queue:
        st.session_state.current_challenger = st.session_state.unranked_queue.pop(0)
        st.session_state.low = 0
        st.session_state.high = len(st.session_state.ranked_list) - 1

    if st.session_state.current_challenger:
        challenger = st.session_state.current_challenger
        
        if st.session_state.low <= st.session_state.high:
            mid = (st.session_state.low + st.session_state.high) // 2
            defender = st.session_state.ranked_list[mid]

            st.write(f"### Ranking Film {len(st.session_state.ranked_list) + 1} of {len(st.session_state.ranked_list) + len(st.session_state.unranked_queue) + 1}")
            
            col1, col2 = st.columns(2)
            with col1:
                if challenger['image']: st.image(challenger['image'], use_container_width=True)
                if st.button(f"Better: {challenger['title']}", key="btn_A", use_container_width=True):
                    st.session_state.high = mid - 1
                    st.rerun()
            with col2:
                if defender['image']: st.image(defender['image'], use_container_width=True)
                if st.button(f"Better: {defender['title']}", key="btn_B", use_container_width=True):
                    st.session_state.low = mid + 1
                    st.rerun()
        else:
            # Insert and move to next challenger
            st.session_state.ranked_list.insert(st.session_state.low, challenger)
            st.session_state.current_challenger = None
            st.rerun()

# ---------------------------
# 4. LEADERBOARD
# ---------------------------

st.divider()
st.header("🏅 Current Rankings")
for i, film in enumerate(st.session_state.ranked_list, 1):
    st.write(f"**{i}.** {film['title']}")

if st.button("Full Reset (Reload from Notion)"):
    st.cache_data.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
