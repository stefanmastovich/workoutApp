import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
MUSCLE_MAP = {
    "Pushups": "Chest/Push",
    "Overhead Press": "Shoulders/Push",
    "Tricep Ext.": "Arms/Push",
    "Bicep Curls": "Arms/Pull",
    "Renegade Rows": "Back/Pull",
    "Goblet Squats": "Legs/Quads",
    "Lunges": "Legs/Quads",
    "Glute Bridges": "Legs/Posterior",
    "Bird-Dogs": "Core/Stability"
}

st.set_page_config(page_title="Road to 100", layout="centered")
st.title("📈 Functional Progression (Cloud)")

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_history():
    return conn.read(worksheet="workout_history", ttl="0s")

# --- SIDEBAR: EXERCISE MANAGEMENT ---
if 'exercises' not in st.session_state:
    st.session_state.exercises = list(MUSCLE_MAP.keys())

with st.sidebar:
    st.header("⚙️ Settings")
    new_ex = st.text_input("Add New Exercise:")
    new_cat = st.selectbox("Category:", ["Push", "Pull", "Legs", "Core", "Arms"])
    if st.button("Add to Routine"):
        if new_ex and new_ex not in st.session_state.exercises:
            st.session_state.exercises.append(new_ex)
            MUSCLE_MAP[new_ex] = new_cat
            st.rerun()

# --- MAIN LOGGING UI ---
with st.expander("📝 Log Today's Movement", expanded=True):
    log_date = st.date_input("Workout Date", datetime.now())
    current_workout = []
    
    for ex in st.session_state.exercises:
        st.markdown(f"**{ex}**")
        col1, col2 = st.columns(2)
        with col1:
            reps = st.number_input(f"Reps", min_value=0, step=1, key=f"reps_{ex}")
        with col2:
            weight = st.number_input(f"Weight (lbs)", min_value=0.0, step=1.0, key=f"weight_{ex}")
        
        if reps > 0:
            current_workout.append({
                "Date": log_date.strftime('%Y-%m-%d'),
                "Exercise": ex,
                "Reps": reps,
                "Weight_Lbs": weight,
                "Muscle_Group": MUSCLE_MAP.get(ex, "Other")
            })

    if st.button("Submit Workout", type="primary", use_container_width=True):
        if current_workout:
            existing_data = load_history()
            updated_df = pd.concat([existing_data, pd.DataFrame(current_workout)], ignore_index=True)
            conn.update(worksheet="workout_history", data=updated_df)
            st.success("Data synced to Google Sheets!")
            st.rerun()

# --- ANALYTICS ---
history_df = load_history()

if not history_df.empty:
    st.divider()
    history_df["Reps"] = pd.to_numeric(history_df["Reps"])
    history_df["Weight_Lbs"] = pd.to_numeric(history_df["Weight_Lbs"])
    history_df["Volume"] = history_df["Reps"] * history_df["Weight_Lbs"]
    
    # 1. High Level Metrics
    total_vol = history_df["Volume"].sum()
    st.metric("Total Lifetime Volume", f"{total_vol:,.0f} lbs")

    # 2. Muscle Group Volume (Treemap)
    st.write("**Volume Distribution by Muscle Group**")
    vol_by_group = history_df.groupby("Muscle_Group")["Volume"].sum().reset_index()
    fig_tree = px.treemap(vol_by_group, path=['Muscle_Group'], values='Volume', 
                          color='Volume', color_continuous_scale='Blues')
    st.plotly_chart(fig_tree, use_container_width=True)

    # 3. Progression Line Chart
    st.write("**Progression Over Time (Max Reps)**")
    fig_line = px.line(history_df.sort_values("Date"), x="Date", y="Reps", color="Exercise", markers=True)
    st.plotly_chart(fig_line, use_container_width=True)

    # 4. Raw Data Access
    with st.expander("📋 Edit/View Raw Data"):
        edited_df = st.data_editor(history_df, num_rows="dynamic", use_container_width=True)
        if st.button("Save Changes to Cloud"):
            conn.update(worksheet="workout_history", data=edited_df)
            st.toast("Google Sheet Updated!")
