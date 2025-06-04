# Duke Central Analytics App

This project is a FastAPI web application that acts as a central web service which receives JSON data via POST and stores it in MongoDB.

## Requirements
- Python 3.10+

## Environment Variables
Create a `.env` file in the project root with the following variables:

```
MONGODB_URI="your-mongodb-database-url"
MONGODB_DB="your-monogodb-database-name"
AVIGILON_PROXY_URL="your-avigilon-proxy-endpoint"
VERIFY_SSL=False
```

## Setup (Local Development)

1. **Clone the repo:**
   ```sh
   git clone <repo-url>
   cd duke-central
   ```
2. **Create and activate a virtualenv:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Create your `.env` file** (see above).
5. **Run the app:**
   ```sh
   uvicorn app.main:app --reload
   ```
6. **Access docs:**
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
