import streamlit as st
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pandas import json_normalize
import requests
import base64
from PIL import Image
from io import BytesIO

# --- Configuration ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "appearances"
CAMERA_COLLECTION = "camera_anomaly_reports"
PERSON_COLLECTION = "anomaly_reports"
API_URL = "http://localhost:8001"

# --- Data Loading Functions ---
@st.cache_data(ttl=600)
def load_data(collection_name):
    """Loads data from a specified MongoDB collection."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster')
        db = client[DB_NAME]
        collection = db[collection_name]
        records = list(collection.find({}, {"_id": 0}))
        if not records:
            st.warning(f"No records found in the '{DB_NAME}.{collection_name}' collection.")
            return pd.DataFrame()
        
        df = json_normalize(records)

        # Use utc=True to robustly handle both tz-aware strings and missing/null values.
        # Use errors='coerce' to prevent crashes on unparseable strings, turning them into NaT.
        if 'anomaly_timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['anomaly_timestamp'], utc=True, errors='coerce')
            df = df.drop(columns=['anomaly_timestamp'])
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        
        return df
    except ConnectionFailure:
        st.error(f"Could not connect to MongoDB at {MONGO_URI}. Please ensure it's running.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred while loading or processing data for '{collection_name}': {e}")
        return pd.DataFrame()

# --- Helper Functions ---
@st.cache_data(show_spinner=False)
def get_face_image(person_id):
    if not person_id or person_id == "N/A": return None
    try:
        params = {"personId": person_id, "personIdOnly": True}
        resp = requests.get(f"{API_URL}/get-appearances", params=params, timeout=10)
        resp.raise_for_status()
        events = resp.json()
        if not events: return None
        event = events[0]
        img_b64 = event.get("imageBaseString")
        if not img_b64: return None
        img_bytes = base64.b64decode(img_b64)
        image = Image.open(BytesIO(img_bytes))
        if event.get("personFace") and event["personFace"].get("BoundingBox"):
            bbox = event["personFace"]["BoundingBox"]
            width, height = image.size
            left, top = int(bbox["Left"] * width), int(bbox["Top"] * height)
            right, bottom = int((bbox["Left"] + bbox["Width"]) * width), int((bbox["Top"] + bbox["Height"]) * height)
            return image.crop((left, top, right, bottom))
        return image
    except Exception as e:
        print(f"Error fetching face image for {person_id}: {e}")
        return None

def get_priority_icon(priority):
    """Gets the consistent emoji icon for a priority level."""
    icon_map = {"CRITICAL": "🛑", "HIGH": "⚠️", "MEDIUM": "🔶", "LOW": "ℹ️", "N/A": "⚪"}
    return icon_map.get(str(priority).upper(), "❓")

if "person_occurrences_cache" not in st.session_state:
    st.session_state.person_occurrences_cache = {}

# --- Streamlit App Layout ---
st.set_page_config(page_title="Unified Anomaly Dashboard", layout="wide")
st.title("📷👤 Unified Anomaly Dashboard")
st.markdown("This dashboard displays both person-centric and camera-centric anomaly reports.")

st.sidebar.header("View & Filter Options")
anomaly_type = st.sidebar.radio("Select Anomaly Type", ("Person-Centric", "Camera-Centric"), key="anomaly_type_selector")

if anomaly_type == "Person-Centric":
    df = load_data(PERSON_COLLECTION)
    id_column = 'personId'
    page_header = "Person Anomaly Reports"
else:
    df = load_data(CAMERA_COLLECTION)
    id_column = 'camera_identifier'
    page_header = "Camera Anomaly Reports"

st.header(page_header)

if not df.empty:
    df['model_type'] = df['model_config.model_choice']
    df['ai_triage.priority'] = df.get('ai_triage.priority', pd.Series(dtype='str')).fillna('N/A')
    
    if id_column not in df.columns:
        st.error(f"Data is missing the required ID column: '{id_column}'.")
        st.stop()
        
    selected_ids = st.sidebar.multiselect(f"Filter by {id_column.replace('_', ' ').title()}", options=sorted(df[id_column].unique()), default=sorted(df[id_column].unique()))
    selected_models = st.sidebar.multiselect("Filter by Model Type", options=sorted(df['model_type'].unique()), default=sorted(df['model_type'].unique()))
    priority_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "N/A"]
    sorted_priorities = sorted(df['ai_triage.priority'].unique(), key=lambda x: priority_order.index(x) if x in priority_order else len(priority_order))
    selected_priorities = st.sidebar.multiselect("Filter by AI Triage Priority", options=sorted_priorities, default=sorted_priorities)

    filtered_df = df[df[id_column].isin(selected_ids) & df['model_type'].isin(selected_models) & df['ai_triage.priority'].isin(selected_priorities)]

    st.dataframe(filtered_df.drop(columns=[col for col in ['explanation.model_driven_insight', 'explanation.rule_based', 'ai_triage.insight'] if col in filtered_df.columns], errors='ignore'))
    
    st.header("Anomaly Counts")
    col1, col2 = st.columns(2)
    col1.subheader(f"Anomalies per {id_column.replace('_', ' ').title()}"); col1.bar_chart(filtered_df[id_column].value_counts())
    col2.subheader("Anomalies by Model Type"); col2.bar_chart(filtered_df['model_type'].value_counts())
    
    if 'timestamp' in filtered_df.columns:
        filtered_df = filtered_df.sort_values(
            by='timestamp', 
            ascending=False, 
            na_position='last'
        )

    st.header("Detailed Anomaly Insights")
    
    for idx, row in filtered_df.iterrows():
        priority = row.get('ai_triage.priority', 'N/A')
        date_str = row['timestamp'].strftime('%Y-%m-%d') if pd.notna(row.get('timestamp')) else 'N/A'
        rule_based = row.get('explanation.rule_based', [])
        model_driven = row.get('explanation.model_driven_insight', [])
        
        # Determine the primary cause of the anomaly for the title
        title_subject = "General Anomaly"
        if isinstance(rule_based, list) and rule_based:
            title_subject = ", ".join(set([item.get('category', 'Anomaly') for item in rule_based]))
        elif isinstance(model_driven, list) and model_driven:
            try:
                sorted_insights = sorted(model_driven, key=lambda x: x.get('contribution_pct', 0), reverse=True)
                title_subject = ", ".join([str(insight.get('feature', 'N/A')) for insight in sorted_insights[:3]])
            except (TypeError, KeyError): 
                title_subject = "Model-Driven Anomaly"

        # --- NEW: Determine the source of the anomaly (Rule or ML) ---
        anomaly_source_text = "ML-based"  # Default to ML-based
        if isinstance(rule_based, list) and rule_based:
            anomaly_source_text = "Rule-based"
        # --- END NEW ---
        
        # --- MODIFIED: Add the source to the expander title ---
        expander_title = (
            f"{get_priority_icon(priority)} {priority.upper()} | {anomaly_source_text} | {title_subject} | "
            f"{id_column.replace('_', ' ').title()}: {row[id_column]} | Date: {date_str}"
        )
        
        with st.expander(expander_title):
            # --- START OF UNIFIED LAYOUT ---

            st.subheader("Report Details")
            details_col1, details_col2 = st.columns([1, 4])
            
            with details_col1:
                if anomaly_type == "Person-Centric":
                    person_id = row.get(id_column)
                    face_image = get_face_image(person_id)
                    if face_image:
                        st.image(face_image, use_container_width=True, caption=f"Person: {person_id}")
                    else:
                        st.markdown("<div style='height:128px;border:1px solid #444;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:4em;'>👤</div>", unsafe_allow_html=True)
                        st.caption("No Image")
                else: 
                    st.markdown("<div style='height:128px;border:1px solid #444;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:4em;'>📷</div>", unsafe_allow_html=True)
                    st.caption("Camera")

            with details_col2:
                id_label = "Person ID" if anomaly_type == "Person-Centric" else "Camera ID"
                st.markdown(f"**{id_label}:** `{row.get(id_column)}`")
                st.markdown(f"**Anomaly Timestamp:** {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S %Z') if pd.notna(row.get('timestamp')) else 'N/A'}")
                st.markdown(f"**Model Type:** {row['model_type']}")
                st.markdown(f"**Anomaly ID:** `{row.get('anomaly_id', 'N/A')}`")
            st.divider()

            st.subheader("Anomaly Breakdown")
            break_col1, break_col2 = st.columns([1, 2])
            with break_col1:
                st.metric("Anomaly Score", value=row.get('anomaly_details.score', 0))
                st.write(f"Raw Error: {row.get('anomaly_details.raw_error', 0):.4f}")
                st.write(f"Threshold: {row.get('anomaly_details.threshold', 0):.4f}")
            with break_col2:
                st.markdown("**AI Triage**")
                priority_val = row.get('ai_triage.priority', 'N/A').upper()
                insight = row.get('ai_triage.insight', 'No triage insight provided.')
                priority_text = f"**Priority: {priority_val}**"
                icon_for_callout = get_priority_icon(priority_val)

                if priority_val in ("CRITICAL", "HIGH"):
                    st.error(priority_text, icon=icon_for_callout)
                elif priority_val == "MEDIUM":
                    st.warning(priority_text, icon=icon_for_callout)
                else:
                    st.info(priority_text, icon=icon_for_callout)
                st.markdown(f"> {insight}")
            st.divider()
            
            st.subheader("Explanation Details")
            if isinstance(rule_based, list) and rule_based:
                st.markdown("**Rule-Based Insights:**")
                for item in rule_based: st.markdown(f"- **{item.get('category', 'N/A')}**: {item.get('description', 'No description')}")
            else:
                st.markdown("_No rule-based insights available._")
            
            if isinstance(model_driven, list) and model_driven:
                st.markdown("**Model-Driven Insights:**")
                try:
                    st.dataframe(pd.DataFrame(model_driven), use_container_width=True)
                except Exception as e:
                    st.error(f"Could not display model-driven insights table: {e}")
                    st.write(model_driven)
            else:
                st.markdown("_No model-driven insights available._")
            st.divider()

            if anomaly_type == "Person-Centric":
                st.subheader(f"Historical Appearances for Person `{row.get(id_column)}`")
                person_id = row.get(id_column)
                if person_id in st.session_state.person_occurrences_cache:
                    events = st.session_state.person_occurrences_cache[person_id]
                    if not events: st.info("No historical appearances found for this person.")
                    else:
                        sorted_events = sorted(events, key=lambda e: e.get("eventStartTime", ""), reverse=True)
                        st.metric("Total Occurrences Found", len(sorted_events))
                        with st.container(height=400):
                            for event in sorted_events:
                                img_col, data_col = st.columns([1, 3])
                                with img_col:
                                    img_b64 = event.get("imageBaseString")
                                    if img_b64: st.image(base64.b64decode(img_b64), use_container_width=True)
                                with data_col:
                                    event_time_str = event.get("eventStartTime", "Unknown").replace("T", " ").split(".")[0]
                                    st.markdown(f"**Time:** `{event_time_str}Z`")
                                    st.markdown(f"**Camera:** `{event.get('cameraId', 'N/A')}`")
                                    st.markdown(f"**Confidence:** `{event.get('personFace', {}).get('Confidence', 0):.1f}%`")
                                st.divider()
                else:
                    button_key = f"load_app_{row.get('anomaly_id', idx)}"
                    if st.button("Load Historical Appearances", key=button_key):
                        with st.spinner(f"Loading appearances for person {person_id}..."):
                            try:
                                params = {"personId": person_id}
                                resp = requests.get(f"{API_URL}/get-appearances", params=params, timeout=20)
                                resp.raise_for_status()
                                st.session_state.person_occurrences_cache[person_id] = resp.json()
                            except Exception as e:
                                st.error(f"Could not load appearances: {e}")
                                st.session_state.person_occurrences_cache[person_id] = []
                        st.rerun()
else:
    st.info("Waiting for data... Select a view and ensure the corresponding pipeline was run with the --write-to-mongo flag.")
    