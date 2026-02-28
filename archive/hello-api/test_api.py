# test_api.py
# This runs in a SEPARATE container
# It calls the FastAPI server (hello-app) through HTTP and displays results

import time
import requests
from colorama import Fore, Style

# Inside Docker, containers talk by SERVICE NAME, not localhost
# "hello-app" is the service name in docker-compose.yml
# Port 8080 is the INTERNAL port (not 8085 which is the external one)
API_URL = "http://hello-app:8080"


def wait_for_api():
    """Wait until the API server is ready before running tests."""
    print(f"{Fore.YELLOW}Waiting for API server to be ready...{Style.RESET_ALL}")
    for attempt in range(1, 16):  # Try 15 times (15 seconds max)
        try:
            r = requests.get(f"{API_URL}/health", timeout=2)
            if r.status_code == 200:
                print(f"{Fore.GREEN}API server is ready! (attempt {attempt}){Style.RESET_ALL}\n")
                return True
        except Exception:
            pass
        print(f"  Attempt {attempt}/15 — not ready yet, waiting 1 second...")
        time.sleep(1)

    print(f"{Fore.RED}API server never became ready. Giving up.{Style.RESET_ALL}")
    return False


def test_home():
    """Test the home endpoint."""
    print(f"{Fore.CYAN}--- Test 1: Home Endpoint (GET /) ---{Style.RESET_ALL}")
    r = requests.get(f"{API_URL}/")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")


def test_health():
    """Test the health check."""
    print(f"\n{Fore.CYAN}--- Test 2: Health Check (GET /health) ---{Style.RESET_ALL}")
    r = requests.get(f"{API_URL}/health")
    data = r.json()
    print(f"  Status: {data['status']}")
    print(f"  Database: {data['database']}")


def test_customers():
    """Test the customers endpoint."""
    print(f"\n{Fore.CYAN}--- Test 3: All Customers (GET /customers) ---{Style.RESET_ALL}")
    r = requests.get(f"{API_URL}/customers")
    customers = r.json()
    for c in customers:
        print(f"  {c['id']}. {c['name']} ({c['email']}) - {c['city']}")


def test_products():
    """Test the products endpoint."""
    print(f"\n{Fore.CYAN}--- Test 4: All Products (GET /products) ---{Style.RESET_ALL}")
    r = requests.get(f"{API_URL}/products")
    products = r.json()
    for p in products:
        print(f"  {p['name']} [{p['category']}] - ${p['price']}")


def test_orders():
    """Test the orders endpoint."""
    print(f"\n{Fore.CYAN}--- Test 5: All Orders (GET /orders) ---{Style.RESET_ALL}")
    r = requests.get(f"{API_URL}/orders")
    orders = r.json()
    for o in orders:
        print(f"  {o['customer']} bought {o['quantity']}x {o['product']} - {o['status']}")


def test_custom_query():
    """Test the POST /query endpoint with a custom SQL."""
    print(f"\n{Fore.CYAN}--- Test 6: Custom Query (POST /query) ---{Style.RESET_ALL}")

    # Query 1: Customers from Sydney
    print(f"\n  {Fore.YELLOW}Query: Customers from Sydney{Style.RESET_ALL}")
    r = requests.post(f"{API_URL}/query", json={
        "sql": "SELECT name, email FROM customers WHERE city = 'Sydney'"
    })
    data = r.json()
    print(f"  SQL: {data['sql']}")
    print(f"  Rows: {data['row_count']}")
    for row in data['data']:
        print(f"    → {row['name']} ({row['email']})")

    # Query 2: Top spenders
    print(f"\n  {Fore.YELLOW}Query: Top spenders{Style.RESET_ALL}")
    r = requests.post(f"{API_URL}/query", json={
        "sql": """SELECT c.name, SUM(p.price * o.quantity) AS total_spent
                  FROM customers c
                  JOIN orders o ON o.customer_id = c.id
                  JOIN products p ON o.product_id = p.id
                  WHERE o.status != 'cancelled'
                  GROUP BY c.name
                  ORDER BY total_spent DESC"""
    })
    data = r.json()
    print(f"  SQL sent successfully, got {data['row_count']} rows:")
    for row in data['data']:
        print(f"    → {row['name']}: ${row['total_spent']}")


def test_safety():
    """Test that dangerous queries are blocked."""
    print(f"\n{Fore.CYAN}--- Test 7: Safety Check (should be BLOCKED) ---{Style.RESET_ALL}")
    r = requests.post(f"{API_URL}/query", json={
        "sql": "DELETE FROM customers"
    })
    if r.status_code == 400:
        print(f"  {Fore.GREEN}BLOCKED: {r.json()['detail']}{Style.RESET_ALL}")
    else:
        print(f"  {Fore.RED}WARNING: Dangerous query was NOT blocked!{Style.RESET_ALL}")


# ---- Run all tests ----
print(f"\n{Fore.GREEN}{'=' * 50}")
print(f"  API Test Client — running in separate container")
print(f"  Calling: {API_URL}")
print(f"{'=' * 50}{Style.RESET_ALL}\n")

# Wait for API server to be ready first!
if not wait_for_api():
    exit(1)

test_home()
test_health()
test_customers()
test_products()
test_orders()
test_custom_query()
test_safety()

print(f"\n{Fore.GREEN}{'=' * 50}")
print(f"  All tests complete!")
print(f"{'=' * 50}{Style.RESET_ALL}\n")
