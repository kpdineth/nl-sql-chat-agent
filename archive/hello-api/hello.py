# hello.py
# BEFORE: connected to database, printed data, and exited
# NOW:    runs a FastAPI web server with API endpoints
#         you send a SQL query string → it returns data as JSON

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL_READONLY")

# ---- Database connection pool (shared across all requests) ----
pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start database pool when server starts, close when it stops."""
    global pool
    print("Connecting to database...")
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    print("Database connected! Server is ready.")
    yield
    await pool.close()
    print("Database pool closed.")


# ---- Create the FastAPI app ----
app = FastAPI(
    title="Hello SQL API",
    description="Send a SQL query, get data back as JSON",
    lifespan=lifespan,
)


# ---- Request/Response models ----
class QueryRequest(BaseModel):
    sql: str   # The SQL query string to run


# ---- ENDPOINTS ----

@app.get("/")
async def home():
    """Just to check the server is alive."""
    return {"message": "Hello! The SQL API is running. Try POST /query"}


@app.get("/health")
async def health():
    """Health check — also tests database connection."""
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
    return {"status": "ok", "database": "connected", "test_query": result}


@app.get("/customers")
async def get_customers():
    """Quick endpoint — returns all customers."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, name, email, city FROM customers")
    return [dict(row) for row in rows]


@app.get("/products")
async def get_products():
    """Quick endpoint — returns all products."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, name, category, price FROM products")
    return [dict(row) for row in rows]


@app.get("/orders")
async def get_orders():
    """Quick endpoint — returns all orders with customer and product names."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.name AS customer, p.name AS product,
                   o.quantity, o.status, o.order_date
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            JOIN products p ON o.product_id = p.id
            ORDER BY o.order_date DESC
        """)
    return [dict(row) for row in rows]


@app.post("/query")
async def run_query(request: QueryRequest):
    """
    THE MAIN ENDPOINT
    Send any SELECT query → get results back as JSON.

    Example request body:
    {
        "sql": "SELECT name, city FROM customers WHERE city = 'London'"
    }
    """

    sql = request.sql.strip()

    # Safety check: only allow SELECT queries
    if not sql.upper().startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT queries are allowed. Your query must start with SELECT."
        )

    # Run the query
    try:
        async with pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch(sql)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}")

    # Convert to JSON-friendly format
    results = [dict(row) for row in rows]

    return {
        "sql": sql,
        "row_count": len(results),
        "data": results,
    }
