from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from app.database import get_connection
from psycopg2.extras import RealDictCursor
import requests
from datetime import datetime
from psycopg2 import sql

app = FastAPI(title="Whale Data API")

# -----------------------------
# CORS Setup
# -----------------------------
origins = [
    "http://j04kwgsks88okgkgcwgcwkg8.142.171.41.4.sslip.io",
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
# GBIF Whale Sync Function
# -----------------------------
def fetch_whales_from_gbif():
    """
    Pull occurrence data from GBIF API and insert/update into whales table.
    """
    url = "https://api.gbif.org/v1/occurrence/search"
    params = {
        "taxon_key": 2440028,  # Orcinus orca (Killer Whale) example, can be extended
        "has_coordinate": "true",
        "limit": 300  # max per request, can paginate later
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json().get("results", [])

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        for item in data:
            species = item.get("species") or item.get("scientificName")
            lat = item.get("decimalLatitude")
            lon = item.get("decimalLongitude")
            region = item.get("locality") or item.get("country")
            last_updated = item.get("eventDate") or datetime.utcnow().isoformat()

            if lat is None or lon is None:
                continue  # skip if no coordinates

            cur.execute("""
                INSERT INTO whales (species, population, location, region, last_updated)
                VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
                ON CONFLICT (species, location) DO UPDATE
                SET population = EXCLUDED.population,
                    last_updated = EXCLUDED.last_updated,
                    region = EXCLUDED.region;
            """, (species, 1, lon, lat, region, last_updated))

        conn.commit()
        cur.close()
        conn.close()
        print(f"GBIF sync completed: {len(data)} occurrences added/updated.")

    except Exception as e:
        print(f"Error fetching GBIF data: {e}")


# -----------------------------
# API Endpoints
# -----------------------------
@app.get("/population")
def population(species: str = None):
    """Return whale data from DB."""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = "SELECT species, population, ST_X(location::geometry) AS longitude, ST_Y(location::geometry) AS latitude, region, last_updated FROM whales"
        params = []
        if species:
            query += " WHERE species = %s"
            params.append(species)
        cur.execute(query, params)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return {"data": data}
    except Exception as e:
        return {"error": str(e)}


@app.post("/sync-gbif")
def sync_gbif(background_tasks: BackgroundTasks):
    """Trigger GBIF sync in background."""
    background_tasks.add_task(fetch_whales_from_gbif)
    return {"message": "GBIF sync started in background"}
