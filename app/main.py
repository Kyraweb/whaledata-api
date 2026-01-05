from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import get_connection
from psycopg2.extras import RealDictCursor
import random
from datetime import date

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
# Dynamic whale population route (from DB)
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

# -----------------------------
# Seed 50 fake whales into DB for testing
# -----------------------------
@app.post("/seed-whales")
def seed_whales():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Optional: clear old data
        cur.execute("TRUNCATE TABLE whales;")

        species_list = ["Killer Whale", "Blue Whale", "Humpback Whale", "Fin Whale", "Sperm Whale", "Orca"]

        for _ in range(50):
            species = random.choice(species_list)
            population = random.randint(1, 20)
            longitude = round(random.uniform(-180, 180), 4)
            latitude = round(random.uniform(-90, 90), 4)
            region = f"Region {random.randint(1, 10)}"
            last_updated = date.today()

            cur.execute("""
                INSERT INTO whales (species, population, location, region, last_updated)
                VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s);
            """, (species, population, longitude, latitude, region, last_updated))

        conn.commit()
        cur.close()
        conn.close()

        return {"status": "success", "message": "Inserted 50 random whales!"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
