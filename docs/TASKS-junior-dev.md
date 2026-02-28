# NL-SQL Tool — Junior Developer Task List

> **Who is this for?** You are brand new. You may have written some Python, but you've never used Docker, never called an API, and never built a web app. Every task below tells you WHAT to do, WHY you're doing it, and HOW to know it worked.

---

## How to Use This List

- Do tasks **in order**. Each one builds on the last.
- **Do NOT skip ahead.** If something breaks, fix it before moving on.
- Each task has a **"Done when"** section — that's how you know it worked.
- If you get stuck on a task for more than 30 minutes, search the error message on Google/StackOverflow.

---

## PHASE 0: Baby Steps — Prove Your Tools Work

> **Why this phase?** Before building anything real, you need to make sure Docker and Python actually work on your machine. These tasks are throwaway — their only purpose is to build your confidence.

---

### Task 0.1: Install Docker Desktop

**What:** Install Docker on your computer.

**Why:** Docker lets you run programs inside tiny virtual computers called "containers." Instead of installing PostgreSQL, Python servers, etc. directly on your machine (which can break things), you run them inside containers. If something goes wrong, you delete the container and start fresh. Your computer stays clean.

**Steps:**
1. Go to https://www.docker.com/products/docker-desktop/
2. Download Docker Desktop for your OS (Windows/Mac/Linux)
3. Run the installer — accept all defaults
4. **Windows users:** If it asks about WSL2, say YES
5. Restart your computer when asked
6. Open Docker Desktop
7. Wait until it says "Docker is running" (green icon or green bar at bottom-left)

**Test it — open a terminal and run:**
```bash
docker --version
```

**Done when:** You see something like `Docker version 24.x.x` or `Docker version 27.x.x`. The exact number doesn't matter — any version means it's installed.

---

### Task 0.2: Run Your First Docker Container (Hello World)

**What:** Run Docker's built-in test container.

**Why:** This proves Docker can download images from the internet and run containers. If this works, Docker is set up correctly. Think of a "Docker image" as a recipe, and a "container" as the meal cooked from that recipe.

**Steps — run this in your terminal:**
```bash
docker run hello-world
```

**What happens behind the scenes:**
1. Docker looks for an image called `hello-world` on your computer — doesn't find it
2. Docker downloads it from Docker Hub (like an app store for containers)
3. Docker creates a container from that image and runs it
4. The container prints a message and exits

**Done when:** You see the message `Hello from Docker!` in your terminal. If you see an error about permissions, try running the command with `sudo` (Linux/Mac) or make sure Docker Desktop is running (Windows).

---

### Task 0.3: Run a Python "Hello World" Inside Docker

**What:** Run a single Python command inside a Docker container.

**Why:** This proves you can run Python inside Docker without installing Python on your machine. The container has Python pre-installed.

**Steps — run this in your terminal:**
```bash
docker run python:3.12-slim python -c "print('Hello from Python inside Docker!')"
```

**What this command means:**
| Part | Meaning |
|------|---------|
| `docker run` | Create and start a new container |
| `python:3.12-slim` | Use the official Python 3.12 image (slim = smaller download) |
| `python -c "print(...)"` | Run this Python code inside the container |

**First time is slow** (1-2 minutes) because Docker downloads the Python image (~50MB). Second time is instant.

**Done when:** You see `Hello from Python inside Docker!` printed in your terminal.

---

### Task 0.4: Run a Python Script File Inside Docker

**What:** Create a Python file on YOUR computer and run it inside a Docker container.

**Why:** This is the bridge between "your files" and "Docker." You'll learn how to share files between your computer and a container using "volumes." This is a core Docker concept you'll use for the rest of the project.

**Steps:**

1. Create the project folder:
```bash
mkdir nl-sql-tool
cd nl-sql-tool
```

2. Create a file called `hello.py` with this content:
```python
# hello.py
print("=" * 40)
print("  Hello from a Python FILE in Docker!")
print("  This file lives on my computer")
print("  but it's running INSIDE a container")
print("=" * 40)

import sys
print(f"\nPython version: {sys.version}")
print(f"Running on: {sys.platform}")
```

3. Run it inside Docker:
```bash
docker run --rm -v "$(pwd)":/app -w /app python:3.12-slim python hello.py
```

**What each flag means:**
| Flag | Meaning |
|------|---------|
| `--rm` | Delete the container after it stops (keeps things clean) |
| `-v "$(pwd)":/app` | Mount (share) your current folder into `/app` inside the container |
| `-w /app` | Set the working directory inside the container to `/app` |
| `python:3.12-slim` | The Docker image to use |
| `python hello.py` | The command to run inside the container |

**Done when:** You see the hello message AND `Running on: linux` — even though you might be on Windows or Mac! That's because the container runs Linux inside.

---

### Task 0.5: Understand docker-compose with a Minimal Example

**What:** Create a `docker-compose.yml` file that runs your hello.py script.

**Why:** In Task 0.4 you typed a long `docker run` command with lots of flags. `docker-compose` lets you save all those settings in a file so you just type `docker compose up`. For our project, we'll have multiple containers (database + app), and docker-compose manages them all.

**Steps:**

1. Create `docker-compose.hello.yml` in your `nl-sql-tool/` folder:
```yaml
# docker-compose.hello.yml
# This is a LEARNING example — we'll delete this later

version: "3.9"

services:
  hello:
    image: python:3.12-slim
    volumes:
      - .:/app          # Share current folder into /app
    working_dir: /app
    command: python hello.py
```

2. Run it:
```bash
docker compose -f docker-compose.hello.yml up
```

**What each line means:**
| Line | Meaning |
|------|---------|
| `version: "3.9"` | The docker-compose file format version |
| `services:` | The list of containers to run |
| `hello:` | A name for this container (you pick the name) |
| `image: python:3.12-slim` | Which Docker image to use |
| `volumes: - .:/app` | Share your project folder into the container |
| `working_dir: /app` | Where to start inside the container |
| `command: python hello.py` | What to run |

3. After it works, stop it with `Ctrl+C` and clean up:
```bash
docker compose -f docker-compose.hello.yml down
```

**Done when:** You see your hello.py output in the terminal. You now understand what docker-compose does — it replaces long `docker run` commands with a simple file.

---

### Task 0.6: Clean Up Phase 0

**What:** Delete the practice files. Keep the project folder.

**Why:** These were learning files. The real project starts in Phase 1.

**Steps:**
```bash
# From inside nl-sql-tool/
rm hello.py
rm docker-compose.hello.yml
```

**Done when:** Your `nl-sql-tool/` folder is empty and clean.

---

## PHASE 1: Database in Docker

> **Why this phase?** Every app needs somewhere to store data. We'll run a PostgreSQL database inside Docker and fill it with sample data (customers, products, orders). By the end, you'll have a working database you can query.

---

### Task 1.1: Create docker-compose.yml with PostgreSQL

**What:** Create the main `docker-compose.yml` file that runs a PostgreSQL database.

**Why:** PostgreSQL is the database where all our data lives. We're running it in Docker so you don't need to install PostgreSQL on your machine. This file tells Docker: "Download PostgreSQL, create a database called `shopdb`, set up a user and password, and keep the data safe between restarts."

**Steps:**

1. Make sure you're inside `nl-sql-tool/`
2. Create `docker-compose.yml` with this content:

