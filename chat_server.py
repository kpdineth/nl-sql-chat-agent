# chat_server.py
# FastAPI Chat Server — the middleman between Browser and Claude API
#
# HOW IT WORKS (the full chain):
#
#   Browser (HTML)  -->  This Server  -->  Claude API  -->  MCP Server  -->  Database
#   You type here        Forwards msg      AI thinks       Runs queries     Your data
#
# IMPORTANT: This server does NOT talk to the MCP server directly.
# It tells Claude: "here's an MCP server you can use" and Claude handles the rest.
# For this to work, Claude API (on Anthropic's servers) must be able to REACH
# your MCP server. Locally, that means using ngrok or a tunnel.

import os
import json
import time
import requests as http_requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import anthropic

load_dotenv()

# ---- Configuration ----
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8000")
NGROK_API_URL = os.getenv("NGROK_API_URL", "http://ngrok:4040")
MODEL = "claude-sonnet-4-20250514"

# ---- Reports directory (shared volume with MCP server) ----
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ---- Auto-discover ngrok public URL ----
# ngrok creates a public URL that Claude API can reach.
# We ask ngrok's API for the tunnel URL automatically.
ngrok_public_url = None


def discover_ngrok_url():
    """Ask ngrok container for the public tunnel URL."""
    global ngrok_public_url
    print("Discovering ngrok tunnel URL...")

    for attempt in range(15):
        try:
            resp = http_requests.get(f"{NGROK_API_URL}/api/tunnels", timeout=3)
            data = resp.json()
            tunnels = data.get("tunnels", [])
            for tunnel in tunnels:
                if tunnel.get("proto") == "https":
                    ngrok_public_url = tunnel["public_url"]
                    print(f"ngrok tunnel found: {ngrok_public_url}")
                    return ngrok_public_url
            # If no https tunnel, try any tunnel
            if tunnels:
                ngrok_public_url = tunnels[0]["public_url"]
                print(f"ngrok tunnel found: {ngrok_public_url}")
                return ngrok_public_url
        except Exception as e:
            print(f"  Waiting for ngrok... (attempt {attempt + 1}/15) - {e}")
        time.sleep(2)

    print("WARNING: Could not discover ngrok URL. MCP tools may not work.")
    return None


def get_mcp_url():
    """Get the MCP server URL that Claude API can reach."""
    # If ngrok URL is available, use it (Claude API can reach it from internet)
    if ngrok_public_url:
        return ngrok_public_url
    # Fallback to configured URL (won't work unless publicly accessible)
    return MCP_SERVER_URL


# ---- Create Anthropic client ----
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ---- Create FastAPI app ----
app = FastAPI(title="AI Database Chat")

# Allow browser to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- In-memory conversation storage (per session) ----
# In production you'd use Redis or a database
conversations = {}

# ---- Discover ngrok URL at startup ----
discover_ngrok_url()


# ---- Helper: extract text from Claude response ----
def extract_response_text(response) -> str:
    """Pull out the text from Claude's response content blocks."""
    texts = []
    for block in response.content:
        if hasattr(block, "text"):
            texts.append(block.text)
    return "\n".join(texts) if texts else "I processed your request but have no text response."


# ========================================================
#   API ENDPOINTS
# ========================================================

