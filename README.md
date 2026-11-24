# Real-time AI Sales Dashboards

A store manager asks one plain-language question about sales.
The app checks the handbook, runs the numbers from the table, and shows the chart, the rows, and the formula used.

It is an initial check, not a replacement for a governed BI report.

## Why it helps

- No SQL. A manager types the question in everyday language.
- Numbers come only from code against the sales table. The model does not add or invent figures.
- A handbook formula is traced to the file name and page. If two handbooks disagree, the app lists both and does not calculate.

## Business scenario

Lane & Co. has stores in Kowloon, Hong Kong Island, and New Territories.
Categories are Beverage, Snacks, Household, and Fresh.

A manager sees that Kowloon looks weak this week and does not want to wait for the BI team.
They ask why. The app compares this week with last week, then drills into the weakest category.
If the question needs a defined metric, the app uses the handbook formula.
If it only asks what a handbook says, the app quotes the sentence and does not calculate.

## Flow

<img width="1168" height="784" alt="clean-professional-architecture-flowchart (1)" src="https://github.com/user-attachments/assets/9320365d-c836-4500-8b8b-acaedf186b90" />

```text
Question
  → Follow-up? Keep filters and the previous formula
  → Handbook match (vector search, top 5 passages)
      document → quote and stop
      conflict → list both formulas and stop
      metric found → use only that formula
      explore or not found → investigate
  → LangGraph
      explorer → planner
          refused → writer → end
          plan → coder
              error → coder again
              next step → advance → coder
              done → writer → end
```

Handbook matching and follow-up happen before LangGraph.
LangGraph only runs an investigation. It does not decide whether the question is a document question.

## Examples

**Investigate**

```text
why is Kowloon down this week
```

Compares this week with last week, then the weakest category.
Returns a chart, a table, and Finding / Evidence / Comparison / Limit.

**Handbook formula**

```text
October Kowloon Beverage unit margin
```

Uses the handbook definition, shows the formula and filters, then calculates.
The sentence is copied from the handbook, with the file name and page.

**Ask the handbook**

```text
what does the handbook say about credit cards
```

Quotes the handbook sentence. No chart and no calculation.

## Data

One DuckDB table, `sales`.

| | |
|---|---|
| Grain | One row per day, region, and category |
| Columns | date, year, month, weekday, region, category, sales, cost, units, orders |

Upload a CSV in the sidebar. The app cleans it, drops bad rows, derives year, month, and weekday, and loads `sales`.
The sidebar shows how many rows were read, kept, and deleted.

Upload one or more handbook PDFs. They are stored in `data/handbooks/`.

## Stack

Python, Streamlit, LangGraph, DeepSeek, Pydantic, DuckDB, Pandas, Plotly, pypdf, fastembed.

## How a question is answered

1. Follow-up check. A follow-up keeps the previous filters and formula. A changed field is replaced.
2. Handbook match. Pages are split into passages, embedded, and the top 5 are sent to the model. A copied sentence must appear in those passages.
3. Route. A document question quotes and stops. A formula conflict lists both sides and stops. A defined metric is injected into the question.
4. Explorer profiles the table. No model.
5. Planner writes 1 to 3 steps using only columns in the profile.
6. Coder writes a query. Python runs it against DuckDB. A failed step is retried once.
7. Writer reads the result tables only and writes Finding, Evidence, Comparison, and Limit.

## Setup

```powershell
python -m pip install -r requirements.txt
```

Put `DEEPSEEK_API_KEY` in a `.env` file next to `app.py`.

```powershell
streamlit run app.py
```

Upload a sales CSV, then any handbook PDFs. The first handbook question downloads the embedding model.

## Tests

| Question or action | Expected |
|---|---|
| Upload a CSV with bad rows | Sidebar shows read, kept, and deleted |
| `why is Kowloon down this week` | Chart and table, no handbook block |
| `what is unit margin` | Quote from the margins handbook, with file and page |
| `what does the handbook say about credit cards` | Quote from the banking handbook |
| A metric missing from every handbook | Labeled not in the handbook; formula, filters, and groups shown |
| Same metric, two different formulas | Conflict. No calculation |
| Follow-up `what about cost` | Same filters, column changed to cost |

## Limits

- This is a first check, not an official performance number.
- Chat history is kept for the open page only.
- The model can plan and quote. It cannot invent a column that is not in the table.