```yaml
# docker-compose.yml

version: "3.9"

services:
  db:
    image: postgres:16
    container_name: nl_sql_db
    restart: unless-stopped

    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret123
      POSTGRES_DB: shopdb

    ports:
      - "5432:5432"

    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin -d shopdb"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

**What every important line does:**
| Line | Meaning |
|------|---------|
| `image: postgres:16` | Download and use the official PostgreSQL 16 image |
| `container_name: nl_sql_db` | Give the container a friendly name (used in other commands) |
| `POSTGRES_USER: admin` | Create a database user called "admin" |
| `POSTGRES_PASSWORD: secret123` | Set the password (change this in real projects!) |
| `POSTGRES_DB: shopdb` | Create a database called "shopdb" |
| `ports: "5432:5432"` | Your computer's port 5432 connects to the container's port 5432 |
| `volumes: pgdata:...` | Save database files so data survives container restarts |
| `volumes: ./init-scripts:...` | Any `.sql` files in the `init-scripts/` folder run automatically on FIRST start |
| `healthcheck` | Docker checks every 5 seconds if PostgreSQL is ready |

**Done when:** The file exists at `nl-sql-tool/docker-compose.yml`. Don't run it yet — we need the init script first.

---

### Task 1.2: Create the Database Init Script

**What:** Create a SQL file that automatically creates tables and fills them with sample data when the database starts for the first time.

**Why:** Instead of manually creating tables every time, PostgreSQL in Docker has a special feature: any `.sql` files placed in `/docker-entrypoint-initdb.d/` run automatically on first start. This means our database comes pre-loaded with data — ready to query immediately.

**Steps:**

1. Create the folder:
```bash
mkdir init-scripts
```

2. Create `init-scripts/01-create-tables.sql` with this content:

```sql
-- init-scripts/01-create-tables.sql
-- This runs AUTOMATICALLY the first time the database starts

-- Create a read-only user (for security — the app will use this user)
CREATE USER readonly_user WITH PASSWORD 'readonly123';

-- Customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    city VARCHAR(50),
    joined_date DATE DEFAULT CURRENT_DATE
);

-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price NUMERIC(10, 2) NOT NULL
);

-- Orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pending',
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample customers
INSERT INTO customers (name, email, city) VALUES
    ('Alice Smith', 'alice@email.com', 'London'),
    ('Bob Jones', 'bob@email.com', 'Sydney'),
    ('Charlie Brown', 'charlie@email.com', 'Perth'),
    ('Diana Prince', 'diana@email.com', 'Melbourne'),
    ('Eve Wilson', 'eve@email.com', 'Brisbane');

-- Insert sample products
INSERT INTO products (name, category, price) VALUES
    ('Laptop', 'Electronics', 999.99),
    ('Headphones', 'Electronics', 79.99),
    ('Coffee Maker', 'Kitchen', 49.99),
    ('Running Shoes', 'Sports', 129.99),
    ('Notebook', 'Stationery', 12.99);

-- Insert sample orders
INSERT INTO orders (customer_id, product_id, quantity, status, order_date) VALUES
    (1, 1, 1, 'delivered', '2025-01-15'),
    (1, 2, 2, 'delivered', '2025-01-20'),
    (2, 3, 1, 'shipped', '2025-02-01'),
    (3, 4, 1, 'pending', '2025-02-10'),
    (4, 1, 1, 'delivered', '2025-02-12'),
    (4, 5, 3, 'shipped', '2025-02-14'),
    (5, 2, 1, 'pending', '2025-02-20'),
    (2, 1, 1, 'cancelled', '2025-02-22'),
    (3, 3, 2, 'delivered', '2025-02-25'),
    (1, 4, 1, 'shipped', '2025-02-27');

-- Give read-only user permissions
GRANT CONNECT ON DATABASE shopdb TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

