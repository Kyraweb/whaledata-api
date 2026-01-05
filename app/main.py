# app/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from app.database import get_connection
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Whale Data API")

# CORS Setup
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

# Fetch all whale data with optional filters
@app.get("/population")
def population(
    species: str | None = Query(None, description="Filter by species"),
    region: str | None = Query(None, description="Filter by region")
):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        base_query = """
            SELECT species, population,
                   ST_X(location::geometry) AS longitude,
                   ST_Y(location::geometry) AS latitude,
                   region, last_updated
            FROM whales
            WHERE 1=1
        """
        params = []
        if species:
            base_query += " AND species = %s"
            params.append(species)
        if region:
            base_query += " AND region = %s"
            params.append(region)

        cur.execute(base_query, params)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return {"data": data}

    except Exception as e:
        return {"error": str(e)}
