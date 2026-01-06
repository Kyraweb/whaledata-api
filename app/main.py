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
    "https://whaledata.org",  # your frontend
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
# Whale population route
# -----------------------------
@app.get("/population")
def population():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT species AS scientific_name,
                   common_name,
                   population,
                   ST_X(location::geometry) AS longitude,
                   ST_Y(location::geometry) AS latitude,
                   region,
                   last_updated
            FROM whales;
        """)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return {"data": data}
    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# Sync GBIF whales
# -----------------------------
@app.post("/sync-gbif")
def sync_gbif():
    GBIF_API = "https://api.gbif.org/v1/occurrence/search"
    
    try:
        # Example: fetch marine mammals (filter as needed)
        params = {
            "taxon_key": 2470,  # Cetacea (whales, dolphins)
            "has_coordinate": "true",
            "limit": 300
        }
        response = requests.get(GBIF_API, params=params)
        response.raise_for_status()
        results = response.json().get("results", [])

        conn = get_connection()
        cur = conn.cursor()
        inserted_count = 0

        for r in results:
            sci_name = r.get("species") or r.get("scientificName")
            common_name = r.get("vernacularName") or None
            population = 1  # default if unknown
            lon = r.get("decimalLongitude")
            lat = r.get("decimalLatitude")
            region = r.get("country") or r.get("countryCode") or "Unknown"
            last_updated = date.today()

            if not (sci_name and lon and lat):
                continue  # skip incomplete records

            # Insert or update based on scientific_name + location
            cur.execute("""
                INSERT INTO whales (scientific_name, common_name, population, location, region, last_updated)
                VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
                ON CONFLICT (scientific_name, location)
                DO UPDATE SET
                    common_name = COALESCE(EXCLUDED.common_name, whales.common_name),
                    population = EXCLUDED.population,
                    region = EXCLUDED.region,
                    last_updated = EXCLUDED.last_updated;
            """, (sci_name, common_name, population, lon, lat, region, last_updated))
            inserted_count += 1

        conn.commit()
        cur.close()
        conn.close()

        return {"source": "GBIF", "inserted_or_updated": inserted_count}

    except Exception as e:
        return {"error": str(e)}

