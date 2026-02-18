import streamlit as st
from notion_client import Client

# ---------------------------
# 1. DATA FETCHING (NOTION)
# ---------------------------

@st.cache_data(show_spinner="Connecting to Notion...")
def get_battle_eligible_films():
    # Fetch secrets directly inside to avoid scope issues
    try:
        token = st.secrets["NOTION_TOKEN"]
        db_id = st.secrets["DATABASE_ID"]
    except KeyError:
        st.error("Missing Notion secrets! Check your Streamlit dashboard.")
        return []

    client = Client(auth=token)
    
    try:
        # Standard query for notion-client v2.0+
        response = client.databases.query(database_id=db_id)
        results = response.get('results', [])
    except Exception as e:
        st.error(f"Notion API Error: {e}")
        return []

    films = []
    for page in results:
        props = page.get('properties', {})
        
        # 1. Check Eligibility (Safe formula parsing)
        eligible_prop = props.get('Battle Eligible', {})
        is_eligible = False
        if eligible_prop.get('type') == 'formula':
            formula = eligible_prop.get('formula', {})
            is_eligible = formula.get('checkbox', False)
        
        if is_eligible:
            # 2. Get Title
            title_data = props.get('Film Title', {}).get('title', [])
            title = title_data[0]['plain_text'] if title_data else "Untitled Film"
            
            # 3. Get Image URL
            img_data = props.get('Default Image', {}).get('files', [])
            img_url = None
            if img_data:
                # Handle both internal Notion files and external URLs
                file_obj = img_data[0]
                img_url = file_obj.get('file', {}).get('url') or file_obj.get('external', {}).get('url')

            films.append({
                "id": page['id'],
                "title": title,
                "image": img_url
            })
            
    return films

# ---------------------------
# 2. SESSION STATE SETUP
# ---------------------------

st.set_page_config(page_title="Film Battle Mode", layout="centered")
st.title("🎬 Film Battle Mode")

# Initialize our "Memory"
if 'ranked_list' not in st.session_state:
    all_films = get_battle_eligible_films()
    if all_films:
        # We start with the first film already "ranked"
        st.session_state.ranked_list = [all_films[0]]
        # Everyone else is waiting in the queue
        st.session_state.unranked_queue = all_films[1:]
    else:
        st.session_state.ranked_list = []
        st.session_state.unranked_queue = []
    
    # Binary Search Pointers
    st.session_state.current_challenger = None
    st.session_state.low = 0
    st.session_state.high = 0

# ---------------------------
# 3. THE BATTLE ENGINE
# ---------------------------

# Check if we have more films to rank
if not st.session_state.unranked_queue and st.session_state.current_challenger is None:
    st.balloons()
    st.success("🏆 All battles complete! See final rankings below.")
else:
    # Get a new challenger from the queue if we don't have one active
    if st.session_state.current_challenger is None and st.session_state.unranked_queue:
        st.session_state.current_challenger = st.session_state.unranked_queue.pop(0)
        st.session_state.low = 0
        st.session_state.high = len(st.session_state.ranked_list) - 1

    # If we are currently placing a challenger
    if st.session_state.current_challenger:
        challenger = st.session_state.current_challenger
        
        # Binary search logic: Keep comparing until low > high
        if st.session_state.low <= st.session_state.high:
            mid = (st.session_state.low + st.session_state.high) // 2
            defender = st.session_state.ranked_list[mid]

            st.write(f"### Battle {len(st.session_state.ranked_list)} of {len(st.session_state.ranked_list) + len(st.session_state.unranked_queue)}")
            st.subheader("Which film is superior?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if challenger['image']: st.image(challenger['image'], use_container_width=True)
                if st.button(f"Option A: {challenger['title']}", key="btn_A", use_container_width=True):
                    # Winner is Challenger: Move high pointer to look at "better" films
                    st.session_state.high = mid - 1
                    st.rerun()

            with col2:
                if defender['image']: st.image(defender['image'], use_container_width=True)
                if st.button(f"Option B: {defender['title']}", key="btn_B", use_container_width=True):
                    # Winner is Defender: Move low pointer to look at "worse" films
                    st.session_state.low = mid + 1
                    st.rerun()
        else:
            # We found the perfect spot! Insert him at 'low'
            st.session_state.ranked_list.insert(st.session_state.low, challenger)
            st.session_state.current_challenger = None
            st.rerun()

# ---------------------------
# 4. LEADERBOARD UI
# ---------------------------

st.divider()
if st.session_state.ranked_list:
    st.header("🏅 Current Leaderboard")
    for i, film in enumerate(st.session_state.ranked_list, 1):
        st.write(f"**{i}.** {film['title']}")

if st.button("Reset All Battles"):
    st.cache_data.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
