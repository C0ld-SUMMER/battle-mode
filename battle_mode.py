import streamlit as st
from notion_client import Client

# ---------------------------
# 1. THE "PRO" NOTION FETCH
# ---------------------------

@st.cache_data(show_spinner="Fetching competitors...")
def get_battle_eligible_films():
    try:
        # Pulling secrets - no new secrets needed, just using your existing ones
        token = st.secrets["NOTION_TOKEN"]
        db_id = st.secrets["DATABASE_ID"]
        client = Client(auth=token)
        
        # MANUAL REQUEST: This bypasses the 'databases.query' attribute error
        # by calling the endpoint directly.
        response = client.request(
            path=f"databases/{db_id}/query",
            method="POST"
        )
        results = response.get('results', [])
    except Exception as e:
        st.error(f"📡 Notion Connection Error: {e}")
        return None

    films = []
    for page in results:
        props = page.get('properties', {})
        
        # Logic to check if 'Battle Eligible' is checked
        is_eligible = False
        eligible_prop = props.get('Battle Eligible', {})
        p_type = eligible_prop.get('type')
        
        if p_type == 'formula':
            is_eligible = eligible_prop.get('formula', {}).get('checkbox', False)
        elif p_type == 'checkbox':
            is_eligible = eligible_prop.get('checkbox', False)
        
        if is_eligible:
            # Flexible Title Check (handles "Film Title", "Name", or "Title")
            title_prop = props.get('Film Title') or props.get('Name') or props.get('Title')
            title_list = title_prop.get('title', []) if title_prop else []
            title = title_list[0]['plain_text'] if title_list else "Unknown Film"
            
            # Flexible Image Check
            img_data = props.get('Default Image', {}).get('files', [])
            img_url = None
            if img_data:
                file_obj = img_data[0]
                img_url = file_obj.get('file', {}).get('url') or file_obj.get('external', {}).get('url')

            films.append({"id": page['id'], "title": title, "image": img_url})
            
    return films

# ---------------------------
# 2. TOURNAMENT INITIALIZATION
# ---------------------------

st.set_page_config(page_title="Film Rankings", layout="centered")
st.title("🎬 Film Battle Mode")

# We only run this setup ONCE per session
if 'ranked_list' not in st.session_state:
    all_films = get_battle_eligible_films()
    
    # Error Handling for empty/failed data
    if all_films is None:
        st.stop() # Error message already shown in get_battle_eligible_films
    if not all_films:
        st.info("No films found with 'Battle Eligible' checked.")
        st.stop()
    if len(all_films) < 2:
        st.warning("You need at least 2 films to start a battle!")
        st.stop()

    # Start the "Insertion Sort" tournament
    st.session_state.ranked_list = [all_films[0]] # First film is "ranked" by default
    st.session_state.unranked_queue = all_films[1:] # Everyone else is waiting
    st.session_state.current_challenger = None
    st.session_state.low = 0
    st.session_state.high = 0

# ---------------------------
# 3. BATTLE ENGINE (Binary Insertion)
# ---------------------------

# Logic: If queue is empty AND no active challenger, we are done.
is_finished = not st.session_state.unranked_queue and st.session_state.current_challenger is None

if is_finished:
    st.balloons()
    st.success("🏆 Tournament Complete! Here is your definitive ranking:")
else:
    # 1. Get the next challenger from the pile
    if st.session_state.current_challenger is None:
        st.session_state.current_challenger = st.session_state.unranked_queue.pop(0)
        st.session_state.low = 0
        st.session_state.high = len(st.session_state.ranked_list) - 1

    challenger = st.session_state.current_challenger
    
    # 2. Binary Search: Narrow down where they fit in the ranked list
    if st.session_state.low <= st.session_state.high:
        mid = (st.session_state.low + st.session_state.high) // 2
        defender = st.session_state.ranked_list[mid]

        st.subheader("Which film is better?")
        col1, col2 = st.columns(2)
        
        with col1:
            if challenger['image']: st.image(challenger['image'], use_container_width=True)
            if st.button(f"🥇 {challenger['title']}", key="btn_challenger", use_container_width=True):
                # Challenger is better: move 'high' pointer left to check even better films
                st.session_state.high = mid - 1
                st.rerun()

        with col2:
            if defender['image']: st.image(defender['image'], use_container_width=True)
            if st.button(f"🥇 {defender['title']}", key="btn_defender", use_container_width=True):
                # Defender is better: move 'low' pointer right to check worse films
                st.session_state.low = mid + 1
                st.rerun()
    else:
        # 3. Position found! Insert the film and clear for the next challenger
        st.session_state.ranked_list.insert(st.session_state.low, challenger)
        st.session_state.current_challenger = None
        st.rerun()

# ---------------------------
# 4. LEADERBOARD DISPLAY
# ---------------------------

st.divider()
if st.session_state.ranked_list:
    st.header("🏅 Definitive Rankings")
    for i, film in enumerate(st.session_state.ranked_list, 1):
        st.write(f"**{i}.** {film['title']}")

if st.button("Reset & Refresh Data"):
    st.cache_data.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