-- Table to store visualizations later (Milestone 7)
CREATE TABLE saved_visualizations (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    chart_type VARCHAR(50),
    chart_script TEXT,
    chart_image BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

GRANT SELECT, INSERT ON saved_visualizations TO readonly_user;
GRANT USAGE ON SEQUENCE saved_visualizations_id_seq TO readonly_user;
```

**What this script does in plain English:**
- Creates 3 main tables: `customers`, `products`, `orders`
- Fills them with fake sample data (5 customers, 5 products, 10 orders)
- Creates a special `readonly_user` that can READ data but CANNOT change or delete it (security!)
- Creates a `saved_visualizations` table for storing charts later

**Done when:** The file exists at `nl-sql-tool/init-scripts/01-create-tables.sql`.

---

### Task 1.3: Start the Database and Verify It Works

**What:** Start PostgreSQL in Docker and make sure all tables and data were created.

**Why:** This is the moment of truth for Phase 1. If the database starts, the init script ran, and you can query data — you have a working database.

**Steps:**

1. Start the database:
```bash
docker compose up -d
```
(`-d` means "run in the background" so you get your terminal back)

2. Wait 10-20 seconds, then check it's running:
```bash
docker compose ps
```
You should see:
```
NAME          STATUS
nl_sql_db     Up (healthy)
```
If it says "starting" or "unhealthy", wait 30 seconds and check again.

3. Connect to the database:
```bash
docker exec -it nl_sql_db psql -U admin -d shopdb
```
You should see a prompt like: `shopdb=#`

4. Test these queries one by one (type each one and press Enter):
```sql
-- See all tables
\dt

-- See all customers
SELECT * FROM customers;

-- See all products
SELECT * FROM products;

-- See orders with customer and product names
SELECT c.name, p.name AS product, o.quantity, o.status
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN products p ON o.product_id = p.id;
```

5. Test read-only security:
```sql
SET ROLE readonly_user;
SELECT * FROM customers;
-- ^ This should WORK

INSERT INTO customers (name, email) VALUES ('Hacker', 'hack@evil.com');
-- ^ This should FAIL with "permission denied"

RESET ROLE;
```

6. Exit the database:
```sql
\q
```

**Troubleshooting:**
| Problem | Fix |
|---------|-----|
| "port 5432 already in use" | You have PostgreSQL installed locally. In `docker-compose.yml`, change `"5432:5432"` to `"5433:5432"` |
| "permission denied" on docker | Run `sudo docker compose up -d` or add your user to the docker group |
| Tables don't exist | The init script only runs on FIRST start. Run `docker compose down -v` then `docker compose up -d` to start completely fresh |

**Done when:**
- `docker compose ps` shows `nl_sql_db` as `Up (healthy)`
- `SELECT * FROM customers;` returns 5 rows
- `INSERT` as `readonly_user` gives "permission denied"

---

## PHASE 2: Python Talks to the Database

> **Why this phase?** The database is running in Docker. Now we need Python code (running on your computer) to connect to it and read data. This proves the two systems can talk to each other.

---

### Task 2.1: Set Up Python Virtual Environment

**What:** Create an isolated Python environment for this project.

**Why:** A "virtual environment" (venv) is a separate copy of Python just for this project. It keeps your project's libraries separate from your system Python. If you install something that breaks things, you just delete the venv and recreate it — your computer is fine.

**Steps:**
```bash
# Make sure you're inside nl-sql-tool/
cd nl-sql-tool

# Create the virtual environment
python -m venv .venv

# Activate it:
# Windows (Command Prompt):
.venv\Scripts\activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (Git Bash):
source .venv/Scripts/activate
# Mac/Linux:
source .venv/bin/activate
```

**How to know it's activated:** Your terminal prompt will show `(.venv)` at the beginning, like:
```
(.venv) C:\Users\you\nl-sql-tool>
```

**Important:** You need to activate the venv EVERY TIME you open a new terminal window. If you see errors about missing packages, check if `.venv` is activated first.

**Done when:** Your terminal shows `(.venv)` at the beginning of the prompt.

---

### Task 2.2: Install Python Libraries

**What:** Install the libraries (packages) that Python needs to talk to PostgreSQL.

**Why:**
- `asyncpg` — The fastest Python library for connecting to PostgreSQL. "Async" means it doesn't freeze your program while waiting for the database.
- `python-dotenv` — Reads settings from a `.env` file so you don't hardcode passwords in your code.

**Steps:**
```bash
pip install asyncpg python-dotenv
```

**Verify they installed:**
```bash
pip list | grep -i asyncpg
pip list | grep -i dotenv
```

**Done when:** Both `asyncpg` and `python-dotenv` appear in `pip list`.

---

### Task 2.3: Create the .env File

**What:** Create a file that stores your database connection details.

**Why:** You NEVER hardcode passwords directly in Python files. What if you accidentally share your code? Instead, passwords go in a `.env` file which you add to `.gitignore` so it's never shared. Your Python code reads from this file.

**Steps:**

1. Create `.env` in your project root:
```
DATABASE_URL=postgresql://admin:secret123@localhost:5432/shopdb
DATABASE_URL_READONLY=postgresql://readonly_user:readonly123@localhost:5432/shopdb
```

2. Create `.gitignore` to protect your secrets:
```
.env
.venv/
__pycache__/
*.pyc
```

**What the connection URL means:**
```
postgresql://admin:secret123@localhost:5432/shopdb
             ^^^^^  ^^^^^^^^^  ^^^^^^^^^  ^^^^  ^^^^^^
             user   password   host       port  database
```

- `admin:secret123` — username and password (from docker-compose.yml)
- `localhost:5432` — the database is on your computer, port 5432
- `shopdb` — the database name

**Why two URLs?**
- `DATABASE_URL` uses the admin user (full access — for setup only)
- `DATABASE_URL_READONLY` uses the read-only user (for the app — even if something goes wrong, it can't modify data)

**Done when:** `.env` and `.gitignore` files exist in your project root.

---

### Task 2.4: Write and Run the Database Connection Test

**What:** Write a Python script that connects to the database in Docker and reads data.

**Why:** This is the proof that Python on your computer can talk to PostgreSQL inside Docker. If this works, the foundation of the entire project is solid.

**Steps:**

1. Create `test_db_connection.py`:

```python
# test_db_connection.py
# Purpose: Prove that Python can talk to the database in Docker

import asyncio
import os
from dotenv import load_dotenv
import asyncpg

# Load the DATABASE_URL from .env file
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL_READONLY")


async def test_connection():
    """Connect to the database and run some test queries."""

    # Step 1: Connect
    print("Connecting to database...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected successfully!\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        print("\nChecklist:")
        print("  1. Is Docker running? (docker compose ps)")
        print("  2. Is the .env file in this directory?")
        print("  3. Is the DATABASE_URL correct?")
        return

    # Step 2: Test a simple query
    print("All customers:")
    print("-" * 50)
    rows = await conn.fetch("SELECT id, name, email, city FROM customers")
    for row in rows:
        print(f"  {row['id']}. {row['name']} ({row['email']}) - {row['city']}")

    # Step 3: Test a JOIN query
    print(f"\nAll orders:")
    print("-" * 50)
    rows = await conn.fetch("""
        SELECT c.name AS customer, p.name AS product,
               o.quantity, o.status, o.order_date
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        ORDER BY o.order_date DESC
    """)
    for row in rows:
        print(f"  {row['customer']} bought {row['quantity']}x {row['product']}"
              f" - {row['status']} ({row['order_date'].strftime('%Y-%m-%d')})")

    # Step 4: Test that read-only actually blocks writes
    print(f"\nTesting read-only protection...")
    try:
        await conn.execute(
            "INSERT INTO customers (name, email) VALUES ('Test', 'test@test.com')"
        )
        print("WARNING: Write succeeded - readonly_user has too many permissions!")
    except asyncpg.InsufficientPrivilegeError:
        print("Write blocked - read-only protection works!")
    except Exception as e:
        print(f"Write blocked with: {type(e).__name__}")

    await conn.close()
    print("\nAll tests passed! Database connection is working.")


# Run it
asyncio.run(test_connection())
```

2. Make sure Docker is running (the database from Task 1.3)
3. Run the script:
```bash
python test_db_connection.py
```

**Expected output:**
```
Connecting to database...
Connected successfully!

All customers:
--------------------------------------------------
  1. Alice Smith (alice@email.com) - London
  2. Bob Jones (bob@email.com) - Sydney
  ...

All orders:
--------------------------------------------------
  Alice Smith bought 1x Running Shoes - shipped (2025-02-27)
  ...

Testing read-only protection...
Write blocked - read-only protection works!

All tests passed! Database connection is working.
```

**Troubleshooting:**
| Problem | Fix |
|---------|-----|
| "connection refused" | Is Docker running? Run `docker compose ps` |
| "password authentication failed" | Check your .env file — does the password match docker-compose.yml? |
| "database shopdb does not exist" | The init script didn't run. Run `docker compose down -v` then `docker compose up -d` |
| "ModuleNotFoundError: asyncpg" | Did you activate the venv? Check for `(.venv)` in your prompt |

**Done when:** The script prints all customers, all orders, and "Write blocked — read-only protection works!"

---

## PHASE 3: Python App in Docker (Optional but Recommended)

> **Why this phase?** Right now, Python runs on your computer and the database runs in Docker. This works fine, but it's better to have EVERYTHING in Docker. That way anyone can clone your project and run `docker compose up` and everything works — no need to install Python, create venvs, etc. **You can skip this phase** and come back later if you want.

---

### Task 3.1: Create requirements.txt

**What:** List all Python packages your project needs in a file.

**Why:** When Docker builds your Python container, it needs to know what to install. `requirements.txt` is the standard way to list Python dependencies. It's like a shopping list for `pip install`.

**Steps:**

Create `requirements.txt` in your project root:
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
asyncpg==0.30.0
anthropic==0.43.0
sqlparse==0.5.3
pydantic-settings==2.7.1
python-dotenv==1.0.1
matplotlib==3.9.0
```

**What each package does:**
| Package | Purpose |
|---------|---------|
| `fastapi` | The web framework — handles HTTP requests (like Express for Node.js) |
| `uvicorn` | The web server that runs FastAPI |
| `asyncpg` | Connects Python to PostgreSQL |
| `anthropic` | Connects Python to Claude AI |
| `sqlparse` | Parses SQL queries (used in the safety validator) |
| `pydantic-settings` | Manages app settings/config |
| `python-dotenv` | Reads `.env` files |
| `matplotlib` | Creates charts and graphs |

**Done when:** The file exists at `nl-sql-tool/requirements.txt`.

---

### Task 3.2: Create a Dockerfile

**What:** Write instructions that tell Docker how to build a container with your Python app.

**Why:** A `Dockerfile` is like a recipe. It says: "Start with Python 3.12, copy my code, install my dependencies, and run my app." Docker follows these steps to build an "image" — a snapshot of your app that can be run anywhere.

**Steps:**

Create `Dockerfile` in your project root:
```dockerfile
# Dockerfile
# Start with a base image that has Python installed
FROM python:3.12-slim

# Set /app as the working directory inside the container
WORKDIR /app

# Copy ONLY requirements first (Docker caches this layer)
COPY requirements.txt .

# Install all Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Tell Docker this container listens on port 8000
EXPOSE 8000

# The command that runs when the container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**What each line does:**
| Line | Meaning |
|------|---------|
| `FROM python:3.12-slim` | Start from the official Python image |
| `WORKDIR /app` | All commands after this run inside `/app` |
| `COPY requirements.txt .` | Copy requirements file into the container |
| `RUN pip install ...` | Install Python packages inside the container |
| `COPY . .` | Copy ALL your project files into the container |
| `CMD [...]` | The default command when the container starts |

**Done when:** The file exists at `nl-sql-tool/Dockerfile`.

---

### Task 3.3: Add Python App to docker-compose.yml

**What:** Add a second service (the Python app) to docker-compose.yml so both the database and app run together.

**Why:** Right now docker-compose only runs the database. We need to add the Python app as a second container. Docker Compose will make sure the database starts first (and is healthy) before starting the app.

**Steps:**

Add this BELOW the `db` service in your `docker-compose.yml` (but ABOVE the `volumes:` section):

```yaml
  # --- THE PYTHON APP ---
  app:
    build: .
    container_name: nl_sql_app
    restart: unless-stopped

    environment:
      DATABASE_URL: postgresql://readonly_user:readonly123@db:5432/shopdb
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}

    ports:
      - "8000:8000"

    depends_on:
      db:
        condition: service_healthy

    volumes:
      - ./app:/app/app
```

**IMPORTANT:** Notice the database URL uses `@db:5432` NOT `@localhost:5432`. Inside Docker, containers talk to each other by their SERVICE NAME (the name under `services:` in docker-compose.yml). The database service is called `db`, so the app connects to `db:5432`.

**Done when:** Your docker-compose.yml has both `db` and `app` services. Don't start it yet — we'll build the app code first.

---

### Task 3.4: Test Docker Build (Quick Sanity Check)

**What:** Verify that Docker can build your Python image without errors.

**Why:** Before writing more code, make sure the Dockerfile and requirements work. It's easier to fix problems now than after writing hundreds of lines of code.

**Steps:**
```bash
docker compose build app
```

This will download the Python image, install all packages, and copy your code. First time takes 2-5 minutes.

**If it fails:** Read the error message carefully. Common issues:
- Typo in `requirements.txt` — check package names
- Docker not running — open Docker Desktop

**Done when:** The build finishes without errors. You'll see `Successfully built ...` or `Successfully tagged ...`.

---

## PHASE 4: Talk to AI (Claude) from Python

> **Why this phase?** This is where the "AI" part starts. You'll learn how to send a message to Claude from Python and get a response. Then you'll teach Claude about your database so it can write SQL for you. No magic — just HTTP requests to Anthropic's servers.

---

### Task 4.1: Get an Anthropic API Key

**What:** Create an account on Anthropic and get an API key.

**Why:** An API key is like a password that lets your Python code talk to Claude. Every time your code sends a request, it includes this key so Anthropic knows who's asking. You get free credits to start with.

**Steps:**
1. Go to https://console.anthropic.com/
2. Sign up for an account
3. Go to "API Keys" in the sidebar
4. Click "Create Key"
5. Copy the key (it starts with `sk-ant-...`)
6. Add it to your `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
DATABASE_URL=postgresql://admin:secret123@localhost:5432/shopdb
DATABASE_URL_READONLY=postgresql://readonly_user:readonly123@localhost:5432/shopdb
```

**NEVER share your API key.** Don't put it in code files. Don't commit it to git. It stays in `.env` which is in `.gitignore`.

**Done when:** Your `.env` file has a line starting with `ANTHROPIC_API_KEY=sk-ant-...`

---

### Task 4.2: Install the Anthropic Library

**What:** Install the Python package that talks to Claude.

**Why:** The `anthropic` package handles all the HTTP communication with Anthropic's servers. You just call a function and get Claude's response back.

**Steps:**
```bash
pip install anthropic
```

**Done when:** `pip list | grep -i anthropic` shows the package.

---

### Task 4.3: Send Your First Message to Claude

**What:** Write a Python script that sends one message to Claude and prints the response.

**Why:** This is your "hello world" for AI. Once this works, you know your API key is valid and you can communicate with Claude. Everything else builds on this.

**Steps:**

1. Create `test_ai_basic.py`:

```python
# test_ai_basic.py
# Purpose: Send a message to Claude and get a response. No magic.

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# Create the client - this is what talks to Anthropic's servers
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Send a message
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",   # Which AI model to use
    max_tokens=200,                        # Maximum length of response
    temperature=0,                         # 0 = same input always gives same output

    system="You are a helpful assistant. Reply in one sentence.",

    messages=[
        {"role": "user", "content": "What is PostgreSQL?"}
    ]
)

# The response is a Python object. The actual text is here:
print("Claude says:")
print(response.content[0].text)

# Also see how many tokens (words) were used:
print(f"\nModel used: {response.model}")
print(f"Tokens used: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
```

2. Run it:
```bash
python test_ai_basic.py
```

**What each part means:**
| Part | Meaning |
|------|---------|
| `Anthropic(api_key=...)` | Create a connection to Anthropic's servers |
| `model="claude-sonnet-4-5-20250929"` | Which Claude model to use (Sonnet is fast and smart) |
| `max_tokens=200` | Don't let the response be longer than ~200 words |
| `temperature=0` | Be deterministic — same question = same answer every time |
| `system="..."` | The "job description" for Claude — it sees this before every message |
| `messages=[...]` | The actual conversation — in this case, one user message |

**Done when:** Claude responds with a sentence about PostgreSQL. You just talked to AI from Python!

---

### Task 4.4: Make Claude Write SQL for Your Database

**What:** Give Claude your database schema and ask it to write SQL queries based on English questions.

**Why:** This is the CORE of the project. Instead of you writing SQL, you describe what you want in English, and Claude writes the SQL for you. The "system prompt" tells Claude about your tables so it writes correct SQL.

**Steps:**

1. Create `test_ai_sql.py`:

```python
# test_ai_sql.py
# Purpose: Give Claude our database schema and ask it to write SQL

import os
import re
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# This is the SYSTEM PROMPT - it tells Claude its job and what our database looks like
SYSTEM_PROMPT = """You are a SQL expert for a PostgreSQL database.

Here is the database schema:

<schema>
Table: customers
  - id: SERIAL (PK)
  - name: VARCHAR(100)
  - email: VARCHAR(100)
  - city: VARCHAR(50)
  - joined_date: DATE

Table: products
  - id: SERIAL (PK)
  - name: VARCHAR(100)
  - category: VARCHAR(50) - values: 'Electronics', 'Kitchen', 'Sports', 'Stationery'
  - price: NUMERIC(10,2)

Table: orders
  - id: SERIAL (PK)
  - customer_id: INTEGER (FK -> customers.id)
  - product_id: INTEGER (FK -> products.id)
  - quantity: INTEGER
  - status: VARCHAR(20) - values: 'pending', 'shipped', 'delivered', 'cancelled'
  - order_date: TIMESTAMP
</schema>

Rules:
- ONLY write SELECT queries. Never write INSERT, UPDATE, DELETE, or DROP.
- Wrap your SQL in <sql> tags.
- Before the SQL, explain your thinking in <thought_process> tags.
"""

# Ask a question
question = "Which customers have spent the most money?"

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=500,
    temperature=0,
    system=SYSTEM_PROMPT,
    messages=[
        {"role": "user", "content": question}
    ]
)

reply = response.content[0].text
print("Question:", question)
print("\nClaude's full response:")
print(reply)

# Extract just the SQL using regex
sql_match = re.search(r"<sql>(.*?)</sql>", reply, re.DOTALL)
if sql_match:
    sql = sql_match.group(1).strip()
    print("\n--- Extracted SQL ---")
    print(sql)
```

2. Run it:
```bash
python test_ai_sql.py
```

**What just happened:**
1. We told Claude about our database (system prompt with schema)
2. We asked "Which customers have spent the most money?" in English
3. Claude wrote a working SQL query with JOINs, GROUP BY, and ORDER BY
4. We extracted the SQL from the `<sql>` tags using regex

**Done when:** Claude returns a SQL query wrapped in `<sql>` tags and you can extract it.

---

### Task 4.5: The Full Loop — Question to AI to Database to Results

**What:** Combine everything: ask a question in English, Claude writes SQL, Python runs it against the real database, and you see actual data.

**Why:** This is THE moment. This is the entire project working end-to-end. Everything after this is just making it prettier, safer, and accessible through a web browser.

**Steps:**

1. Create `test_ai_plus_db.py`:

```python
# test_ai_plus_db.py
# Purpose: question -> AI writes SQL -> Python runs it -> see real results

import asyncio
import os
import re
from dotenv import load_dotenv
from anthropic import Anthropic
import asyncpg

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
DATABASE_URL = os.getenv("DATABASE_URL_READONLY")

SYSTEM_PROMPT = """You are a SQL expert for a PostgreSQL database.

<schema>
Table: customers (id SERIAL PK, name VARCHAR, email VARCHAR, city VARCHAR, joined_date DATE)
Table: products (id SERIAL PK, name VARCHAR, category VARCHAR, price NUMERIC)
  category values: 'Electronics', 'Kitchen', 'Sports', 'Stationery'
Table: orders (id SERIAL PK, customer_id INT FK->customers, product_id INT FK->products, quantity INT, status VARCHAR, order_date TIMESTAMP)
  status values: 'pending', 'shipped', 'delivered', 'cancelled'
</schema>

Rules:
- ONLY write SELECT queries.
- Wrap SQL in <sql> tags.
- Explain your reasoning in <thought_process> tags.
"""


def ask_claude(question: str) -> dict:
    """Send a question to Claude, get back SQL and explanation."""
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}]
    )
    reply = response.content[0].text

    sql_match = re.search(r"<sql>(.*?)</sql>", reply, re.DOTALL)
    thought_match = re.search(r"<thought_process>(.*?)</thought_process>", reply, re.DOTALL)

    return {
        "sql": sql_match.group(1).strip() if sql_match else None,
        "explanation": thought_match.group(1).strip() if thought_match else None,
        "raw_response": reply
    }


async def run_query(sql: str) -> list[dict]:
    """Run a SQL query and return results as a list of dicts."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(sql)
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def ask_question(question: str):
    """The full pipeline: question -> AI -> SQL -> database -> results."""
    print(f"Question: {question}")
    print("=" * 60)

    # Step 1: Ask Claude to write SQL
    print("\nAsking Claude...")
    result = ask_claude(question)

    if not result["sql"]:
        print("Claude didn't generate SQL. Raw response:")
        print(result["raw_response"])
        return

    print(f"\nExplanation: {result['explanation']}")
    print(f"\nSQL:\n{result['sql']}")

    # Step 2: Run the SQL against the real database
    print("\nRunning query...")
    try:
        rows = await run_query(result["sql"])
    except Exception as e:
        print(f"Query failed: {e}")
        return

    # Step 3: Display results
    print(f"\nGot {len(rows)} results:\n")
    if rows:
        headers = list(rows[0].keys())
        print("  |  ".join(f"{h:>15}" for h in headers))
        print("  " + "-" * (18 * len(headers)))
        for row in rows:
            values = [str(v) for v in row.values()]
            print("  |  ".join(f"{v:>15}" for v in values))


async def main():
    questions = [
        "Show me all customers",
        "Which customers have spent the most money?",
        "How many orders are in each status?",
        "What are the most popular products?",
    ]
    for q in questions:
        await ask_question(q)
        print("\n" + "=" * 60 + "\n")


asyncio.run(main())
```

2. Make sure Docker database is running: `docker compose ps`
3. Run it:
```bash
python test_ai_plus_db.py
```

**Done when:** You see real data from your database for each question. English question in, database results out. The core project works!

---

## PHASE 5: Safety Layer (Query Validator)

> **Why this phase?** Claude follows instructions, but clever users can try "prompt injection" — tricking the AI into writing dangerous SQL like `DROP TABLE customers`. The validator catches dangerous SQL before it reaches the database. This is called "defense in depth" — multiple layers of protection.

---

### Task 5.1: Create the App Folder Structure

**What:** Set up the proper folder structure for the application.

**Why:** We've been writing test scripts in the root folder. Now we start building the real app. In Python, you organize code into packages (folders with `__init__.py` files). This keeps things clean and importable.

**Steps:**
```bash
mkdir app
```

Create an empty `app/__init__.py` file (this tells Python the folder is a package):
```python
# app/__init__.py
# This file can be empty — it just tells Python that "app" is a package
```

**Done when:** The `app/` folder exists with an empty `__init__.py` inside.

---

### Task 5.2: Create the Query Validator

**What:** Write a Python module that checks if a SQL query is safe to run.

**Why:** Even though Claude is told to only write SELECT queries, someone could trick it. The validator is a safety net — it checks every query BEFORE it reaches the database. If the query contains `DROP`, `DELETE`, `INSERT`, etc., it blocks it.

**Steps:**

1. Install sqlparse:
```bash
pip install sqlparse
```

2. Create `app/query_validator.py`:

```python
# app/query_validator.py
# Purpose: Check that AI-generated SQL is safe before running it

import sqlparse

# Words that should NEVER appear in a query from this tool
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "EXECUTE", "COPY",
    "pg_sleep", "pg_catalog", "pg_read_file", "pg_write_file",
    "lo_import", "lo_export",
]


def validate_query(sql: str) -> dict:
    """
    Check if a SQL query is safe to run.

    Returns:
        {"valid": True} if safe
        {"valid": False, "error": "reason"} if dangerous
    """

    # Check 1: Is it empty?
    if not sql or not sql.strip():
        return {"valid": False, "error": "Empty query"}

    # Check 2: Parse with sqlparse
    statements = sqlparse.parse(sql)

    # Check 3: Only ONE statement allowed
    # This blocks tricks like: "SELECT 1; DROP TABLE users;"
    if len(statements) != 1:
        return {
            "valid": False,
            "error": f"Expected 1 statement, got {len(statements)}. "
                     f"Multi-statement queries are not allowed."
        }

    # Check 4: Must be a SELECT statement
    stmt = statements[0]
    if stmt.get_type() != "SELECT":
        return {
            "valid": False,
            "error": f"Only SELECT queries allowed. Got: {stmt.get_type()}"
        }

    # Check 5: No forbidden keywords anywhere in the query
    sql_upper = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword.upper() in sql_upper:
            return {
                "valid": False,
                "error": f"Forbidden keyword detected: {keyword}"
            }

    # Check 6: No semicolons in the middle (extra safety)
    if ";" in sql.strip().rstrip(";"):
        return {
            "valid": False,
            "error": "Suspicious semicolon detected in query body"
        }

    return {"valid": True}
```

**Done when:** The file exists at `app/query_validator.py`.

---

### Task 5.3: Test the Validator

**What:** Write a test script that throws safe and dangerous queries at the validator to make sure it works.

**Why:** You should NEVER trust a security component without testing it. We test both "good" queries (should pass) and "bad" queries (should be blocked).

**Steps:**

1. Create `test_validator.py`:

```python
# test_validator.py
from app.query_validator import validate_query

# These should all PASS (safe queries)
safe_queries = [
    "SELECT * FROM customers",
    "SELECT name, SUM(price) FROM products GROUP BY name",
    "SELECT c.name FROM customers c JOIN orders o ON c.id = o.customer_id",
]

# These should all FAIL (dangerous queries)
dangerous_queries = [
    "DROP TABLE customers",
    "DELETE FROM customers WHERE id = 1",
    "INSERT INTO customers (name) VALUES ('hacker')",
    "SELECT 1; DROP TABLE customers;",
    "UPDATE customers SET name = 'hacked'",
    "SELECT pg_sleep(100)",
]

print("SAFE QUERIES (should all pass):")
for q in safe_queries:
    result = validate_query(q)
    status = "PASS" if result["valid"] else f"BLOCKED: {result['error']}"
    print(f"  {status} -- {q[:50]}")

print("\nDANGEROUS QUERIES (should all be blocked):")
for q in dangerous_queries:
    result = validate_query(q)
    status = f"BLOCKED: {result['error']}" if not result["valid"] else "MISSED!"
    print(f"  {status} -- {q[:50]}")
```

2. Run it:
```bash
python test_validator.py
```

**Done when:** Every safe query passes and every dangerous query is blocked.

---

## PHASE 6: The Web Interface (FastAPI)

> **Why this phase?** Everything works in the terminal, but real users want a web page. We'll build a browser-based interface using FastAPI (Python web framework) where users type questions and see results in a nice table.

---

### Task 6.1: Install Web Framework Dependencies

**What:** Install FastAPI and Uvicorn (the web server).

**Why:**
- `FastAPI` — A modern Python web framework. It handles HTTP requests (GET, POST) and returns responses. Think of it like Flask but faster and with automatic documentation.
- `Uvicorn` — The server that actually runs your FastAPI app and listens for web requests.
- `pydantic-settings` — Manages app configuration in a type-safe way.

**Steps:**
```bash
pip install fastapi uvicorn pydantic-settings
```

**Done when:** `pip list` shows `fastapi`, `uvicorn`, and `pydantic-settings`.

---

### Task 6.2: Create App Configuration (app/config.py)

**What:** Create a centralized configuration module that reads all settings from the .env file.

**Why:** Instead of scattering `os.getenv(...)` calls throughout your code, you put them all in one place. If you need to change a setting, you change it in ONE file. This is a very common pattern in professional projects.

**Steps:**

Create `app/config.py`:

```python
# app/config.py
# Purpose: All app settings in one place

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://readonly_user:readonly123@localhost:5432/shopdb"
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"


# Create a single instance used across the app
settings = Settings()
```

**Done when:** The file exists and you understand that `settings.database_url` and `settings.anthropic_api_key` pull from `.env`.

---

### Task 6.3: Create Database Module (app/database.py)

**What:** Create a module that handles all database connections and queries.

**Why:** Instead of creating database connections everywhere, we centralize it. This module provides two functions: `get_schema()` (gets table info to send to Claude) and `execute_query()` (runs SQL and returns results).

**Steps:**

Create `app/database.py`:

```python
# app/database.py
# Purpose: All database operations

import asyncpg
from app.config import settings


async def get_pool():
    """Create a connection pool (reuses connections instead of creating new ones)."""
    return await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)


async def get_schema(pool) -> str:
    """Get the database schema to include in the AI prompt."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ('customers', 'products', 'orders')
            ORDER BY table_name, ordinal_position
        """)

    schema_text = ""
    current_table = ""
    for row in rows:
        if row["table_name"] != current_table:
            current_table = row["table_name"]
            schema_text += f"\nTable: {current_table}\n"
        nullable = "NULL" if row["is_nullable"] == "YES" else "NOT NULL"
        schema_text += f"  - {row['column_name']}: {row['data_type']} ({nullable})\n"

    return schema_text


async def execute_query(pool, sql: str) -> list[dict]:
    """Execute a read-only SQL query and return results."""
    async with pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(sql)
    return [dict(row) for row in rows]
```

**Done when:** The file exists at `app/database.py`.

---

### Task 6.4: Create LLM Module (app/llm.py)

**What:** Create a module that handles all communication with Claude AI.

**Why:** This wraps the Anthropic API calls into clean functions. The main app just calls `generate_sql(question)` and gets back SQL + an explanation. All the prompt engineering lives here.

**Steps:**

Create `app/llm.py`:

```python
# app/llm.py
# Purpose: All AI/Claude communication

import re
from anthropic import Anthropic
from app.config import settings

client = Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT_TEMPLATE = """You are a SQL expert for a PostgreSQL database.

Here is the database schema:
<schema>
{schema}
</schema>

Additional info:
- products.category values: 'Electronics', 'Kitchen', 'Sports', 'Stationery'
- orders.status values: 'pending', 'shipped', 'delivered', 'cancelled'

Rules:
- ONLY write SELECT queries. Never INSERT, UPDATE, DELETE, DROP.
- Wrap your SQL in <sql> tags.
- Explain your reasoning in <thought_process> tags.
"""


def generate_sql(question: str, schema: str) -> dict:
    """Ask Claude to write a SQL query for the given question."""

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema)

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": question}]
    )

    reply = response.content[0].text

    sql_match = re.search(r"<sql>(.*?)</sql>", reply, re.DOTALL)
    thought_match = re.search(r"<thought_process>(.*?)</thought_process>", reply, re.DOTALL)

    return {
        "sql": sql_match.group(1).strip() if sql_match else None,
        "explanation": thought_match.group(1).strip() if thought_match else None,
        "raw_response": reply,
    }
```

**Done when:** The file exists at `app/llm.py`.

---

### Task 6.5: Create API Routes (app/routes.py)

**What:** Create the HTTP endpoints that the web browser will call.

**Why:** When a user types a question in the browser and clicks "Ask", the browser sends an HTTP POST request to `/api/query`. This module handles that request: it gets the schema, asks Claude for SQL, validates it, runs it, and returns results as JSON.

**Steps:**

Create `app/routes.py`:

```python
# app/routes.py
# Purpose: HTTP endpoints

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import get_schema, execute_query
from app.llm import generate_sql
from app.query_validator import validate_query

router = APIRouter()

# Global pool reference (set by main.py on startup)
pool = None


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    explanation: str | None
    columns: list[str]
    rows: list[dict]


@router.post("/api/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """The main endpoint: question -> SQL -> results."""

    # Step 1: Get database schema
    schema = await get_schema(pool)

    # Step 2: Ask Claude to write SQL
    result = generate_sql(request.question, schema)

    if not result["sql"]:
        raise HTTPException(status_code=400, detail="AI could not generate SQL for this question.")

    # Step 3: Validate the SQL (safety check!)
    validation = validate_query(result["sql"])
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=f"Unsafe query blocked: {validation['error']}")

    # Step 4: Run the SQL
    try:
        rows = await execute_query(pool, result["sql"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")

    # Step 5: Return results
    columns = list(rows[0].keys()) if rows else []
    return QueryResponse(
        question=request.question,
        sql=result["sql"],
        explanation=result["explanation"],
        columns=columns,
        rows=rows,
    )


@router.get("/api/health")
async def health_check():
    """Simple health check."""
    return {"status": "ok"}
```

**Done when:** The file exists at `app/routes.py`.

---

### Task 6.6: Create the Main App Entry Point (app/main.py)

**What:** Create the main FastAPI application that ties everything together.

**Why:** This is the "front door" of your app. It creates the FastAPI instance, connects to the database on startup, disconnects on shutdown, includes the routes, and serves the static HTML files.

**Steps:**

Create `app/main.py`:

```python
# app/main.py
# Purpose: The main app - ties everything together

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import get_pool
from app import routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # STARTUP: Connect to database
    routes.pool = await get_pool()
    print("Database pool created")
    yield
    # SHUTDOWN: Close database connections
    await routes.pool.close()
    print("Database pool closed")


app = FastAPI(title="NL-SQL Tool", lifespan=lifespan)

# Include API routes
app.include_router(routes.router)

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def root():
    """Serve the main page."""
    return FileResponse("app/static/index.html")
```

**Done when:** The file exists at `app/main.py`.

---

### Task 6.7: Create the Frontend (HTML/CSS/JS)

**What:** Create the web page that users interact with in their browser.

**Why:** This is the "face" of the app. Users type questions here, and results appear as a nicely formatted table. It communicates with the Python backend via the `/api/query` endpoint.

**Steps:**

1. Create the static folder:
```bash
mkdir app/static
```

2. Create `app/static/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NL-SQL Tool</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>Natural Language SQL Tool</h1>
        <p class="subtitle">Ask questions about your data in plain English</p>

        <div class="input-area">
            <input
                type="text"
                id="question"
                placeholder="e.g. Which customers have spent the most money?"
                autofocus
            />
            <button id="ask-btn" onclick="askQuestion()">Ask</button>
        </div>

        <div id="loading" class="hidden">Thinking...</div>
        <div id="error" class="hidden"></div>

        <div id="result" class="hidden">
            <div class="section">
                <h3>Explanation</h3>
                <p id="explanation"></p>
            </div>

            <div class="section">
                <h3>SQL Query</h3>
                <pre id="sql-query"></pre>
            </div>

            <div class="section">
                <h3>Results</h3>
                <div id="table-container"></div>
            </div>
        </div>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
```

3. Create `app/static/style.css`:

```css
/* app/static/style.css */

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5;
    color: #333;
    padding: 2rem;
}

.container {
    max-width: 900px;
    margin: 0 auto;
}

h1 { margin-bottom: 0.25rem; }
.subtitle { color: #666; margin-bottom: 2rem; }

.input-area {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
}

input[type="text"] {
    flex: 1;
    padding: 0.75rem 1rem;
    font-size: 1rem;
    border: 2px solid #ddd;
    border-radius: 8px;
    outline: none;
}

input[type="text"]:focus { border-color: #4a90d9; }

button {
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    background: #4a90d9;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
}

button:hover { background: #357abd; }
button:disabled { background: #ccc; cursor: not-allowed; }

.section {
    background: white;
    padding: 1.25rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.section h3 { margin-bottom: 0.75rem; color: #555; }

pre {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 1rem;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 0.9rem;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th, td {
    padding: 0.6rem 0.75rem;
    text-align: left;
    border-bottom: 1px solid #eee;
}

th { background: #f8f8f8; font-weight: 600; }
tr:hover { background: #f0f7ff; }

.hidden { display: none; }

#loading {
    text-align: center;
    padding: 2rem;
    font-size: 1.1rem;
    color: #666;
}

#error {
    background: #fff0f0;
    color: #d32f2f;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
}
```

4. Create `app/static/app.js`:

```javascript
// app/static/app.js

// Allow pressing Enter to submit
document.getElementById("question").addEventListener("keydown", function (e) {
    if (e.key === "Enter") askQuestion();
});

async function askQuestion() {
    const input = document.getElementById("question");
    const question = input.value.trim();
    if (!question) return;

    // Show loading, hide previous results
    document.getElementById("loading").classList.remove("hidden");
    document.getElementById("result").classList.add("hidden");
    document.getElementById("error").classList.add("hidden");
    document.getElementById("ask-btn").disabled = true;

    try {
        const response = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Something went wrong");
        }

        const data = await response.json();
        displayResult(data);

    } catch (err) {
        document.getElementById("error").textContent = err.message;
        document.getElementById("error").classList.remove("hidden");
    } finally {
        document.getElementById("loading").classList.add("hidden");
        document.getElementById("ask-btn").disabled = false;
    }
}

function displayResult(data) {
    // Show explanation
    document.getElementById("explanation").textContent = data.explanation || "No explanation provided.";

    // Show SQL
    document.getElementById("sql-query").textContent = data.sql;

    // Build results table
    const container = document.getElementById("table-container");
    if (data.rows.length === 0) {
        container.innerHTML = "<p>No results found.</p>";
    } else {
        let html = "<table><thead><tr>";
        for (const col of data.columns) {
            html += `<th>${col}</th>`;
        }
        html += "</tr></thead><tbody>";
        for (const row of data.rows) {
            html += "<tr>";
            for (const col of data.columns) {
                html += `<td>${row[col] ?? ""}</td>`;
            }
            html += "</tr>";
        }
        html += "</tbody></table>";
        container.innerHTML = html;
    }

    document.getElementById("result").classList.remove("hidden");
}
```

**Done when:** All three files exist: `app/static/index.html`, `app/static/style.css`, `app/static/app.js`.

---

### Task 6.8: Run the Web App and Test It

**What:** Start the FastAPI server and use the app in your browser.

**Why:** This is the moment you see everything working together as a real web application!

**Steps:**

1. Make sure Docker database is running:
```bash
docker compose ps
```

2. Start the web server:
```bash
uvicorn app.main:app --reload
```
(`--reload` means the server restarts automatically when you change code)

3. Open your browser and go to: http://localhost:8000

4. Try these questions:
   - "Show me all customers"
   - "Which customers have spent the most money?"
   - "How many orders are in each status?"
   - "What products have been ordered the most?"
   - "Show me all orders from London customers"

5. Also check the health endpoint: http://localhost:8000/api/health

6. Stop the server with `Ctrl+C` when done testing.

**Troubleshooting:**
| Problem | Fix |
|---------|-----|
| "ModuleNotFoundError" | Make sure your venv is activated (see `(.venv)` in prompt) |
| "Connection refused" on database | Make sure Docker is running: `docker compose up -d` |
| "Invalid API key" | Check your `.env` file has the correct `ANTHROPIC_API_KEY` |
| Page loads but "Ask" does nothing | Open browser DevTools (F12) → Console tab → look for errors |

**Done when:** You can type a question in the browser, click "Ask", and see a table of results. The full web app is working!

---

## PHASE 7: AI-Generated Visualizations (Charts)

> **Why this phase?** Numbers in a table are useful, but charts make data easier to understand at a glance. In this phase, Claude writes a SECOND piece of code — a matplotlib script — that creates a chart from the query results. Your server runs that script and saves the chart image.

---

### Task 7.1: Install Matplotlib

**What:** Install the Python charting library.

**Why:** Matplotlib is Python's most popular library for creating charts (bar charts, line charts, pie charts, etc.). Claude will write matplotlib code, and your server will run it.

**Steps:**
```bash
pip install matplotlib
```

**Done when:** `pip list | grep -i matplotlib` shows the package.

---

### Task 7.2: Add Visualization Logic to LLM Module (app/llm.py)

**What:** Add a second function to `app/llm.py` that asks Claude to write a matplotlib chart script.

**Why:** After getting query results, we make a SECOND call to Claude. The first call writes SQL. The second call writes Python charting code. It's two separate AI calls with two separate system prompts.

**Steps:**

Add this to the END of `app/llm.py`:

```python
VIZ_SYSTEM_PROMPT = """You are a Python data visualization expert.
You will receive a question, the SQL that answered it, and the result data.
Write a Python script using matplotlib that creates a clear, readable chart.

Rules:
- Use matplotlib only (it's already installed)
- Save the chart to the path given in the user message
- Include a title, axis labels, and legend if appropriate
- Pick the best chart type (bar, line, pie, etc.) based on the data
- Use plt.tight_layout() before saving
- Wrap your code in <python> tags
- Do NOT use plt.show() — only plt.savefig()
"""


def generate_chart_script(question: str, sql: str, rows: list[dict], save_path: str) -> str | None:
    """Ask Claude to write a matplotlib script to visualize query results."""

    sample = rows[:20]  # Only send first 20 rows to keep the prompt small

    user_message = f"""
Question: {question}
SQL: {sql}
Results ({len(rows)} rows, showing first {len(sample)}):
{sample}

Save the chart to: {save_path}
"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1500,
        temperature=0,
        system=VIZ_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    reply = response.content[0].text
    match = re.search(r"<python>(.*?)</python>", reply, re.DOTALL)
    return match.group(1).strip() if match else None
```

**Done when:** `app/llm.py` has both `generate_sql()` and `generate_chart_script()` functions.

---

### Task 7.3: Create Chart Runner Utility

**What:** Create a utility module that safely runs the matplotlib script in a subprocess.

**Why:** We NEVER run AI-generated code directly in our main process. Instead, we run it in a separate subprocess with a timeout. If the script hangs, crashes, or does something weird, it can't affect the main app.

**Steps:**

Create `app/chart_runner.py`:

```python
# app/chart_runner.py
# Purpose: Safely run AI-generated matplotlib scripts

import os
import subprocess
import tempfile


def run_chart_script(script: str, save_path: str) -> bool:
    """
    Run a matplotlib script in a subprocess.
    Returns True if the chart was created successfully.
    """

    # Write the script to a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        # Run with a 30-second timeout
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print(f"Chart script error: {result.stderr}")
            return False

        return os.path.exists(save_path)

    except subprocess.TimeoutExpired:
        print("Chart script timed out after 30 seconds")
        return False
    finally:
        os.unlink(script_path)  # Clean up temp file
```

**Done when:** The file exists at `app/chart_runner.py`.

---

### Task 7.4: Add Visualization Endpoints to Routes

**What:** Add new API endpoints for creating and retrieving charts.

**Why:** The frontend needs a way to request a chart and then display it. We add: (1) a chart generation step to the existing `/api/query` flow, and (2) endpoints to list/view saved charts.

**Steps:**

Add these imports to the TOP of `app/routes.py`:

```python
import base64
import tempfile
from fastapi.responses import Response
from app.llm import generate_chart_script
from app.chart_runner import run_chart_script
```

Add these new endpoints to the BOTTOM of `app/routes.py`:

```python
@router.post("/api/visualize")
async def handle_visualize(request: QueryRequest):
    """Generate a chart from query results."""

    # Step 1-4: Same as /api/query (get SQL, validate, run)
    schema = await get_schema(pool)
    result = generate_sql(request.question, schema)

    if not result["sql"]:
        raise HTTPException(status_code=400, detail="AI could not generate SQL.")

    validation = validate_query(result["sql"])
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=f"Unsafe query: {validation['error']}")

    try:
        rows = await execute_query(pool, result["sql"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}")

    if not rows:
        raise HTTPException(status_code=400, detail="No data to visualize.")

    # Step 5: Ask Claude to write a chart script
    save_path = tempfile.mktemp(suffix=".png")
    script = generate_chart_script(request.question, result["sql"], rows, save_path)

    if not script:
        raise HTTPException(status_code=400, detail="AI could not generate a chart script.")

    # Step 6: Run the chart script
    success = run_chart_script(script, save_path)
    if not success:
        raise HTTPException(status_code=500, detail="Chart generation failed.")

    # Step 7: Read the image and return as base64
    with open(save_path, "rb") as f:
        image_bytes = f.read()

    import os
    os.unlink(save_path)  # Clean up temp image

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    return {
        "question": request.question,
        "sql": result["sql"],
        "explanation": result["explanation"],
        "chart_image": image_base64,
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows,
    }
```

**Done when:** The new `/api/visualize` endpoint exists in `app/routes.py`.

---

### Task 7.5: Update Frontend to Show Charts

**What:** Add a "Visualize" button to the web page that generates and displays charts.

**Why:** Users should be able to click one button to get a chart instead of a table (or both!).

**Steps:**

1. In `app/static/index.html`, add a Visualize button next to the Ask button:

```html
<!-- Replace the input-area div with this: -->
<div class="input-area">
    <input
        type="text"
        id="question"
        placeholder="e.g. Which customers have spent the most money?"
        autofocus
    />
    <button id="ask-btn" onclick="askQuestion()">Ask</button>
    <button id="viz-btn" onclick="askVisualize()" style="background:#2ecc71;">Visualize</button>
</div>

<!-- Add this inside the result div, after the Results section: -->
<div class="section hidden" id="chart-section">
    <h3>Chart</h3>
    <img id="chart-image" style="max-width:100%;" />
</div>
```

2. Add this function to `app/static/app.js`:

```javascript
async function askVisualize() {
    const input = document.getElementById("question");
    const question = input.value.trim();
    if (!question) return;

    document.getElementById("loading").classList.remove("hidden");
    document.getElementById("result").classList.add("hidden");
    document.getElementById("error").classList.add("hidden");
    document.getElementById("chart-section").classList.add("hidden");
    document.getElementById("viz-btn").disabled = true;

    try {
        const response = await fetch("/api/visualize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Something went wrong");
        }

        const data = await response.json();
        displayResult(data);

        // Show chart
        if (data.chart_image) {
            document.getElementById("chart-image").src =
                "data:image/png;base64," + data.chart_image;
            document.getElementById("chart-section").classList.remove("hidden");
        }

    } catch (err) {
        document.getElementById("error").textContent = err.message;
        document.getElementById("error").classList.remove("hidden");
    } finally {
        document.getElementById("loading").classList.add("hidden");
        document.getElementById("viz-btn").disabled = false;
    }
}
```

**Done when:** The web page has both "Ask" (table) and "Visualize" (chart) buttons, and clicking "Visualize" shows a chart image.

---

### Task 7.6: Final Integration Test

**What:** Test the entire application end-to-end.

**Why:** This is the final check. Everything should work together: Docker database, Python backend, AI SQL generation, query validation, web interface, and chart generation.

**Steps:**

1. Make sure Docker database is running:
```bash
docker compose ps
```

2. Start the web server:
```bash
uvicorn app.main:app --reload
```

3. Open http://localhost:8000

4. Test these scenarios:

| Test | What to do | Expected result |
|------|-----------|-----------------|
| Basic query | Ask "Show me all customers" | Table with 5 customers |
| Complex query | Ask "Which customers spent the most?" | Table sorted by spending |
| Visualization | Click "Visualize" with "Revenue by product" | Bar chart appears |
| Safety | Ask "Delete all customers" | Error message — query blocked |
| Edge case | Ask "asdfghjkl" | Graceful error message |
| Empty input | Click Ask with empty input | Nothing happens (no crash) |

**Done when:** All 6 tests produce the expected results. The application is complete!

---

## Summary: What You Built

| Phase | What | Skills Learned |
|-------|------|----------------|
| 0 | Hello World in Docker | Docker basics, containers, volumes, docker-compose |
| 1 | Database in Docker | PostgreSQL, SQL, init scripts, user permissions |
| 2 | Python connects to DB | asyncpg, async/await, .env files, venvs |
| 3 | Python in Docker | Dockerfile, container networking, requirements.txt |
| 4 | AI writes SQL | Anthropic API, system prompts, prompt engineering, regex |
| 5 | Safety validator | SQL parsing, input validation, security thinking |
| 6 | Web interface | FastAPI, HTML/CSS/JS, REST APIs, fetch() |
| 7 | AI visualizations | Two-stage AI calls, subprocess, matplotlib |

**Congratulations!** You built a full-stack AI application from scratch. Each phase worked on its own, tested before moving to the next. That's how real software gets built.

---

## Project File Structure (Final)

```
nl-sql-tool/
├── docker-compose.yml          # Runs database (and optionally the app)
├── Dockerfile                  # Builds the Python app container
├── requirements.txt            # Python dependencies
├── .env                        # Secrets (API keys, database URLs) - NEVER commit
├── .gitignore                  # Tells git to ignore .env, .venv, etc.
├── init-scripts/
│   └── 01-create-tables.sql    # Auto-runs on first database start
├── app/
│   ├── __init__.py             # Makes "app" a Python package
│   ├── config.py               # App settings (reads from .env)
│   ├── database.py             # Database connection and queries
│   ├── llm.py                  # Claude AI communication
│   ├── query_validator.py      # SQL safety checker
│   ├── chart_runner.py         # Runs matplotlib scripts safely
│   ├── routes.py               # API endpoints (POST /api/query, etc.)
│   ├── main.py                 # App entry point (ties everything together)
│   └── static/
│       ├── index.html          # The web page
│       ├── style.css           # Styling
│       └── app.js              # Frontend JavaScript
├── test_db_connection.py       # Phase 2 test script
├── test_ai_basic.py            # Phase 4 test script
├── test_ai_sql.py              # Phase 4 test script
├── test_ai_plus_db.py          # Phase 4 test script
└── test_validator.py           # Phase 5 test script
```
