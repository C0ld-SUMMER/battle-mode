import streamlit as st
from notion_client import Client

# ---------------------------
# 1. THE ROBUST NOTION FETCH
# ---------------------------

@st.cache_data(show_spinner="Fetching competitors from Notion...")
def get_battle_eligible_films(debug_mode=False):
    try:
        token = st.secrets["NOTION_TOKEN"]
        db_id = st.secrets["DATABASE_ID"]
        client = Client(auth=token)
        
        # Using the manual request to avoid the 'DatabasesEndpoint' error
        response = client.request(
            path=f"databases/{db_id}/query",
            method="POST"
        )
        results = response.get('results', [])
    except Exception as e:
        st.error(f"📡 Notion Connection Error: {e}")
        return None

    films = []
    
    if debug_mode and results:
        st.sidebar.write("### Debug: First Item Properties")
        st.sidebar.json(results[0].get('properties', {}))

    for page in results:
        props = page.get('properties', {})
        
        # --- ELIGIBILITY LOGIC ---
        is_eligible = False
        eligible_prop = props.get('Battle Eligible', {})
        p_type = eligible_prop.get('type')
        
        if p_type == 'formula':
            formula_res = eligible_prop.get('formula', {})
            # FIX: Notion Formulas use 'boolean' for checkbox outputs
            is_eligible = formula_res.get('boolean', False) or formula_res.get('checkbox', False)
        elif p_type == 'checkbox':
            is_eligible = eligible_prop.get('checkbox', False)
        
        if is_eligible:
            # --- TITLE PARSING ---
            # Checks 'Film Title', then 'Name', then 'Title'
            title_prop = props.get('Film Title') or props.get('Name') or props.get('Title')
            title_list = title_prop.get('title', []) if title_prop else []
            title = title_list[0]['plain_text'] if title_list else "Unknown Film"
            
            # --- IMAGE PARSING ---
            img_data = props.get('Default Image', {}).get('files', [])
            img_url = None
            if img_data:
                file_obj = img_data[0]
                # Handles both Notion-hosted and externally hosted images
                img_url = file_obj.get('file', {}).get('url') or file_obj.get('external', {}).get('url')

            films.append({
                "id": page['id'],
                "title": title,
                "image": img_url
            })
            
    return films

# ---------------------------
# 2. TOURNAMENT SETUP
# ---------------------------

st.set_page_config(page_title="Film Rankings", layout="centered")
st.title("🎬 Film Battle Mode")

# Optional Debug Toggle
debug = st.sidebar.checkbox("Show Debug Info")

if 'ranked_list' not in st.session_state:
    all_films = get_battle_eligible_films(debug_mode=debug)
    
    if all_films is None:
        st.stop()
    if not all_films:
        st.info("No films found with 'Battle Eligible' checked.")
        if debug:
            st.write("Check the sidebar to see if the property names match your database.")
        st.stop()
    if len(all_films) < 2:
        st.warning(f"Found {len(all_films)} film(s). You need at least 2 to start a battle.")
        st.stop()

    # Initialize Insertion Sort
    st.session_state.ranked_list = [all_films[0]]
    st.session_state.unranked_queue = all_films[1:]
    st.session_state.current_challenger = None
    st.session_state.low = 0
    st.session_state.high = 0

# ---------------------------
# 3. THE BATTLE ENGINE
# ---------------------------

is_finished = not st.session_state.unranked_queue and st.session_state.current_challenger is None

if is_finished:
    st.balloons()
    st.success("🏆 Tournament Complete!")
else:
    # Load next challenger if needed
    if st.session_state.current_challenger is None:
        st.session_state.current_challenger = st.session_state.unranked_queue.pop(0)
        st.session_state.low = 0
        st.session_state.high = len(st.session_state.ranked_list) - 1

    challenger = st.session_state.current_challenger
    
    # Binary Search Progress
    if st.session_state.low <= st.session_state.high:
        mid = (st.session_state.low + st.session_state.high) // 2
        defender = st.session_state.ranked_list[mid]

        st.write(f"**Ranking {len(st.session_state.ranked_list) + 1} of {len(st.session_state.ranked_list) + len(st.session_state.unranked_queue) + 1}**")
        st.subheader("Which is the better film?")
        
        col1, col2 = st.columns(2)
        with col1:
            if challenger['image']: st.image(challenger['image'], use_container_width=True)
            if st.button(f"🥇 {challenger['title']}", key="btn_A", use_container_width=True):
                st.session_state.high = mid - 1
                st.rerun()

        with col2:
            if defender['image']: st.image(defender['image'], use_container_width=True)
            if st.button(f"🥇 {defender['title']}", key="btn_B", use_container_width=True):
                st.session_state.low = mid + 1
                st.rerun()
    else:
        # Placement Found
        st.session_state.ranked_list.insert(st.session_state.low, challenger)
        st.session_state.current_challenger = None
        st.rerun()

# ---------------------------
# 4. LEADERBOARD
# ---------------------------

st.divider()
if st.session_state.ranked_list:
    st.header("🏅 Definitive Rankings")
    for i, film in enumerate(st.session_state.ranked_list, 1):
        st.write(f"**{i}.** {film['title']}")

if st.button("Reset Tournament & Refresh Films"):
    st.cache_data.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
