# test_mcp.py
# This runs in a SEPARATE container and tests the MCP server
#
# HOW MCP WORKS:
#   1. Client connects to MCP server via SSE (Server-Sent Events)
#   2. Client asks: "what tools do you have?"
#   3. Server replies: ["db_health_check", "db_get_customers", ...]
#   4. Client calls a tool: "run db_get_customers"
#   5. Server runs the query and sends back results
#
# This is exactly what Claude/AI agent does — but we're doing it manually to test

import os
import time
import json
import asyncio
from colorama import Fore, Style
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8000")


def wait_for_server():
    """Wait for MCP server to be ready."""
    import socket
    print(f"{Fore.YELLOW}Waiting for MCP server to be ready...{Style.RESET_ALL}")
    for attempt in range(1, 20):
        try:
            # Just check if the port is open (TCP connection test)
            sock = socket.create_connection(("mcp-server", 8000), timeout=2)
            sock.close()
            # Give it an extra moment to fully start
            time.sleep(2)
            print(f"{Fore.GREEN}MCP server is ready! (attempt {attempt}){Style.RESET_ALL}\n")
            return True
        except Exception:
            pass
        print(f"  Attempt {attempt}/20 — not ready yet, waiting 2 seconds...")
        time.sleep(2)

    print(f"{Fore.RED}MCP server never became ready. Giving up.{Style.RESET_ALL}")
    return False


async def run_tests():
    """Connect to MCP server and call each tool."""

    sse_url = f"{MCP_SERVER_URL}/sse"
    print(f"{Fore.CYAN}Connecting to MCP server at: {sse_url}{Style.RESET_ALL}\n")

    async with sse_client(sse_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:

            # Initialize the connection
            await session.initialize()
            print(f"{Fore.GREEN}Connected to MCP server!{Style.RESET_ALL}\n")

            # ---- Test 1: List available tools ----
            print(f"{Fore.CYAN}--- Test 1: List Available Tools ---{Style.RESET_ALL}")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  Tool: {Fore.YELLOW}{tool.name}{Style.RESET_ALL}")
                print(f"    Description: {tool.description[:80]}...")

            # ---- Test 2: Health check ----
            print(f"\n{Fore.CYAN}--- Test 2: db_health_check ---{Style.RESET_ALL}")
            result = await session.call_tool("db_health_check", {})
            print(f"  Raw result: {result}")
            print(f"  Content items: {len(result.content)}")
            for i, item in enumerate(result.content):
                print(f"  Content[{i}] type={type(item).__name__} text={repr(item.text[:200] if hasattr(item, 'text') else str(item)[:200])}")
            raw_text = result.content[0].text
            if raw_text:
                data = json.loads(raw_text)
                print(f"  Status: {data['status']}")
                print(f"  Database: {data['database']}")
            else:
                print(f"  {Fore.RED}Empty response from tool{Style.RESET_ALL}")

            # ---- Test 3: Get customers ----
            print(f"\n{Fore.CYAN}--- Test 3: db_get_customers ---{Style.RESET_ALL}")
            result = await session.call_tool("db_get_customers", {})
            customers = json.loads(result.content[0].text)
            for c in customers:
                print(f"  {c['id']}. {c['name']} ({c['email']}) - {c['city']}")

            # ---- Test 4: Get products ----
            print(f"\n{Fore.CYAN}--- Test 4: db_get_products ---{Style.RESET_ALL}")
            result = await session.call_tool("db_get_products", {})
            products = json.loads(result.content[0].text)
            for p in products:
                print(f"  {p['name']} [{p['category']}] - ${p['price']}")

            # ---- Test 5: Get orders ----
            print(f"\n{Fore.CYAN}--- Test 5: db_get_orders ---{Style.RESET_ALL}")
            result = await session.call_tool("db_get_orders", {})
            orders = json.loads(result.content[0].text)
            for o in orders:
                print(f"  {o['customer']} bought {o['quantity']}x {o['product']} - {o['status']}")

            # ---- Test 6: Custom query ----
            print(f"\n{Fore.CYAN}--- Test 6: db_run_query (custom SQL) ---{Style.RESET_ALL}")

            print(f"\n  {Fore.YELLOW}Query: Customers from Sydney{Style.RESET_ALL}")
            result = await session.call_tool("db_run_query", {
                "sql": "SELECT name, email FROM customers WHERE city = 'Sydney'"
            })
            data = json.loads(result.content[0].text)
            print(f"  Rows: {data['row_count']}")
            for row in data['data']:
                print(f"    -> {row['name']} ({row['email']})")

            print(f"\n  {Fore.YELLOW}Query: Top spenders{Style.RESET_ALL}")
            result = await session.call_tool("db_run_query", {
                "sql": "SELECT c.name, SUM(p.price * o.quantity) AS total_spent FROM customers c JOIN orders o ON o.customer_id = c.id JOIN products p ON o.product_id = p.id WHERE o.status != 'cancelled' GROUP BY c.name ORDER BY total_spent DESC"
            })
            data = json.loads(result.content[0].text)
            print(f"  Got {data['row_count']} rows:")
            for row in data['data']:
                print(f"    -> {row['name']}: ${row['total_spent']}")

            # ---- Test 7: Safety check ----
            print(f"\n{Fore.CYAN}--- Test 7: Safety Check (should be BLOCKED) ---{Style.RESET_ALL}")
            result = await session.call_tool("db_run_query", {
                "sql": "DELETE FROM customers"
            })
            data = json.loads(result.content[0].text)
            if "error" in data:
                print(f"  {Fore.GREEN}BLOCKED: {data['error']}{Style.RESET_ALL}")
            else:
                print(f"  {Fore.RED}WARNING: Dangerous query was NOT blocked!{Style.RESET_ALL}")


# ---- Run ----
print(f"\n{Fore.GREEN}{'=' * 55}")
print(f"  MCP Test Client — running in separate container")
print(f"  Calling MCP server at: {MCP_SERVER_URL}")
print(f"{'=' * 55}{Style.RESET_ALL}\n")

if not wait_for_server():
    exit(1)

asyncio.run(run_tests())

print(f"\n{Fore.GREEN}{'=' * 55}")
print(f"  All MCP tests complete!")
print(f"{'=' * 55}{Style.RESET_ALL}\n")
