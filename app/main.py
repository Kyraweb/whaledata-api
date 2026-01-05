import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import RealDictCursor
from app.database import get_connection

# -----------------------------------
# App config
# -----------------------------------
app = FastAPI(title="Whale Data API")

# Feature flag: fake vs real data
USE_FAKE_DATA = os.getenv("USE_FAKE_DATA", "false").lower() == "true"

# -----------------------------------
# CORS
# -----------------------------------
origins = [
    "http://j04kwgsks88okgkgcwgcwkg8.142.171.41.4.sslip.io",  # frontend
    "*"  # OK for now, tighten later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------
# Fake data provider (internal)
# -----------------------------------
def fake_population_data():
    return {
        "source": "fake",
        "count": 3,
        "data": [
            {
                "species": "Killer Whale",
                "population": 5,
                "latitude": 10,
                "longitude": 80,
                "region": "Bay of Bengal",
                "last_updated": "2026-01-04"
            },
            {
                "species": "Humpback Whale",
                "population": 12,
                "latitude": -20,
                "longitude": 150,
                "region": "Pacific Ocean",
                "last_updated": "2026-01-04"
            },
            {
                "species": "Blue Whale",
                "population": 3,
                "latitude": 40,
                "longitude": -70,
                "region": "Atlantic Ocean",
                "last_updated": "2026-01-04"
            }
        ]
    }

# -----------------------------------
# Main population endpoint
# -----------------------------------
@app.get("/population")
def population():
    # Toggle fake data
    if USE_FAKE_DATA:
        print("DATA SOURCE: FAKE")
        return fake_population_data()

    print("DATA SOURCE: DATABASE")

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                species,
                population,
                ST_X(location::geometry) AS longitude,
                ST_Y(location::geometry) AS latitude,
                region,
                last_updated
            FROM whales;
        """)

        rows = cur.fetchall()

        cur.close()
        conn.close()

        return {
            "source": "database",
            "count": len(rows),
            "data": rows
        }

    except Exception as e:
        return {
            "error": "Failed to fetch whale data",
            "details": str(e)
        }

# -----------------------------------
# Health check (important for Coolify)
# -----------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "use_fake_data": USE_FAKE_DATA
    }
