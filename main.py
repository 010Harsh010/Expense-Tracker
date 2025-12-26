from fastmcp import FastMCP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import json
import datetime
from typing import Optional

load_dotenv()

DATABASE_URL = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

mcp = FastMCP(name="Expense Tracker")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

category_Path = "category.json"

# -------------------- DB INIT --------------------

def init_db():
    query = """
    CREATE TABLE IF NOT EXISTS expanse (
        id INT AUTO_INCREMENT PRIMARY KEY,
        amount INT NOT NULL,
        category VARCHAR(100) NOT NULL,
        subcategory VARCHAR(100) DEFAULT '',
        note TEXT DEFAULT '',
        date DATE NOT NULL
    );
    """

    with engine.begin() as conn:
        conn.execute(text(query))

    print("MySQL database initialized.")

init_db()

# -------------------- TOOLS --------------------
@mcp.tool()
def add_expanse(
    amount: int,
    category: str,
    subcategory: str = "",
    note: str = "",
    date: str = ""
):
    """Add a new expanse record to the database."""

    # date = normalize_date(date)

    query = """
    INSERT INTO expanse (amount, category, subcategory, note, date)
    VALUES (:amount, :category, :subcategory, :note, :date)
    """

    date = datetime.datetime.strptime(date, "%Y-%m-%d").date() if date!="" else datetime.date.today()
    
    with engine.begin() as conn:
        result = conn.execute(
            text(query),
            {
                "amount": amount,
                "category": category,
                "subcategory": subcategory,
                "note": note,
                "date": date
            }
        )

    return {
        "status": "success",
        "message": "Expanse added successfully.",
        "id": result.lastrowid,
        "date_used": date
    }

@mcp.tool()
def get_expanse(start_date: str, end_date: str):
    """Retrieve expanse records within a date range."""

    query = """
    SELECT * FROM expanse
    WHERE date BETWEEN :start AND :end
    ORDER BY id ASC
    """

    with engine.connect() as conn:
        cur = conn.execute(
            text(query),
            {"start": start_date, "end": end_date}
        )
        cols = cur.keys()
        return [dict(zip(cols, row)) for row in cur.fetchall()]

@mcp.tool()
def summirize_expanse(start_date: str, end_date: str, category: str = ""):
    """Summarize expanse amounts by category."""

    query = """
    SELECT category, SUM(amount) AS total_amount
    FROM expanse
    WHERE date BETWEEN :start AND :end
    """

    params = {"start": start_date, "end": end_date}

    if category:
        query += " AND category = :category"
        params["category"] = category

    query += " GROUP BY category ORDER BY total_amount DESC"

    with engine.connect() as conn:
        cur = conn.execute(text(query), params)
        cols = cur.keys()
        return [dict(zip(cols, row)) for row in cur.fetchall()]

@mcp.tool()
def remove_expanse(expanse_id: int):
    """Remove an expanse record by ID."""

    query = "DELETE FROM expanse WHERE id = :id"

    with engine.begin() as conn:
        conn.execute(text(query), {"id": expanse_id})

    return {
        "status": "success",
        "message": f"Expanse with id {expanse_id} removed successfully."
    }

# -------------------- RESOURCE --------------------

@mcp.resource("expense://categories", mime_type="application/json")
def category_list():
    with open(category_Path, "r", encoding="utf-8") as f:
        return f.read()

# -------------------- RUN --------------------

if __name__ == "__main__":
    mcp.run()
