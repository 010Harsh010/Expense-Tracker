from fastmcp import FastMCP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import json
import datetime
from typing import Optional
from typing import Annotated
from pydantic import Field
from fastmcp.exceptions import ToolError

load_dotenv()

DATABASE_URL = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

mcp = FastMCP(name="Expense Tracker",strict_input_validation=True)
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
@mcp.tool(
    name="add_expanse", description="Add a new expanse record to the database.",
    tags=["expense", "add"],
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "openWorldHint": True
    }    
)
def add_expanse(
    amount: Annotated[int,Field(description="The amount of the expanse in integer.")],
    category: Annotated[str,Field(description="The category of the expanse from the attached Resourse.")],
    subcategory: Annotated[Optional[str],Field(description="The subcategory of the expanse from the attached Resourse.")] = "",
    note: Annotated[Optional[str],Field(description="Additional note for the expanse.")] = "",
    date: Annotated[Optional[str],Field(description="The date of the expanse in YYYY-MM-DD format. If not provided, defaults to today's date.")] = ""
):
    """Add a new expanse record to the database."""

    # date = normalize_date(date)

    query = """
    INSERT INTO expanse (amount, category, subcategory, note, date)
    VALUES (:amount, :category, :subcategory, :note, :date)
    """

    date = datetime.datetime.strptime(date, "%Y-%m-%d").date() if date!="" else datetime.date.today()
    
    if amount < 0:
        raise ToolError("Amount must be a positive integer.")
    
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

@mcp.tool(
    name="get_expanse", description="Retrieve expanse records within a date range.",
    tags=["expense", "get"],
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "openWorldHint": True
    }
)
def get_expanse(start_date: Annotated[str,Field(description="The start date of the range in YYYY-MM-DD format.")] = datetime.date.today().strftime("%Y-%m-%d"), 
                end_date: Annotated[str,Field(description="The end date of the range in YYYY-MM-DD format.")]= datetime.date.today().strftime("%Y-%m-%d")):
    """Retrieve expanse records within a date range."""

    if start_date > end_date:
        raise ToolError("Start date must be before end date.")

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

@mcp.tool(
    name="summirize_expanse", description="Summarize expanse amounts by category.",
    tags=["expense", "summary"],
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "openWorldHint": True
    }
)
def summirize_expanse(start_date: Annotated[str,Field(description="The start date of the range in YYYY-MM-DD format.")] = datetime.date.today().strftime("%Y-%m-%d"), end_date: Annotated[str,Field(description="The end date of the range in YYYY-MM-DD format.")]= datetime.date.today().strftime("%Y-%m-%d"), category: Annotated[Optional[str],Field(description="The category to filter by. If not provided, summarizes all categories.")] = None):
    """Summarize expanse amounts by category."""

    if start_date > end_date:
        raise ToolError("Start date must be before end date.")

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

@mcp.tool(
    name="remove_expanse", description="Remove an expanse record by ID.",
    tags=["expense", "remove"],
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "openWorldHint": True
    }
)
def remove_expanse(expanse_id: Annotated[int,Field(description="The ID of the expanse record to remove.")]):
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