@app.post("/api/chat")
async def chat(request: Request):
    """
    Main chat endpoint.
    Receives: { "message": "user's question", "session_id": "abc123" }
    Returns:  { "reply": "Claude's answer", "session_id": "abc123" }
    """
    body = await request.json()
    user_message = body.get("message", "").strip()
    session_id = body.get("session_id", "default")

    if not user_message:
        return JSONResponse(
            status_code=400,
            content={"error": "Message cannot be empty"},
        )

    # Get or create conversation history for this session
    if session_id not in conversations:
        conversations[session_id] = []

    history = conversations[session_id]

    # Add user message to history
    history.append({"role": "user", "content": user_message})

    try:
        # Call Claude API WITH the MCP server address
        # THIS IS THE MAGIC — tell Claude about the MCP server
        # Uses the auto-discovered ngrok public URL so Claude API can reach it
        mcp_url = get_mcp_url()
        print(f"Using MCP URL: {mcp_url}/sse")

        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=(
                "You are a helpful AI assistant connected to a shop database via MCP tools. "
                "The database has customers, products, and orders tables. "
                "When users ask about data, use the available database tools to get real answers. "
                "Be friendly and format your responses clearly with markdown tables when showing data.\n\n"
                "TOOLS AVAILABLE (14 tools):\n"
                "- Database: db_health_check, db_get_customers, db_get_products, db_get_orders, db_run_query, db_get_schema\n"
                "- Code execution: execute_analysis — write Python code with def analyze(rows) to do calculations. "
                "All Python operations are allowed (os, subprocess, open, exec, eval, imports, etc). No restrictions.\n"
                "- Reports: create_pdf_report (styled PDF), create_html_report (HTML with Chart.js charts), list_reports\n"
                "- Self-extending tools: save_custom_tool, run_custom_tool, list_custom_tools\n\n"
                "SELF-EXTENDING TOOL SYSTEM:\n"
                "When you write useful analysis code with execute_analysis, SAVE it using save_custom_tool so it can be reused later. "
                "Before writing new code, CHECK list_custom_tools first to see if a similar tool already exists. "
                "If it does, use run_custom_tool to run it instead of rewriting the code.\n\n"
                "REPORTS:\n"
                "When generating reports, files are saved and accessible via /reports/<filename>. "
                "Always include a clickable link like [View Report](/reports/filename.html) so the user can open it. "
                "When asked for a sales report, analysis, or chart — use the report tools to create beautiful outputs."
            ),
            messages=history,
            # Tell Claude where the MCP server is (ngrok public URL)
            mcp_servers=[
                {
                    "type": "url",
                    "url": f"{mcp_url}/sse",
                    "name": "shop_database",
                }
            ],
            extra_headers={
                "anthropic-beta": "mcp-client-2025-04-04",
            },
        )

        # Extract the text reply
        reply = extract_response_text(response)

        # Add Claude's reply to history
        history.append({"role": "assistant", "content": reply})

        # Keep history manageable (last 40 messages = 20 back-and-forth)
        if len(history) > 40:
            history[:] = history[-40:]

        return {"reply": reply, "session_id": session_id}

    except anthropic.APIError as e:
        print(f"Claude API error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Claude API error: {str(e)}"},
        )
    except Exception as e:
        print(f"Server error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Server error: {str(e)}"},
        )


@app.post("/api/clear")
async def clear_chat(request: Request):
    """Clear conversation history for a session."""
    body = await request.json()
    session_id = body.get("session_id", "default")
    conversations.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}


@app.get("/api/health")
async def health():
    """Health check — shows configuration."""
    return {
        "status": "ok",
        "model": MODEL,
        "mcp_server_url": get_mcp_url(),
        "ngrok_tunnel": ngrok_public_url,
        "api_key_set": bool(ANTHROPIC_API_KEY),
    }


# ========================================================
#   SERVE GENERATED REPORTS (PDF + HTML)
# ========================================================

@app.get("/reports/{filename}")
async def serve_report(filename: str):
    """Serve a generated report file (PDF or HTML)."""
    # Security: only allow simple filenames (no path traversal)
    if "/" in filename or "\\" in filename or ".." in filename:
        return JSONResponse(status_code=400, content={"error": "Invalid filename"})

    filepath = os.path.join(REPORTS_DIR, filename)

    if not os.path.exists(filepath):
        return JSONResponse(status_code=404, content={"error": "Report not found"})

    if filename.endswith(".pdf"):
        return FileResponse(filepath, media_type="application/pdf", filename=filename)
    elif filename.endswith(".html"):
        return FileResponse(filepath, media_type="text/html", filename=filename)
    else:
        return FileResponse(filepath)


@app.get("/api/reports")
async def list_reports():
    """List all generated reports."""
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
                    "url": f"/reports/{fname}",
                })
    return {"reports": reports, "total": len(reports)}


