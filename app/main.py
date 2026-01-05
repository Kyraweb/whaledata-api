from fastapi import FastAPI
from app.database import get_connection
from psycopg2.extras import RealDictCursor

app = FastAPI()

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
