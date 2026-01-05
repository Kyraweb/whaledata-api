from fastapi import FastAPI
from app.database import get_connection
from psycopg2.extras import RealDictCursor

app = FastAPI()

origins = [
    "http://j04kwgsks88okgkgcwgcwkg8.142.171.41.4.sslip.io",  # frontend URL
    "*",  # optional, allows all origins for testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        return {"data": data}
    except Exception as e:
        return {"error": str(e)}

