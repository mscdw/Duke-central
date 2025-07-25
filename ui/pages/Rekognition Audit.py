import streamlit as st
import httpx
import pandas as pd

# --- Page Configuration ---
st.set_page_config(
    page_title="Rekognition User Audit",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AWS Rekognition User Audit")
st.markdown("This app audits users in an AWS Rekognition Collection against a central user database via an API.")

# --- Helper: Setup Secrets ---
# For this to work, create a file .streamlit/secrets.toml
# and add your AWS credentials and other settings:
#
# [aws]
# AWS_ACCESS_KEY_ID = "YOUR_ACCESS_KEY"
# AWS_SECRET_ACCESS_KEY = "YOUR_SECRET_KEY"
# AWS_DEFAULT_REGION = "us-east-2"
#
# API_BASE = "https://your-central-api.com"
# VERIFY_SSL = true

# --- Configuration from Secrets ---
central_base_url = st.secrets.get("API_BASE", "")
verify_ssl = st.secrets.get("VERIFY_SSL", True)

users_url = f"{central_base_url.rstrip('/')}/users/" if central_base_url else ""

# --- Data Fetching Functions (Cached) ---
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_all_rekognition_users_from_api(base_url: str, collection_id: str, ssl_verify: bool):
    """
    Lists all users from a Rekognition collection, handling pagination automatically.
    Returns a list of user dictionaries or an empty list on error.
    """
    if not base_url:
        st.error("Central API Base URL not configured.")
        return []

    rek_users_url = f"{base_url.rstrip('/')}/users/from-rekognition/{collection_id}"

    try:
        with httpx.Client(verify=ssl_verify, timeout=10, follow_redirects=True) as client:
            response = client.get(rek_users_url)
            response.raise_for_status()
            users = response.json()

        if not isinstance(users, list):
            st.error(f"Unexpected API response format from {rek_users_url}. Expected a JSON list.")
            return []

        return users
    except httpx.HTTPStatusError as e:
        st.error(f"Failed to fetch Rekognition users via API: {e.response.status_code} - {e.response.text}")
        return []
    except httpx.RequestError as e:
        st.error(f"Failed to fetch users from Central API at {rek_users_url}: {e}")
        return []

# @st.cache_data(ttl=300) # Cache for 5 minutes
def get_all_central_users_sync(api_url: str, ssl_verify: bool):
    """
    Fetches all users from Central DB and returns a dict indexed by _id.
    """
    if not api_url:
        st.error("Central users URL not configured.")
        return {}

    try:
        with httpx.Client(verify=ssl_verify, timeout=10, follow_redirects=True) as client:
            response = client.get(api_url.rstrip('/'))
            response.raise_for_status()
            users = response.json()

        if not isinstance(users, list):
            st.error(f"Unexpected API response format from {api_url}. Expected a JSON list.")
            return {}

        return {user["_id"]: user for user in users if "_id" in user}

    except httpx.RequestError as e:
        st.error(f"Failed to fetch users from Central API at {api_url}: {e}")
        return {}
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching Central users: {e}")
        return {}


# --- Main Application Logic ---
collection_id = st.text_input(
    "Rekognition Collection ID",
    "new-face-collection-11" # Using the default from the backend
)

if st.button("🚀 Run Audit", type="primary", use_container_width=True, disabled=(not central_base_url)):

    if not collection_id:
        st.warning("Please provide a Rekognition Collection ID.")
    else:
        with st.status(f"Auditing collection '{collection_id}'...", expanded=True) as status:
            # 1. Fetch Rekognition Users
            st.write("Fetching users from AWS Rekognition (via Central API)...")
            rek_users = get_all_rekognition_users_from_api(central_base_url, collection_id, verify_ssl)
            if not rek_users:
                status.update(label="Audit failed: Could not retrieve Rekognition users.", state="error")
                st.stop()
            st.write(f"✅ Found {len(rek_users)} users in Rekognition.")

            # 2. Fetch Central DB Users
            st.write("Fetching users from Central API...")
            central_users_by_id = get_all_central_users_sync(users_url, verify_ssl)
            if not central_users_by_id:
                status.update(label="Audit failed: Could not retrieve Central API users.", state="error")
                st.stop()
            st.write(f"✅ Found {len(central_users_by_id)} users in Central API.")

            # 3. Perform Audit Logic
            st.write("Comparing user lists and identifying discrepancies...")
            orphaned_users = []
            for user in rek_users:
                user_id = user.get("UserId")
                if user_id and user_id not in central_users_by_id:
                    orphaned_users.append(user_id)

            status.update(label="Audit Complete!", state="complete", expanded=False)

        # --- Reporting ---
        st.header("📊 Audit Report")
        st.divider()

        col1, col2, col3 = st.columns(3)
        col1.metric("Rekognition Users", f"{len(rek_users)}")
        col2.metric("Central DB Users", f"{len(central_users_by_id)}")
        col3.metric("Orphaned Users", f"{len(orphaned_users)}", delta=len(orphaned_users), delta_color="inverse")

        if orphaned_users:
            st.warning(f"🔴 Found {len(orphaned_users)} orphaned users that exist in Rekognition but NOT in the Central DB.")
            with st.expander("View Orphaned User IDs"):
                df = pd.DataFrame(orphaned_users, columns=["Orphaned UserId"])
                st.dataframe(df, use_container_width=True)
        else:
            st.success("✅ No orphaned users found. All Rekognition users are accounted for in the Central DB.")