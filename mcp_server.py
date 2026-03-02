# mcp_server.py
# MCP Server — exposes database tools + code execution + PDF/HTML generation + self-extending tools
#
#   TOOLS AVAILABLE (14 total):
#
#   DATABASE:
#     db_health_check      Check database connection
#     db_get_customers     Get all customers
#     db_get_products      Get all products
#     db_get_orders        Get all orders
#     db_run_query         Run custom SELECT query
#     db_get_schema        See table structures + sample data
#
#   CODE EXECUTION:
#     execute_analysis     Run Python code on full dataset (no restrictions)
#
#   REPORT GENERATION:
#     create_pdf_report    Create a styled PDF report
#     create_html_report   Create an HTML report with charts
#     list_reports         List all generated reports
#
#   SELF-EXTENDING TOOLS:
#     save_custom_tool     Save reusable analysis code to database
#     run_custom_tool      Load and run a previously saved tool
#     list_custom_tools    See all saved custom tools

import os
import io
import json
import uuid
import base64
import subprocess
import tempfile
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import asyncpg
from mcp.server.fastmcp import FastMCP

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL_READONLY")

# ---- Where generated reports are saved ----
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ---- Global database pool ----
db_pool = None


# ---- Lifespan ----
@asynccontextmanager
async def app_lifespan(server):
    """Start database pool when MCP server starts, close when it stops."""
    global db_pool
    print("MCP Server: Connecting to database...")
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    print("MCP Server: Database connected! Ready for tool calls.")
    print(f"MCP Server: Reports will be saved to {REPORTS_DIR}")
    yield
    await db_pool.close()
    print("MCP Server: Database pool closed.")


# ---- Create the MCP server ----
mcp = FastMCP(
    "hello_sql_mcp",
    lifespan=app_lifespan,
    host="0.0.0.0",
    port=8000,
)


# ---- Helper: run a query ----
async def run_db_query(sql: str) -> str:
    """Execute a read-only query and return results as JSON string."""
    async with db_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(sql)
    results = [dict(row) for row in rows]
    return json.dumps(results, indent=2, default=str)


# ====================================================================
#  DATABASE TOOLS
# ====================================================================

@mcp.tool(name="db_health_check")
async def db_health_check() -> str:
    """Check if the database connection is working."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
    return json.dumps({"status": "ok", "database": "connected", "test_query": result})


@mcp.tool(name="db_get_customers")
async def db_get_customers() -> str:
    """Get all customers from the database.
    Returns JSON array of customers with id, name, email, and city."""
    return await run_db_query("SELECT id, name, email, city FROM customers")


@mcp.tool(name="db_get_products")
async def db_get_products() -> str:
    """Get all products from the database.
    Returns JSON array of products with id, name, category, and price."""
    return await run_db_query("SELECT id, name, category, price FROM products")


@mcp.tool(name="db_get_orders")
async def db_get_orders() -> str:
    """Get all orders with customer and product names.
    Returns JSON array of orders with customer, product, quantity, status, order_date."""
    return await run_db_query("""
        SELECT c.name AS customer, p.name AS product,
               o.quantity, o.status, o.order_date
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        ORDER BY o.order_date DESC
    """)


@mcp.tool(name="db_run_query")
async def db_run_query(sql: str) -> str:
    """Run a custom SELECT query against the database.
    Only SELECT queries are allowed for safety.

    Args:
        sql: A SELECT query. Example: SELECT name FROM customers WHERE city = 'London'
    """
    sql = sql.strip()

    if not sql.upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are allowed."})

    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch(sql)
    except Exception as e:
        return json.dumps({"error": f"Query failed: {str(e)}"})

    results = [dict(row) for row in rows]
    return json.dumps(
        {"sql": sql, "row_count": len(results), "data": results},
        indent=2, default=str,
    )


# ====================================================================
#  SCHEMA TOOL — so Claude can see the data structure
# ====================================================================

@mcp.tool(name="db_get_schema")
async def db_get_schema() -> str:
    """Get the database schema (table names, columns, types) and 3 sample rows
    from each table. Use this FIRST to understand the data before writing queries.

    Returns:
        JSON with schema info and sample data for each table.
    """
    # Get all tables
    tables_json = await run_db_query("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)

    # Get sample rows from each table
    tables = json.loads(tables_json)
    table_names = list(set(t["table_name"] for t in tables))

    samples = {}
    for table in table_names:
        try:
            sample = await run_db_query(f"SELECT * FROM {table} LIMIT 3")
            samples[table] = json.loads(sample)
        except Exception:
            samples[table] = []

    # Get row counts
    counts = {}
    for table in table_names:
        try:
            count_json = await run_db_query(f"SELECT COUNT(*) as count FROM {table}")
            counts[table] = json.loads(count_json)[0]["count"]
        except Exception:
            counts[table] = "unknown"

    return json.dumps({
        "schema": tables,
        "sample_data": samples,
        "row_counts": counts,
    }, indent=2, default=str)


# ====================================================================
#  PYTHON CODE EXECUTION TOOL
# ====================================================================

@mcp.tool(name="execute_analysis")
async def execute_analysis(python_code: str, query: str = "SELECT 1") -> str:
    """Execute Python analysis code against database query results.

    Claude writes Python code with a function called `analyze(rows)`.
    This tool runs the query, passes the rows to analyze(), and returns the result.

    The analyze function receives a list of dicts (each dict is a row).
    It must return a JSON-serializable value (dict, list, number, string).

    Args:
        python_code: Python code that defines `def analyze(rows): ...`
                     Example:
                       def analyze(rows):
                           total = sum(r['price'] * r['quantity'] for r in rows)
                           return {"total_revenue": total}

        query: SQL SELECT query to get the data to analyze.
               Example: SELECT * FROM orders o JOIN products p ON o.product_id = p.id
    """
    query = query.strip()
    if not query.upper().startswith("SELECT"):
        return json.dumps({"error": "Query must start with SELECT"})

    # NOTE: All Python operations are allowed (os, subprocess, open, exec, eval, etc.)
    # Safety boundary is Docker container isolation — code runs in sandboxed subprocess.

    # Fetch data from database
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch(query)
        data = [dict(row) for row in rows]
    except Exception as e:
        return json.dumps({"error": f"Query failed: {str(e)}"})

    # Build the execution script
    script = f"""
