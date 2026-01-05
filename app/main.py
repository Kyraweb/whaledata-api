from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import get_connection
from psycopg2.extras import RealDictCursor
from datetime import date
import requests

app = FastAPI(title="Whale Data API")

# -----------------------------
# CORS Setup
# -----------------------------
origins = [
    "http://j04kwgsks88okgkgcwgcwkg8.142.171.41.4.sslip.io",  # frontend URL
    "*"  # temporary for testing, allows all origins
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Route: Get population from DB
# -----------------------------
@app.get("/population")
def population():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT species, common_name, population,
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
# Route: Static test data (optional)
# -----------------------------
@app.get("/population-test")
def population_test():
    return {
        "data": [
            {"species": "Killer Whale", "common_name": "Orca", "population": 5, "latitude": 10, "longitude": 80, "region": "Bay of Bengal", "last_updated": "2026-01-04"},
            {"species": "Humpback Whale", "common_name": "Humpback", "population": 12, "latitude": -20, "longitude": 150, "region": "Pacific Ocean", "last_updated": "2026-01-04"},
            {"species": "Blue Whale", "common_name": "Blue Whale", "population": 3, "latitude": 40, "longitude": -70, "region": "Atlantic Ocean", "last_updated": "2026-01-04"}
        ]
    }

# -----------------------------
# Route: Sync GBIF species and store common name
# -----------------------------
GBIF_BASE = "https://api.gbif.org/v1/species/match"

@app.get("/sync-gbif")
def sync_gbif():
    """
    Pull whale species info from GBIF, including common/vernacular name,
    and update the database accordingly.
    """
    whales_to_sync = [
        "Feresa attenuata",
        "Orcinus orca",
        "Balaenoptera musculus",
        "Megaptera novaeangliae",
        "Physeter macrocephalus"
    ]

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    inserted = 0
    updated = 0

    for sci_name in whales_to_sync:
        # Fetch species info from GBIF
        resp = requests.get(GBIF_BASE, params={"name": sci_name})
        if resp.status_code != 200:
            continue
        gbif_data = resp.json()
        common_name = gbif_data.get("vernacularName")

        # Check if the species exists in DB
        cur.execute("SELECT id, common_name FROM whales WHERE species = %s LIMIT 1;", (sci_name,))
        row = cur.fetchone()

        if row:
            # Update common_name if empty
            if common_name and (not row["common_name"] or row["common_name"].strip() == ""):
                cur.execute(
                    "UPDATE whales SET common_name=%s WHERE id=%s;",
                    (common_name, row["id"])
                )
                updated += 1
        else:
            # Insert new whale with placeholder location & region
            cur.execute("""
                INSERT INTO whales (species, common_name, population, location, region, last_updated)
                VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
            """, (
                sci_name,
                common_name,
                1,               # default population
                0.0, 0.0,        # default lat/lon
                "Unknown",       # default region
                date.today()
            ))
            inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok", "inserted": inserted, "updated": updated}
