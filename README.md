# Duke Central Analytics App

This repository contains two main components:

- **Backend API**: A FastAPI web application for receiving, storing, and serving appearance event data from various sources, using MongoDB as the database.
- **Frontend UI**: A Streamlit dashboard for visualizing appearance events and images.

---

## Backend (̌FastAPI)

### Requirements
- Python 3.10+
- MongoDB instance (local or remote)

### Environment Variables
Create a `.env` file in the project root with the following variables:

```
MONGODB_BASE="your-mongodb-database-url"
MONGODB_DB="your-mongodb-database-name"
AVIGILON_PROXY_BASE="your-avigilon-proxy-endpoint"
VERIFY_SSL=False
```

Create a `secrets.toml` file in the project root under .streamlit folder with the following variables:

```
API_BASE = "your-central-backend-url"
```

---

## Setup & Run (Backend + UI)

### 1. Clone the repository
```sh
git clone <repo-url>
cd duke-central
```

### 2. Create and activate a virtual environment
```sh
python3 -m venv venv
source venv/bin/activate
```

### 3. Install all dependencies (backend + UI)
```sh
pip install -r app/requirements.txt
pip install -r ui/requirements.txt
```

### 4. Configure environment variables and secrets
- Create the .env and secrets.toml file as given above

### 5. Run the backend (FastAPI)
```sh
uvicorn app.main:app --reload
```

### 6. Run the frontend (Streamlit UI)
```sh
streamlit run ui/Home.py
```

---

## Project Structure

```
app/        # FastAPI backend
ui/         # Streamlit frontend
```

---