import json
from datetime import datetime, date
from decimal import Decimal

# Make data JSON-safe
def make_serializable(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return obj

def clean_rows(rows):
    return [{{k: make_serializable(v) for k, v in r.items()}} for r in rows]

# Claude's analysis code
{python_code}

# Run it
rows = json.loads('''{json.dumps(data, default=str)}''')
rows = clean_rows(rows)
result = analyze(rows)
print(json.dumps(result, default=str))
"""

    # Write to temp file and execute in subprocess (sandboxed)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        f.flush()
        temp_path = f.name

    try:
        result = subprocess.run(
            ["python3", temp_path],
            capture_output=True, text=True,
            timeout=120,  # kill after 120 seconds
        )

        if result.returncode != 0:
            return json.dumps({
                "error": "Code execution failed",
                "stderr": result.stderr[:1000],
            })

        return json.dumps({
            "status": "success",
            "result": json.loads(result.stdout),
            "rows_processed": len(data),
        }, indent=2, default=str)

    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Code took too long (120 second limit)"})
    except json.JSONDecodeError:
        # If output isn't valid JSON, return as raw text
        return json.dumps({
            "status": "success",
            "result_text": result.stdout[:2000],
            "rows_processed": len(data),
        })
    finally:
        os.unlink(temp_path)


# ====================================================================
#  PDF REPORT TOOL
# ====================================================================

@mcp.tool(name="create_pdf_report")
async def create_pdf_report(
    title: str,
    filename: str,
    content_sections: str,
    table_data: str = "[]",
    table_headers: str = "[]",
) -> str:
    """Create a styled PDF report and return it as base64.

    Args:
        title: Report title displayed at the top.
               Example: "Monthly Sales Report"

        filename: Meaningful filename for the PDF (without .pdf extension).
                  Use lowercase with underscores.
                  Example: "monthly_sales_report_jan_2025"

        content_sections: JSON array of sections, each with "heading" and "body".
               Example: [{"heading": "Summary", "body": "Total revenue was $5000..."}]

        table_data: Optional JSON array of arrays for a data table.
               Example: [["Alice", "$500"], ["Bob", "$300"]]

        table_headers: Optional JSON array of column headers for the table.
               Example: ["Customer", "Total Spent"]
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable,
        )
    except ImportError:
        return json.dumps({"error": "reportlab not installed. Run: pip install reportlab"})

    sections = json.loads(content_sections)
    t_data = json.loads(table_data)
    t_headers = json.loads(table_headers)

    # Clean filename — keep only safe characters
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in filename)
    safe_name = safe_name.strip().replace(" ", "_").lower()
    if not safe_name:
        safe_name = f"report_{uuid.uuid4().hex[:8]}"
    filename = f"{safe_name}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    # Create PDF
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=25 * mm, rightMargin=25 * mm,
        topMargin=25 * mm, bottomMargin=25 * mm,
    )

    # Custom styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"],
        fontSize=26, textColor=HexColor("#1a1a2e"),
        spaceAfter=6, fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#6b7385"),
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        "CustomHeading", parent=styles["Heading2"],
        fontSize=16, textColor=HexColor("#1a1a2e"),
        spaceBefore=20, spaceAfter=8,
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "CustomBody", parent=styles["Normal"],
        fontSize=11, textColor=HexColor("#333340"),
        leading=16, spaceAfter=12,
    )

    # Build story (reportlab term for page content)
    story = []

    # Title
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        subtitle_style,
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=HexColor("#4b8df8"), spaceAfter=20,
    ))

    # Content sections
    for section in sections:
        heading = section.get("heading", "")
        body = section.get("body", "")
        if heading:
            story.append(Paragraph(heading, heading_style))
        if body:
            for para in body.split("\n"):
                if para.strip():
                    story.append(Paragraph(para.strip(), body_style))
        story.append(Spacer(1, 8))

    # Table (if provided)
    if t_headers and t_data:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Data Table", heading_style))

        full_table = [t_headers] + t_data
        table = Table(full_table, repeatRows=1)
        table.setStyle(TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#4b8df8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            # Data rows
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
            ("TOPPADDING", (0, 1), (-1, -1), 7),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#d0d0e0")),
            # Alternating row colors
            *[("BACKGROUND", (0, i), (-1, i), HexColor("#f4f6fb"))
              for i in range(2, len(full_table), 2)],
            # Alignment
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(table)

    # Footer
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#d0d0e0")))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, textColor=HexColor("#999999"),
        alignment=TA_CENTER, spaceBefore=8,
    )
    story.append(Paragraph(
        "Generated by AI Database Chat &middot; Powered by Claude + MCP",
        footer_style,
    ))

    # Build PDF
    doc.build(story)

    # Read and encode as base64
    with open(filepath, "rb") as f:
        pdf_bytes = f.read()

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    return json.dumps({
        "status": "pdf_created",
        "filename": filename,
        "filepath": filepath,
        "size_kb": round(len(pdf_bytes) / 1024, 1),
        "download_url": f"/reports/{filename}",
    })


