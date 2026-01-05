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
    "http://j04kwgsks88okgkgcwgcwkg8.142.171.41.4.sslip.io",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Fetch whale data from DB
# -----------------------------
@app.get("/population")
def population():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT scientific_name, common_name, population,
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
# Sync GBIF whales into DB
# -----------------------------
@app.post("/sync-gbif")
def sync_gbif():
    """
    Fetch whale occurrences from GBIF and insert/update DB.
    """
    GBIF_API = "https://api.gbif.org/v1/occurrence/search?taxon_key=2492480&limit=300"  # Example: Cetacea class
    try:
        response = requests.get(GBIF_API)
        response.raise_for_status()
        results = response.json().get("results", [])

        conn = get_connection()
        cur = conn.cursor()
        
        for r in results:
            scientific_name = r.get("species") or r.get("scientificName")
            common_name = r.get("vernacularName") or scientific_name  # fallback to scientific name
            latitude = r.get("decimalLatitude")
            longitude = r.get("decimalLongitude")
            if latitude is None or longitude is None or scientific_name is None:
                continue
            population = 1  # default since GBIF may not have exact counts
            region = r.get("country") or "Unknown"
            last_updated = date.today()

            # Upsert: insert if not exists
            cur.execute("""
                INSERT INTO whales (scientific_name, common_name, population, location, region, last_updated)
                VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
                ON CONFLICT (scientific_name, latitude, longitude) DO UPDATE
                SET common_name = EXCLUDED.common_name,
                    last_updated = EXCLUDED.last_updated;
            """, (scientific_name, common_name, population, longitude, latitude, region, last_updated))

        conn.commit()
        cur.close()
        conn.close()

        return {"status": "success", "count": len(results)}

    except Exception as e:
        return {"error": str(e)}
