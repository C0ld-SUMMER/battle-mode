# battle_mode.py

import streamlit as st
from notion_client import Client
import pandas as pd

# ---------------------------
# CONFIGURATION
# ---------------------------

# Placeholder for your Notion integration token
NOTION_TOKEN = "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"

# Replace this with your database ID from Notion
DATABASE_ID = "Explore The Main Films"

# Initialize Notion client
notion = Client(auth=NOTION_TOKEN)

# ---------------------------
# PULL DATA FROM NOTION
# ---------------------------

def get_battle_eligible_films():
    results = notion.databases.query(
        **{
            "database_id": DATABASE_ID,
            "filter": {
                "property": "Battle Eligible",
                "checkbox": {"equals": True}
            }
        }
    )
    
    films = []
    for page in results['results']:
        title = page['properties']['Film Title']['title'][0]['text']['content'] if page['properties']['Film Title']['title'] else "Untitled"
        image = page['properties']['Default Image']['files'][0]['file']['url'] if page['properties']['Default Image']['files'] else None
        page_id = page['id']
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
