# battle_mode.py

import streamlit as st
from notion_client import Client
import pandas as pd

# ---------------------------
# CONFIGURATION
# ---------------------------

# Load your Notion credentials from Streamlit secrets
NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
DATABASE_ID = st.secrets["DATABASE_ID"]

# Initialize Notion client
notion = Client(auth=NOTION_TOKEN)

# ---------------------------
# PULL DATA FROM NOTION
# ---------------------------

def get_battle_eligible_films():
    results = notion.databases.query(database_id=DATABASE_ID)
    
    films = []
    for page in results['results']:
        prop = page['properties'].get('Battle Eligible')
        battle_eligible = False

        if prop and prop['type'] == 'formula':
            formula_output = prop['formula']
            if 'checkbox' in formula_output:
                battle_eligible = formula_output['checkbox']
            elif 'string' in formula_output:
                battle_eligible = formula_output['string'] == "True"
            elif 'number' in formula_output:
                battle_eligible = bool(formula_output['number'])

        if battle_eligible:
            # Safe title extraction
            title_data = page['properties']['Film Title']['title']
            if title_data:
                title = title_data[0]['text']['content']
            else:
                title = "Untitled"

            # Safe image extraction
            file_data = page['properties']['Default Image']['files']
            if file_data:
                image = file_data[0]['file']['url']
            else:
                image = None
            
            page_id = page['id']def get_battle_eligible_films():
    results = notion.databases.query(database_id=DATABASE_ID)
    
    films = []
    for page in results['results']:
        prop = page['properties'].get('Battle Eligible')
        battle_eligible = False

        # Safe formula checkbox access
        if prop and prop.get('type') == 'formula':
            formula_output = prop.get('formula', {})
            battle_eligible = formula_output.get('checkbox', False)

        if battle_eligible:
            # Safe access to Film Title
            title_prop = page['properties'].get('Film Title', {}).get('title', [])
            title = title_prop[0]['text']['content'] if title_prop else "Untitled"

            # Safe access to Default Image
            files = page['properties'].get('Default Image', {}).get('files', [])
            image = files[0]['file']['url'] if files else None

            page_id = page.get('id')

            films.append({
                "id": page_id,
                "title": title,
                "image": image
            })
    
    return films
            
# Pull eligible films
films = get_battle_eligible_films()
# ---------------------------
# BATTLE LOGIC
# ---------------------------

# Initialize rankings
ranking = []

# Copy of films to track battles
battle_pool = films.copy()

# Function to process a battle
def run_battle(left, right):
    st.write(f"**{left['title']}** vs **{right['title']}**")
    col1, col2 = st.columns(2)
    
    winner = None
    with col1:
        if st.button(left['title'], key=f"{left['id']}_vs_{right['id']}"):
            winner = left
    with col2:
        if st.button(right['title'], key=f"{right['id']}_vs_{left['id']}"):
            winner = right
    
    return winner
# ---------------------------
# STREAMLIT UI
# ---------------------------

st.title("Battle Mode")

if len(films) < 2:
    st.warning("Not enough films to run battles!")
else:
    while len(battle_pool) > 1:
        left = battle_pool.pop(0)
        right = battle_pool.pop(0)
        
        winner = run_battle(left, right)
        
        if winner:
            ranking.append(winner)
            battle_pool.insert(0, winner) # Winner stays for next battle
        else:
            # Wait for user to click a button
            break

# Display final ranking
if ranking:
    st.subheader("Current Battle Rankings")
    for i, film in enumerate(ranking, 1):
        st.write(f"{i}. {film['title']}")