# ========================================================
#   SERVE THE HTML FRONTEND
# ========================================================

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the chat interface."""
    return HTML_PAGE


# ========================================================
#   THE CHAT INTERFACE (HTML + CSS + JavaScript)
# ========================================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database AI Chat</title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

    <style>
        /* ---- Reset & Variables ---- */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-chat: #0e0e16;
            --bg-user-msg: #1a1a2e;
            --bg-ai-msg: #0f1923;
            --bg-input: #16161f;
            --border-color: #1e1e2e;
            --border-focus: #4a6cf7;
            --text-primary: #e8e8ed;
            --text-secondary: #8888a0;
            --text-muted: #55556a;
            --accent: #4a6cf7;
            --accent-glow: rgba(74, 108, 247, 0.15);
            --accent-green: #34d399;
            --accent-amber: #fbbf24;
            --accent-red: #f87171;
            --user-gradient: linear-gradient(135deg, #4a6cf7 0%, #6366f1 100%);
            --ai-border: #1a2a3a;
            --radius: 12px;
            --radius-lg: 16px;
        }

        body {
            font-family: 'DM Sans', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* ---- Header ---- */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 24px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            flex-shrink: 0;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .logo-icon {
            width: 40px;
            height: 40px;
            background: var(--user-gradient);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            box-shadow: 0 4px 16px rgba(74, 108, 247, 0.3);
        }

        .header-title {
            font-size: 18px;
            font-weight: 600;
            letter-spacing: -0.3px;
        }

        .header-subtitle {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 1px;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-badge.connected {
            background: rgba(52, 211, 153, 0.08);
            border: 1px solid rgba(52, 211, 153, 0.15);
            color: var(--accent-green);
        }

        .status-badge.error {
            background: rgba(248, 113, 113, 0.08);
            border: 1px solid rgba(248, 113, 113, 0.15);
            color: var(--accent-red);
        }

        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }

        .status-badge.connected .status-dot { background: var(--accent-green); }
        .status-badge.error .status-dot { background: var(--accent-red); }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        .clear-btn {
            padding: 6px 14px;
            background: transparent;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-secondary);
            font-size: 12px;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.2s;
        }

        .clear-btn:hover {
            border-color: var(--text-secondary);
            color: var(--text-primary);
            background: var(--bg-primary);
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* ---- Chat Area ---- */
        .chat-area {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            background: var(--bg-chat);
            scroll-behavior: smooth;
        }

        .chat-area::-webkit-scrollbar { width: 6px; }
        .chat-area::-webkit-scrollbar-track { background: transparent; }
        .chat-area::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }

        /* ---- Welcome Screen ---- */
        .welcome {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            flex: 1;
            text-align: center;
            padding: 40px;
            animation: fadeIn 0.6s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .welcome-icon {
            width: 72px;
            height: 72px;
            background: var(--user-gradient);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            margin-bottom: 24px;
            box-shadow: 0 8px 32px rgba(74, 108, 247, 0.25);
        }

        .welcome h2 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }

        .welcome p {
            color: var(--text-secondary);
            max-width: 440px;
            line-height: 1.6;
            font-size: 14px;
        }

        .suggestions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 28px;
            justify-content: center;
            max-width: 600px;
        }

        .suggestion-chip {
            padding: 10px 18px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: var(--text-secondary);
            font-size: 13px;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.2s;
        }

        .suggestion-chip:hover {
            border-color: var(--accent);
            color: var(--text-primary);
            background: var(--accent-glow);
            transform: translateY(-1px);
        }

        /* ---- Messages ---- */
        .message {
            display: flex;
            gap: 12px;
            max-width: 780px;
            width: 100%;
            margin: 0 auto;
            animation: messageIn 0.3s ease;
        }

        @keyframes messageIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.user { flex-direction: row-reverse; }

        .msg-avatar {
            width: 34px;
            height: 34px;
            border-radius: 9px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            flex-shrink: 0;
            margin-top: 2px;
        }

        .message.user .msg-avatar {
            background: var(--user-gradient);
            box-shadow: 0 2px 8px rgba(74, 108, 247, 0.3);
        }

        .message.ai .msg-avatar {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
        }

        .msg-content {
            padding: 14px 18px;
            border-radius: var(--radius);
            line-height: 1.65;
            font-size: 14px;
            max-width: calc(100% - 50px);
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        .message.user .msg-content {
            background: var(--bg-user-msg);
            border: 1px solid #252540;
            border-top-right-radius: 4px;
        }

        .message.ai .msg-content {
            background: var(--bg-ai-msg);
            border: 1px solid var(--ai-border);
            border-top-left-radius: 4px;
        }

        .msg-content p { margin-bottom: 10px; }
        .msg-content p:last-child { margin-bottom: 0; }

        .msg-content strong, .msg-content b {
            color: var(--accent);
            font-weight: 600;
        }

        .msg-content code {
            font-family: 'JetBrains Mono', monospace;
            background: rgba(255,255,255,0.06);
            padding: 2px 7px;
            border-radius: 5px;
            font-size: 12.5px;
        }

        .msg-content pre {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
            overflow-x: auto;
            margin: 10px 0;
        }

        .msg-content pre code {
            background: none;
            padding: 0;
            font-size: 12.5px;
            line-height: 1.5;
        }

        .msg-content ul, .msg-content ol {
            padding-left: 20px;
            margin: 8px 0;
        }

        .msg-content li { margin-bottom: 4px; }

        .msg-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 13px;
        }

        .msg-content th, .msg-content td {
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            text-align: left;
        }

        .msg-content th {
            background: var(--bg-secondary);
            font-weight: 600;
            color: var(--accent);
        }

        .msg-content .error-msg {
            color: var(--accent-red);
            padding: 10px 14px;
            background: rgba(248, 113, 113, 0.06);
            border: 1px solid rgba(248, 113, 113, 0.15);
            border-radius: 8px;
        }

        /* ---- Thinking indicator ---- */
        .thinking {
            display: flex;
            gap: 12px;
            max-width: 780px;
            width: 100%;
            margin: 0 auto;
            animation: messageIn 0.3s ease;
        }

        .thinking-dots {
            padding: 16px 20px;
            background: var(--bg-ai-msg);
            border: 1px solid var(--ai-border);
            border-radius: var(--radius);
            border-top-left-radius: 4px;
            display: flex;
            gap: 5px;
            align-items: center;
        }

        .thinking-dots span {
            width: 7px;
            height: 7px;
            background: var(--text-muted);
            border-radius: 50%;
            animation: bounce 1.4s ease-in-out infinite;
        }

        .thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
        .thinking-dots span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-8px); }
        }

        .thinking-label {
            font-size: 12px;
            color: var(--text-muted);
            margin-left: 4px;
        }

        /* ---- Input Area ---- */
        .input-area {
            padding: 16px 24px 20px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            flex-shrink: 0;
        }

        .input-wrapper {
            max-width: 780px;
            margin: 0 auto;
            display: flex;
            gap: 10px;
            align-items: flex-end;
        }

        .input-box {
            flex: 1;
            position: relative;
        }

        .input-box textarea {
            width: 100%;
            padding: 14px 18px;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: var(--radius);
            color: var(--text-primary);
            font-family: 'DM Sans', sans-serif;
            font-size: 14px;
            resize: none;
            outline: none;
            min-height: 48px;
            max-height: 150px;
            line-height: 1.5;
            transition: border-color 0.2s;
        }

        .input-box textarea::placeholder { color: var(--text-muted); }
        .input-box textarea:focus { border-color: var(--border-focus); }

        .send-btn {
            width: 48px;
            height: 48px;
            background: var(--user-gradient);
            border: none;
            border-radius: var(--radius);
            color: white;
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            flex-shrink: 0;
            box-shadow: 0 2px 12px rgba(74, 108, 247, 0.3);
        }

        .send-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(74, 108, 247, 0.4);
        }

        .send-btn:disabled {
            opacity: 0.4;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .input-hint {
            text-align: center;
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 8px;
        }

        /* ---- Responsive ---- */
        @media (max-width: 640px) {
            .header { padding: 12px 16px; }
            .chat-area { padding: 16px; }
            .input-area { padding: 12px 16px 16px; }
            .suggestions { flex-direction: column; }
            .header-subtitle { display: none; }
        }
    </style>
</head>
<body>

    <!-- Header -->
    <div class="header">
        <div class="header-left">
            <div class="logo-icon">&#9889;</div>
            <div>
                <div class="header-title">Database AI Chat</div>
                <div class="header-subtitle">Powered by Claude + MCP</div>
            </div>
        </div>
        <div class="header-right">
            <div class="status-badge connected" id="statusBadge">
                <div class="status-dot"></div>
                <span id="statusText">Checking...</span>
            </div>
            <button class="clear-btn" onclick="clearChat()">Clear Chat</button>
        </div>
    </div>

    <!-- Chat Area -->
    <div class="chat-area" id="chatArea">
        <div class="welcome" id="welcome">
            <div class="welcome-icon">&#128451;&#65039;</div>
            <h2>Talk to Your Database</h2>
            <p>Ask questions about your customers, products, and orders.
               Claude will use MCP tools to query the database and give you real answers.</p>
            <div class="suggestions">
                <button class="suggestion-chip" onclick="sendSuggestion(this)">Show me all customers</button>
                <button class="suggestion-chip" onclick="sendSuggestion(this)">What products do we sell?</button>
                <button class="suggestion-chip" onclick="sendSuggestion(this)">Who are the top spenders?</button>
                <button class="suggestion-chip" onclick="sendSuggestion(this)">Show orders from London customers</button>
                <button class="suggestion-chip" onclick="sendSuggestion(this)">How many orders were cancelled?</button>
            </div>
        </div>
    </div>

    <!-- Input Area -->
    <div class="input-area">
        <div class="input-wrapper">
            <div class="input-box">
                <textarea
                    id="messageInput"
                    rows="1"
                    placeholder="Ask about your data..."
                    onkeydown="handleKeyDown(event)"
                    oninput="autoResize(this)"
                ></textarea>
            </div>
            <button class="send-btn" id="sendBtn" onclick="sendMessage()">&#8593;</button>
        </div>
        <div class="input-hint">Press Enter to send &middot; Shift+Enter for new line</div>
    </div>

    <script>
        // ---- State ----
        const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
        let isWaiting = false;

        // ---- Elements ----
        const chatArea = document.getElementById('chatArea');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const welcome = document.getElementById('welcome');
        const statusBadge = document.getElementById('statusBadge');
        const statusText = document.getElementById('statusText');

        // ---- Check server health on load ----
        async function checkHealth() {
            try {
                const res = await fetch('/api/health');
                const data = await res.json();
                if (data.status === 'ok' && data.api_key_set) {
                    statusBadge.className = 'status-badge connected';
                    statusText.textContent = 'MCP Connected';
                } else {
                    statusBadge.className = 'status-badge error';
                    statusText.textContent = 'API Key Missing';
                }
            } catch (e) {
                statusBadge.className = 'status-badge error';
                statusText.textContent = 'Server Error';
            }
        }
        checkHealth();

        // ---- Send message ----
        async function sendMessage() {
            const text = messageInput.value.trim();
            if (!text || isWaiting) return;

            // Hide welcome screen
            if (welcome) welcome.style.display = 'none';

            // Show user message
            appendMessage('user', text);
            messageInput.value = '';
            messageInput.style.height = 'auto';
            setWaiting(true);

            // Show thinking indicator
            const thinkingEl = showThinking();

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, session_id: sessionId }),
                });

                const data = await res.json();
                removeThinking(thinkingEl);

                if (data.error) {
                    appendMessage('ai', '<div class="error-msg">' + escapeHtml(data.error) + '</div>', true);
                } else {
                    appendMessage('ai', data.reply);
                }
            } catch (err) {
                removeThinking(thinkingEl);
                appendMessage('ai', '<div class="error-msg">Connection error. Is the server running?</div>', true);
            }

            setWaiting(false);
        }

        // ---- Escape HTML ----
        function escapeHtml(text) {
            return text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
        }

        // ---- Append message to chat ----
        function appendMessage(role, text, isHtml) {
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message ' + role;

            const avatar = document.createElement('div');
            avatar.className = 'msg-avatar';
            avatar.textContent = role === 'user' ? String.fromCodePoint(0x1F464) : String.fromCodePoint(0x1F916);

            const content = document.createElement('div');
            content.className = 'msg-content';
            content.innerHTML = isHtml ? text : formatMarkdown(text);

            msgDiv.appendChild(avatar);
            msgDiv.appendChild(content);
            chatArea.appendChild(msgDiv);
            scrollToBottom();
        }

        // ---- Markdown formatting ----
        function formatMarkdown(text) {
            // Escape HTML first
            let html = escapeHtml(text);

            // Code blocks (``` ... ```)
            html = html.replace(/```(\\w+)?\\n([\\s\\S]*?)```/g, '<pre><code>$2</code></pre>');
            html = html.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');

            // Inline code
            html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

            // Bold
            html = html.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');

            // Italic
            html = html.replace(/\\*(.+?)\\*/g, '<em>$1</em>');

            // Links [text](url)
            html = html.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2" target="_blank" style="color:#4a6cf7;text-decoration:underline">$1</a>');

            // Tables (| col | col |)
            html = html.replace(
                /((?:^\\|.+\\|$\\n?)+)/gm,
                function(match) {
                    const rows = match.trim().split('\\n');
                    let table = '<table>';
                    rows.forEach(function(row, i) {
                        // Skip separator rows (|---|---|)
                        if (row.match(/^\\|[\\s\\-:]+\\|$/)) return;
                        const cells = row.split('|').filter(function(c) { return c.trim() !== ''; });
                        const tag = i === 0 ? 'th' : 'td';
                        table += '<tr>';
                        cells.forEach(function(cell) {
                            table += '<' + tag + '>' + cell.trim() + '</' + tag + '>';
                        });
                        table += '</tr>';
                    });
                    table += '</table>';
                    return table;
                }
            );

            // Headers
            html = html.replace(/^### (.+)$/gm, '<strong style="font-size:14px;display:block;margin:8px 0 4px">$1</strong>');
            html = html.replace(/^## (.+)$/gm, '<strong style="font-size:15px;display:block;margin:8px 0 4px">$1</strong>');
            html = html.replace(/^# (.+)$/gm, '<strong style="font-size:16px;display:block;margin:8px 0 4px">$1</strong>');

            // Unordered lists
            html = html.replace(/^[\\-\\*] (.+)$/gm, '<li>$1</li>');
            html = html.replace(/((?:<li>.*<\\/li>\\n?)+)/g, '<ul>$1</ul>');

            // Ordered lists
            html = html.replace(/^\\d+\\. (.+)$/gm, '<li>$1</li>');

            // Line breaks to paragraphs
            html = html
                .split('\\n\\n')
                .map(function(p) { return '<p>' + p.replace(/\\n/g, '<br>') + '</p>'; })
                .join('');

            return html;
        }

        // ---- Thinking indicator ----
        function showThinking() {
            const div = document.createElement('div');
            div.className = 'thinking';
            div.innerHTML =
                '<div class="msg-avatar" style="background:var(--bg-secondary);border:1px solid var(--border-color)">' + String.fromCodePoint(0x1F916) + '</div>' +
                '<div>' +
                '  <div class="thinking-dots">' +
                '    <span></span><span></span><span></span>' +
                '    <span class="thinking-label">Claude is thinking...</span>' +
                '  </div>' +
                '</div>';
            chatArea.appendChild(div);
            scrollToBottom();
            return div;
        }

        function removeThinking(el) {
            if (el && el.parentNode) el.parentNode.removeChild(el);
        }

        // ---- UI helpers ----
        function setWaiting(waiting) {
            isWaiting = waiting;
            sendBtn.disabled = waiting;
            messageInput.disabled = waiting;
            if (!waiting) messageInput.focus();
        }

        function scrollToBottom() {
            requestAnimationFrame(function() {
                chatArea.scrollTop = chatArea.scrollHeight;
            });
        }

        function handleKeyDown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }

        function autoResize(el) {
            el.style.height = 'auto';
            el.style.height = Math.min(el.scrollHeight, 150) + 'px';
        }

        function sendSuggestion(el) {
            messageInput.value = el.textContent;
            sendMessage();
        }

        async function clearChat() {
            try {
                await fetch('/api/clear', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId }),
                });
            } catch (e) {}

            // Reset UI
            chatArea.innerHTML = '';
            if (welcome) {
                chatArea.appendChild(welcome);
                welcome.style.display = 'flex';
            }
        }

        // ---- Focus input on load ----
        messageInput.focus();
    </script>

</body>
</html>
"""


# ---- Run ----
if __name__ == "__main__":
    import uvicorn
    print("=" * 55)
    print("  Chat Server starting on http://localhost:3000")
    print("  Open your browser and start chatting!")
    print("=" * 55)
    uvicorn.run(app, host="0.0.0.0", port=3000)