# ====================================================================
#  HTML REPORT TOOL
# ====================================================================

@mcp.tool(name="create_html_report")
async def create_html_report(
    title: str,
    filename: str,
    summary: str,
    chart_type: str,
    labels_json: str,
    values_json: str,
    table_data: str = "[]",
    table_headers: str = "[]",
    extra_html: str = "",
) -> str:
    """Create a beautiful HTML report with interactive Chart.js chart and optional table.

    Args:
        title: Report title. Example: "Monthly Sales Report"

        filename: Meaningful filename for the HTML report (without .html extension).
                  Use lowercase with underscores.
                  Example: "product_sales_chart_feb_2025"

        summary: Text summary of findings. Can include multiple paragraphs.

        chart_type: Chart type — one of: bar, line, pie, doughnut, scatter, radar

        labels_json: JSON array of chart labels. Example: ["Jan","Feb","Mar"]

        values_json: JSON array of chart values. Example: [100, 200, 300]
                     For multiple datasets, use JSON array of arrays:
                     [[100,200,300],[50,80,120]]

        table_data: Optional JSON 2D array for a data table.
                    Example: [["Alice","$500","London"],["Bob","$300","Sydney"]]

        table_headers: Optional JSON array of column headers.
                       Example: ["Customer","Total","City"]

        extra_html: Optional additional HTML to insert after the chart.
    """
    labels = json.loads(labels_json)
    values = json.loads(values_json)
    t_data = json.loads(table_data)
    t_headers = json.loads(table_headers)

    # Colors for charts
    colors = [
        "rgba(75,141,248,0.8)", "rgba(56,189,248,0.8)", "rgba(52,211,153,0.8)",
        "rgba(251,191,36,0.8)", "rgba(248,113,113,0.8)", "rgba(167,139,250,0.8)",
        "rgba(251,146,60,0.8)", "rgba(45,212,191,0.8)",
    ]
    border_colors = [c.replace("0.8", "1") for c in colors]

    # Handle single or multiple datasets
    if values and isinstance(values[0], list):
        datasets_js = ",".join([
            f"""{{
                label: 'Dataset {i+1}',
                data: {json.dumps(ds)},
                backgroundColor: '{colors[i % len(colors)]}',
                borderColor: '{border_colors[i % len(border_colors)]}',
                borderWidth: 2,
                fill: {'true' if chart_type == 'line' else 'false'}
            }}""" for i, ds in enumerate(values)
        ])
    else:
        datasets_js = f"""{{
            label: '{title}',
            data: {json.dumps(values)},
            backgroundColor: {json.dumps(colors[:len(values)])},
            borderColor: {json.dumps(border_colors[:len(values)])},
            borderWidth: 2,
            fill: {'true' if chart_type == 'line' else 'false'}
        }}"""

    # Build table HTML
    table_html = ""
    if t_headers and t_data:
        header_cells = "".join(f"<th>{h}</th>" for h in t_headers)
        rows_html = ""
        for row in t_data:
            cells = "".join(f"<td>{cell}</td>" for cell in row)
            rows_html += f"<tr>{cells}</tr>"
        table_html = f"""
        <div class="section">
            <h2>Data Table</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr>{header_cells}</tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </div>"""

    # Is it a circular chart? (pie/doughnut have no x/y axes)
    is_circular = chart_type in ("pie", "doughnut")

    # Build summary paragraphs
    summary_html = "<br><br>".join(
        p.strip() for p in summary.split("\n") if p.strip()
    )

    # Build scales JS (circular charts like pie/doughnut have no axes)
    if is_circular:
        scales_js = "{}"
    else:
        scales_js = """{
            x: {
                ticks: { color: '#6b7385', font: { family: 'Outfit' } },
                grid: { color: '#1a2035' }
            },
            y: {
                ticks: { color: '#6b7385', font: { family: 'Outfit' } },
                grid: { color: '#1a2035' }
            }
        }"""

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{
    font-family:'Outfit',sans-serif;
    background:#06080d;
    color:#e4e8f1;
    padding:0;
    min-height:100vh;
}}
.report{{
    max-width:900px;
    margin:0 auto;
    padding:40px 32px;
}}
.report-header{{
    margin-bottom:32px;
    padding-bottom:20px;
    border-bottom:2px solid #4b8df8;
}}
.report-header h1{{
    font-size:28px;
    font-weight:700;
    letter-spacing:-0.5px;
    margin-bottom:6px;
}}
.report-header .meta{{
    font-size:12px;
    color:#6b7385;
}}
.section{{
    background:#111520;
    border:1px solid #1a2035;
    border-radius:14px;
    padding:24px;
    margin-bottom:24px;
}}
.section h2{{
    font-size:18px;
    font-weight:600;
    margin-bottom:14px;
    color:#38bdf8;
}}
.summary-text{{
    line-height:1.8;
    font-size:14px;
    color:#b8bfce;
}}
.chart-box{{
    position:relative;
    height:{'360px' if is_circular else '400px'};
    max-width:{'500px' if is_circular else '100%'};
    margin:{'0 auto' if is_circular else '0'};
}}
.table-wrap{{overflow-x:auto}}
table{{
    width:100%;
    border-collapse:collapse;
    font-size:13px;
}}
th{{
    background:#1a2035;
    color:#38bdf8;
    font-weight:600;
    font-size:11px;
    text-transform:uppercase;
    letter-spacing:0.5px;
    padding:10px 14px;
    text-align:left;
    border-bottom:2px solid #253050;
}}
td{{
    padding:9px 14px;
    border-bottom:1px solid #1a2035;
    color:#b8bfce;
}}
tr:hover td{{background:rgba(75,141,248,0.04)}}
.footer{{
    text-align:center;
    font-size:11px;
    color:#3d4456;
    margin-top:40px;
    padding-top:20px;
    border-top:1px solid #1a2035;
}}
</style>
</head>
<body>
<div class="report">
    <div class="report-header">
        <h1>{title}</h1>
        <div class="meta">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} &middot; AI Database Chat</div>
    </div>

    <div class="section">
        <h2>Summary</h2>
        <div class="summary-text">{summary_html}</div>
    </div>

    <div class="section">
        <h2>Chart</h2>
        <div class="chart-box">
            <canvas id="mainChart"></canvas>
        </div>
    </div>

    {table_html}

    <div class="footer">Generated by AI Database Chat &middot; Powered by Claude + MCP</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
