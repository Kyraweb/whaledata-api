from fastapi import FastAPI
from database import get_connection
from psycopg2.extras import RealDictCursor

app = FastAPI(title="WhaleData API")

@app.get("/population")
def population():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT species, population, ST_X(location::geometry) AS longitude, ST_Y(location::geometry) AS latitude, region, last_updated FROM whales;")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return {"data": data}
