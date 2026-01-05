# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import get_connection
from psycopg2.extras import RealDictCursor
import requests
from datetime import date

app = FastAPI(title="Whale Data API")

# -----------------------------
# CORS Setup
# -----------------------------
origins = [
    "http://j04kwgsks88okgkgcwgcwkg8.142.171.41.4.sslip.io",  # frontend
    "*"  # temporary for testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Route: Pull live DB data
# -----------------------------
@app.get("/population")
def population():
    """
    Returns whale population from the database.
    """
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
        return {"source": "database", "count": len(data), "data": data}
    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# Route: Fake/test data
# -----------------------------
@app.get("/population-test")
def population_test():
    """
    Returns a small set of hardcoded whale data for testing/dev purposes.
    """
    return {
        "source": "test-data",
        "count": 3,
        "data": [
            {"species": "Killer Whale", "population": 5, "latitude": 10, "longitude": 80, "region": "Bay of Bengal", "last_updated": "2026-01-04"},
            {"species": "Humpback Whale", "population": 12, "latitude": -20, "longitude": 150, "region": "Pacific Ocean", "last_updated": "2026-01-04"},
            {"species": "Blue Whale", "population": 3, "latitude": 40, "longitude": -70, "region": "Atlantic Ocean", "last_updated": "2026-01-04"}
        ]
    }

# -----------------------------
# Route: Sync GBIF whales into DB
# -----------------------------
@app.post("/sync-gbif")
def sync_gbif():
    """
    Fetch whale occurrence data from GBIF API and insert into DB.
    For now, this uses a limited example and overwrites the table.
    """
    try:
        # Example GBIF API endpoint (adjust to species query or limit)
        gbif_url = "https://api.gbif.org/v1/occurrence/search?taxon_key=2440530&limit=50&hasCoordinate=true"
        resp = requests.get(gbif_url)
        resp.raise_for_status()
        gbif_data = resp.json().get("results", [])

        conn = get_connection()
        cur = conn.cursor()

        # Optional: clear existing whales
        cur.execute("TRUNCATE TABLE whales;")

        # Insert GBIF data
        for item in gbif_data:
            species = item.get("species", "Unknown")
            population = 1  # GBIF doesn't provide population; default 1
            lon = item.get("decimalLongitude")
            lat = item.get("decimalLatitude")
            region = item.get("country", "Unknown")
            last_updated = date.today()

            if lon is not None and lat is not None:
                cur.execute("""
                    INSERT INTO whales (species, population, location, region, last_updated)
                    VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
                """, (species, population, lon, lat, region, last_updated))

        conn.commit()
        cur.close()
        conn.close()

        return {"source": "GBIF", "count": len(gbif_data), "message": "Synced GBIF data successfully!"}

    except requests.RequestException as e:
        return {"error": f"GBIF API error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}
