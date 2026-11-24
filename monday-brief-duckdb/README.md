# Monday Brief

A store manager asks one question. Four agents answer it from a DuckDB table named `sales`.

Explorer reads the table. Planner decides how to answer and how many steps are needed (1 for a ranking, up to 3 for a "why"). Coder writes one read-only query and one chart per step, with one retry. Writer turns those tables into a four-part preliminary answer.

There is no CSV upload. The page always opens `data/sales.duckdb`.

## Run

```bash
cd monday-brief-duckdb
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# put DEEPSEEK_API_KEY in .env
python build_db.py
streamlit run app.py
```

`python build_db.py` loads `data/sample_sales.csv` into the `sales` table and prints the row count. Run it again only when you replace the CSV. Kowloon Beverage drops on Tuesday and Wednesday of the week of 20 Oct 2026.

```bash
python graph.py   # prints the graph, does not call the model
```

## Layout

```text
app.py         Streamlit page
graph.py       Explorer → Planner → Coder → advance → Writer
state.py       one investigation
explorer.py    column profile
planner.py     depth and steps
coder.py       one script, one chart
execute.py     runs that script in a temp folder
writer.py      Finding, Evidence, Comparison, Limit
data_io.py     read the sales table
db.py          open and build the DuckDB file
build_db.py    one-time load from the CSV
config.py      model, limits, and database path
```

## Limits

- Read-only. The generated script must open DuckDB with `read_only=True` and may only query `sales`.
- At most 3 rounds. A failed script is retried once.
- The writer is told to use only numbers present in the round tables.
- Questions about fields that are not in the file should be refused by the planner.