new Chart(document.getElementById('mainChart'), {{
    type: '{chart_type}',
    data: {{
        labels: {json.dumps(labels)},
        datasets: [{datasets_js}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{
                labels: {{ color: '#b8bfce', font: {{ family: 'Outfit', size: 12 }} }}
            }}
        }},
        scales: {scales_js}
    }}
}});
</script>
{extra_html}
</body>
</html>"""

    # Clean filename — keep only safe characters
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in filename)
    safe_name = safe_name.strip().replace(" ", "_").lower()
    if not safe_name:
        safe_name = f"report_{uuid.uuid4().hex[:8]}"
    filename = f"{safe_name}.html"
    filepath = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_html)

    return json.dumps({
        "status": "html_report_created",
        "filename": filename,
        "filepath": filepath,
        "download_url": f"/reports/{filename}",
    })


# ====================================================================
#  LIST GENERATED REPORTS
# ====================================================================

@mcp.tool(name="list_reports")
async def list_reports() -> str:
    """List all generated reports (PDF and HTML files in the reports directory).

    Returns:
        JSON array of report files with name, type, size, and creation time.
    """
    reports = []
    if os.path.exists(REPORTS_DIR):
        for fname in sorted(os.listdir(REPORTS_DIR), reverse=True):
            fpath = os.path.join(REPORTS_DIR, fname)
            if os.path.isfile(fpath):
                stat = os.stat(fpath)
                reports.append({
                    "filename": fname,
                    "type": "pdf" if fname.endswith(".pdf") else "html",
                    "size_kb": round(stat.st_size / 1024, 1),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "download_url": f"/reports/{fname}",
                })

    return json.dumps({"reports": reports, "total": len(reports)}, indent=2)


# ====================================================================
#  CUSTOM TOOLS — Self-Extending Tool System
#  Claude can save reusable Python analysis tools to the database
#  and run them later without rewriting the code.
# ====================================================================

@mcp.tool(name="save_custom_tool")
async def save_custom_tool(
    name: str,
    description: str,
    python_code: str,
    sql_query: str = "SELECT 1",
) -> str:
    """Save a reusable Python analysis tool to the database for future use.

    When you write useful analysis code in execute_analysis, save it here
    so you can reuse it next time without rewriting.

    Args:
        name: Short unique name for the tool (lowercase, underscores).
              Example: "revenue_by_product"

        description: What this tool does — be specific so you can find it later.
                     Example: "Calculate total revenue grouped by product name"

        python_code: The Python code with def analyze(rows): ...
                     This is the same format as execute_analysis.
                     Example:
                       def analyze(rows):
                           products = {}
                           for r in rows:
                               name = r['product_name']
                               rev = float(r['price']) * int(r['quantity'])
                               products[name] = products.get(name, 0) + rev
                           return dict(sorted(products.items(), key=lambda x: x[1], reverse=True))

        sql_query: The SQL query that fetches data for this tool.
                   Example: SELECT o.quantity, p.price, p.name as product_name FROM orders o JOIN products p ON o.product_id = p.id
    """
    # Clean the name
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name.lower())
    safe_name = safe_name.strip("_")
    if not safe_name:
        return json.dumps({"error": "Tool name cannot be empty"})

    try:
        async with db_pool.acquire() as conn:
            # Check if tool already exists — update it
            existing = await conn.fetchval(
                "SELECT id FROM custom_tools WHERE name = $1", safe_name
            )
            if existing:
                await conn.execute(
                    """UPDATE custom_tools
                       SET description = $1, python_code = $2, sql_query = $3, created_at = NOW()
                       WHERE name = $4""",
                    description, python_code, sql_query, safe_name,
                )
                return json.dumps({
                    "status": "updated",
                    "name": safe_name,
                    "message": f"Tool '{safe_name}' updated successfully.",
                })
            else:
                await conn.execute(
                    """INSERT INTO custom_tools (name, description, python_code, sql_query)
                       VALUES ($1, $2, $3, $4)""",
                    safe_name, description, python_code, sql_query,
                )
                return json.dumps({
                    "status": "saved",
                    "name": safe_name,
                    "message": f"Tool '{safe_name}' saved! Use run_custom_tool('{safe_name}') to run it.",
                })

    except Exception as e:
        return json.dumps({"error": f"Failed to save tool: {str(e)}"})


@mcp.tool(name="run_custom_tool")
async def run_custom_tool(name: str) -> str:
    """Load and run a previously saved custom tool from the database.

    This retrieves the saved Python code and SQL query, executes the query,
    and runs the analysis — exactly like execute_analysis but using saved code.

    Args:
        name: The name of the saved tool to run.
              Example: "revenue_by_product"
    """
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT python_code, sql_query FROM custom_tools WHERE name = $1", name
            )
            if not row:
                # Try fuzzy search
                matches = await conn.fetch(
                    "SELECT name, description FROM custom_tools WHERE name ILIKE $1 OR description ILIKE $1",
                    f"%{name}%",
                )
                if matches:
                    suggestions = [f"  - {m['name']}: {m['description']}" for m in matches]
                    return json.dumps({
                        "error": f"Tool '{name}' not found. Did you mean one of these?",
                        "suggestions": suggestions,
                    })
                return json.dumps({"error": f"Tool '{name}' not found. Use list_custom_tools to see available tools."})

            python_code = row["python_code"]
            sql_query = row["sql_query"]

            # Update usage stats
            await conn.execute(
                "UPDATE custom_tools SET last_used_at = NOW(), use_count = use_count + 1 WHERE name = $1",
                name,
            )

    except Exception as e:
        return json.dumps({"error": f"Failed to load tool: {str(e)}"})

    # Now run it — same logic as execute_analysis
    sql_query = sql_query.strip()
    if not sql_query.upper().startswith("SELECT"):
        return json.dumps({"error": "Saved query must start with SELECT"})

    # Fetch data
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch(sql_query)
        data = [dict(row) for row in rows]
    except Exception as e:
        return json.dumps({"error": f"Query failed: {str(e)}"})

    # Build execution script
    script = f"""
