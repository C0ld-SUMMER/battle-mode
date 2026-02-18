import streamlit as st
from notion_client import Client

# ---------------------------
# 1. THE "PRO" NOTION TOOLS
# ---------------------------

def get_client():
    return Client(auth=st.secrets["NOTION_TOKEN"])

@st.cache_data(show_spinner="Fetching competitors...")
def get_battle_eligible_films():
    try:
        client = get_client()
        db_id = st.secrets["DATABASE_ID"]
        # Direct request to bypass library attribute errors
        response = client.request(path=f"databases/{db_id}/query", method="POST")
        results = response.get('results', [])
    except Exception as e:
        st.error(f"📡 Connection Error: {e}")
        return None

    films = []
    for page in results:
        props = page.get('properties', {})
        
        # Eligibility Check (Formulas vs Checkboxes)
        eligible_prop = props.get('Battle Eligible', {})
        p_type = eligible_prop.get('type')
        is_eligible = False
        
        if p_type == 'formula':
            formula_res = eligible_prop.get('formula', {})
            is_eligible = formula_res.get('boolean', False) or formula_res.get('checkbox', False)
        elif p_type == 'checkbox':
            is_eligible = eligible_prop.get('checkbox', False)
        
        if is_eligible:
            title_prop = props.get('Film Title') or props.get('Name') or props.get('Title')
            title = title_prop.get('title', [{}])[0].get('plain_text', 'Unknown')
            
            img_data = props.get('Default Image', {}).get('files', [])
            img_url = None
            if img_data:
                file_obj = img_data[0]
                img_url = file_obj.get('file', {}).get('url') or file_obj.get('external', {}).get('url')

            films.append({"id": page['id'], "title": title, "image": img_url})
    return films

def sync_all_ranks_to_notion(ranked_list):
    """Updates the 'Rank' property for every film in the list."""
    client = get_client()
    for index, film in enumerate(ranked_list, 1):
        try:
            client.pages.update(
                page_id=film['id'],
                properties={
                    "Rank": {"number": index}
                }
            )
        except Exception as e:
            st.error(f"Failed to sync {film['title']}: {e}")

# ---------------------------
# 2. UI & INITIALIZATION
# ---------------------------

# Wide layout looks better when embedded in Notion columns
st.set_page_config(page_title="Film Battle", layout="wide") 
st.title("🎬 Film Battle Mode")

if 'ranked_list' not in st.session_state:
    all_films = get_battle_eligible_films()
    if all_films is None or not all_films:
        st.info("No eligible films found. Check your Notion 'Battle Eligible' column!")
        st.stop()
    
    st.session_state.ranked_list = [all_films[0]]
    st.session_state.unranked_queue = all_films[1:]
    st.session_state.current_challenger = None
    st.session_state.low = 0
    st.session_state.high = 0

# ---------------------------
# 3. BATTLE ENGINE
# ---------------------------

is_finished = not st.session_state.unranked_queue and st.session_state.current_challenger is None

if is_finished:
    st.balloons()
    st.success("🏆 All Ranks Synced to Notion!")
else:
    if st.session_state.current_challenger is None:
        st.session_state.current_challenger = st.session_state.unranked_queue.pop(0)
        st.session_state.low = 0
        st.session_state.high = len(st.session_state.ranked_list) - 1

    challenger = st.session_state.current_challenger
    
    if st.session_state.low <= st.session_state.high:
        mid = (st.session_state.low + st.session_state.high) // 2
        defender = st.session_state.ranked_list[mid]

        st.write(f"**Ranking {len(st.session_state.ranked_list) + 1} of {len(st.session_state.ranked_list) + len(st.session_state.unranked_queue) + 1}**")
        
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
        # PLACEMENT FOUND
        st.session_state.ranked_list.insert(st.session_state.low, challenger)
        st.session_state.current_challenger = None
        
        # AUTO-SYNC: Update Notion whenever a new film is placed
        with st.spinner("Syncing ranks to Notion..."):
            sync_all_ranks_to_notion(st.session_state.ranked_list)
        st.rerun()

# ---------------------------
# 4. SIDEBAR RANKINGS
# ---------------------------

with st.sidebar:
    st.header("🏅 Leaderboard")
    for i, film in enumerate(st.session_state.ranked_list, 1):
        st.write(f"{i}. {film['title']}")
    
    if st.button("Reset Tournament"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
