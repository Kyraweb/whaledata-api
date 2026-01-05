from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import get_connection
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Whale Data API")

# -----------------------------
# CORS Setup
# -----------------------------
origins = [
    "http://j04kwgsks88okgkgcwgcwkg8.142.171.41.4.sslip.io",  # your frontend
    "*"  # temporary for testing, allows all
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Dynamic whale population route
# -----------------------------
@app.get("/population")
def population():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT species, population,
                   ST_X(location::geometry) AS longitude,
                   ST_Y(location::geometry) AS latitude,
                   region, last_updated
            FROM whales;
        """)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return {"data": data}
    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# Static test data route
# -----------------------------
@app.get("/population-test")
def population_test():
    return {
        "data": [
            {"species": "Killer Whale", "population": 5, "latitude": 10, "longitude": 80, "region": "Bay of Bengal", "last_updated": "2026-01-04"},
            {"species": "Humpback Whale", "population": 12, "latitude": -20, "longitude": 150, "region": "Pacific Ocean", "last_updated": "2026-01-04"},
            {"species": "Blue Whale", "population": 3, "latitude": 40, "longitude": -70, "region": "Atlantic Ocean", "last_updated": "2026-01-04"}
        ]
    }
