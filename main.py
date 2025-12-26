from fastmcp import FastMCP
import sqlite3

mcp = FastMCP(name="Expense Tracker")

DB_PATH = "db.sqlite"
category_Path = "category.json"

# @mcp.tool
# def roll_dice(n:int = 1):
#     import random
#     return[random.randint(1, 6) for _ in range(n)]

# @mcp.tool
# def add(x:int=0, y:int=0):
#     return x + y

def init_db():
    """Initialize the database and create the expanse table if it doesn't exist."""
    query = "create table if not exists expanse (id integer primary key autoincrement, amount integer not null, category text not null,subcategory text default '', note text default '', date text not null);"
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(query)
    print("Database initialized.")

init_db()

@mcp.tool()
def add_expanse(amount:int = 0, category:str='', subcategory:str='', note:str='', date:str = ''):
    """Add a new expanse record to the database."""
    query = "insert into expanse (amount, category, subcategory, note, date) values (?, ?, ?, ?, ?);"
    with sqlite3.connect(DB_PATH) as conn:
        cor = conn.execute(query, (amount, category, subcategory, note, date))
        return {
            "status": "success",
            "message": "Expanse added successfully.",
            "id": cor.lastrowid
        }
        
@mcp.tool()
def get_expanse(start_date:str = '', end_date:str = ''):
    """Retrieve expanse records within a specified date range."""
    query = "select * from expanse where date between ? and ? order by id asc;"
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(query, (start_date, end_date))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    
    
@mcp.tool()
def summirize_expanse(start_date:str = '', end_date:str = '',category:str=''):
    """Summarize expanse amounts by category."""
    params = [start_date, end_date]
    query = "select category,sum(amount) as total_amount from expanse where date between ? and ?"
    if category:
        query += " where category = ?"
        params.append(category)
    query += " group by category order by total_amount desc;"
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def remove_expanse(expanse_id:int = 0):
    """Remove an expanse record by its ID."""
    query = "delete from expanse where id = ?;"
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(query, (expanse_id,))
        return {
            "status": "success",
            "message": f"Expanse with id {expanse_id} removed successfully."
        }
        
@mcp.resource("expense://categories", mime_type="application/json")
def category_list():
    """Retrieve the list of categories from the JSON file."""
    import json
    with open(category_Path,'r' ,encoding="utf-8") as f:
        return f.read()
    
if __name__ == "__main__":
    mcp.run()