import json
from datetime import datetime, date
from decimal import Decimal

def make_serializable(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return obj

def clean_rows(rows):
    return [{{k: make_serializable(v) for k, v in r.items()}} for r in rows]

# Saved tool code
{python_code}

# Run it
rows = json.loads('''{json.dumps(data, default=str)}''')
rows = clean_rows(rows)
result = analyze(rows)
print(json.dumps(result, default=str))
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        f.flush()
        temp_path = f.name

    try:
        result = subprocess.run(
            ["python3", temp_path],
            capture_output=True, text=True,
            timeout=120,
        )

        if result.returncode != 0:
            return json.dumps({
                "error": "Saved tool execution failed",
                "tool_name": name,
                "stderr": result.stderr[:1000],
            })

        return json.dumps({
            "status": "success",
            "tool_name": name,
            "result": json.loads(result.stdout),
            "rows_processed": len(data),
        }, indent=2, default=str)

    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Tool '{name}' took too long (120 second limit)"})
    except json.JSONDecodeError:
        return json.dumps({
            "status": "success",
            "tool_name": name,
            "result_text": result.stdout[:2000],
            "rows_processed": len(data),
        })
    finally:
        os.unlink(temp_path)


@mcp.tool(name="list_custom_tools")
async def list_custom_tools() -> str:
    """List all saved custom tools from the database.

    Returns:
        JSON array of saved tools with name, description, usage stats.
    """
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT name, description, sql_query, created_at, last_used_at, use_count
                   FROM custom_tools ORDER BY use_count DESC, created_at DESC"""
            )

        tools = []
        for row in rows:
            tools.append({
                "name": row["name"],
                "description": row["description"],
                "sql_query": row["sql_query"][:100] + "..." if len(row["sql_query"]) > 100 else row["sql_query"],
                "created": row["created_at"].isoformat() if row["created_at"] else None,
                "last_used": row["last_used_at"].isoformat() if row["last_used_at"] else "never",
                "use_count": row["use_count"],
            })

        return json.dumps({
            "tools": tools,
            "total": len(tools),
            "tip": "Use run_custom_tool('name') to run any saved tool.",
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": f"Failed to list tools: {str(e)}"})


# ====================================================================
#  RUN
# ====================================================================
if __name__ == "__main__":
    mcp.run(transport="sse")
