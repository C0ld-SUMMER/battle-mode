import streamlit as st
from notion_client import Client

# ---------------------------
# 1. SETUP & NOTION DATA
# ---------------------------

NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
DATABASE_ID = st.secrets["DATABASE_ID"]

@st.cache_data(show_spinner="Fetching films from Notion...")
def get_battle_eligible_films():
    notion = Client(auth=NOTION_TOKEN)
    results = notion.databases.query(database_id=DATABASE_ID)
    films = []

    for page in results['results']:
        props = page['properties']
        
        # Check Battle Eligibility (Formula Checkbox)
        battle_eligible = False
        prop = props.get('Battle Eligible', {})
        if prop.get('type') == 'formula':
            formula_output = prop.get('formula', {})
            battle_eligible = formula_output.get('checkbox', False)

        if battle_eligible:
            # Title
            title_prop = props.get('Film Title', {}).get('title', [])
            title = title_prop[0]['text']['content'] if title_prop else "Untitled"
            
            # Image
            files = props.get('Default Image', {}).get('files', [])
            image = files[0]['file']['url'] if files else None

            films.append({
                "id": page.get('id'),
                "title": title,
                "image": image
            })
    return films

# ---------------------------
# 2. SESSION STATE (The Memory)
# ---------------------------

if 'unranked' not in st.session_state:
    all_films = get_battle_eligible_films()
    if all_films:
        st.session_state.unranked = all_films[1:]  # Everyone else
        st.session_state.ranked_list = [all_films[0]]  # Start with 1 ranked film
    else:
        st.session_state.unranked = []
        st.session_state.ranked_list = []
    
    # Binary Search Pointers
    st.session_state.low = 0
    st.session_state.high = 0
    st.session_state.current_challenger = None

# ---------------------------
# 3. BATTLE LOGIC
# ---------------------------

st.title("🎬 Film Ranking Battle")

if not st.session_state.ranked_list:
    st.warning("No films found in your Notion database.")
elif not st.session_state.unranked and st.session_state.current_challenger is None:
    st.success("🎉 All films have been ranked!")
else:
    # 1. Pick a new challenger if we don't have one
    if st.session_state.current_challenger is None and st.session_state.unranked:
        st.session_state.current_challenger = st.session_state.unranked.pop(0)
        st.session_state.low = 0
        st.session_state.high = len(st.session_state.ranked_list) - 1

    # 2. If we have a challenger, find their spot using binary search
    if st.session_state.current_challenger:
        challenger = st.session_state.current_challenger
        
        if st.session_state.low <= st.session_state.high:
            mid = (st.session_state.low + st.session_state.high) // 2
            comparison_film = st.session_state.ranked_list[mid]

            st.subheader(f"Battle: Who is better?")
            col1, col2 = st.columns(2)

            with col1:
                if challenger['image']: st.image(challenger['image'], use_container_width=True)
                if st.button(f"🏆 {challenger['title']}", key="btn_challenger", use_container_width=True):
                    # Challenger is BETTER than mid: look in the "upper" half
                    st.session_state.high = mid - 1
                    st.rerun()

            with col2:
                if comparison_film['image']: st.image(comparison_film['image'], use_container_width=True)
                if st.button(f"🏆 {comparison_film['title']}", key="btn_mid", use_container_width=True):
                    # Challenger is WORSE than mid: look in the "lower" half
                    st.session_state.low = mid + 1
                    st.rerun()
        else:
            # 3. Spot found! Insert challenger at 'low' index
            st.session_state.ranked_list.insert(st.session_state.low, challenger)
            st.session_state.current_challenger = None
            st.rerun()

# ---------------------------
# 4. LEADERBOARD UI
# ---------------------------

st.divider()
if st.session_state.ranked_list:
    st.sidebar.header("Current Rankings")
    for i, film in enumerate(st.session_state.ranked_list, 1):
        st.sidebar.write(f"**{i}.** {film['title']}")

if st.sidebar.button("Reset Tournament"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
