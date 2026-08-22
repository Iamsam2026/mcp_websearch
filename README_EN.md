[中文](README_CN.md) | English


> **Note**: This English version is AI-translated for reference only. The original Chinese README (`README.md` or `README_CN.md`) is the authoritative source. Please refer to it for the most accurate and up-to-date information.

# mcp-websearch-ai

> **Project Statement**: This project is proposed and led by me (lamsam2026). The code is generated with AI assistance, and I am responsible for compilation, debugging, functional verification, and final review. I assume full responsibility for code quality, security, and compliance.

> **AI Assistance Disclosure**: The core code of this project is AI-generated and has been reviewed and modified manually. Please read this disclosure and the license terms carefully before use.

> **Environment Note**: This tool and its test scripts have been tested and debugged **only on Windows 11**. Other operating systems (such as macOS, Linux) have not been fully validated and may have compatibility issues. Users should evaluate accordingly.

An MCP (Model Context Protocol) server that integrates **web search + AI-powered summarization**, enabling direct search and AI analysis capabilities through conversation in MCP clients.

**UTF-8 encoding fully fixed**, supports both local APIs and cloud APIs, ready to use out of the box.

---

## ✨ Features

| Feature | Description |
| :--- | :--- |
| 🔍 **web_search** | Search the web using Bing (accessible from China, no proxy required) |
| 📄 **fetch_webpage** | Fetch and extract plain text from a webpage |
| 🤖 **ai_summarize** | AI-powered structured JSON summary of provided content |
| ⚡ **search_and_summarize** | **One-click search -> assemble -> AI summary (recommended)** with **smart summarization** toggle |
| ⚙️ **set_ai_config** | Temporarily modify AI configuration (session only) |
| 🔧 **test_api** | Test AI API connectivity, quickly diagnose key/network issues |
| 📖 **get_tutorial** | Get the full server tutorial |

### Smart Summarization

- When enabled, **AI summary is triggered only when content exceeds the character threshold**; otherwise, only search results are returned — saves tokens and speeds up responses
- Threshold and toggle can be set via parameters or via default constants in the code header

---

## 📦 Requirements

| Item | Requirement |
| :--- | :--- |
| Python | 3.9 or higher |
| Dependencies | `requests` (only one) |
| AI Backend (choose one) | ① Cloud API (OpenAI-compatible format); ② Local API (e.g., LM Studio, etc.) |

### Install Dependencies

```bash
pip install requests
```

---

## ⚙️ Configuration

Open `mcp_websearch_server.py` and fill in the configuration section at the top of the file:

**Option 1: Cloud API (using DeepSeek as an example)**

```python
YOUR_API_KEY = "sk-your-real-key"                        # Replace with your actual API key
YOUR_API_URL = "https://api.deepseek.com/v1/chat/completions"
YOUR_MODEL   = "deepseek-chat"
```

**Option 2: Local API (using LM Studio as an example, fully offline, no real key required)**

```python
YOUR_API_KEY = "lm-studio"                               # Placeholder, local service doesn't validate
YOUR_API_URL = "http://localhost:1234/v1/chat/completions"
YOUR_MODEL   = "your-model-name"                         # e.g., qwen2.5-7b-instruct
```

**General Steps for Local API:**

1. Start your local API service (e.g., LM Studio's 「Start Server」)
2. Access the model list endpoint provided by the service in your browser to get the exact model name
3. Fill the model name into `YOUR_MODEL`
4. Save the code -> Restart MCP client -> run `test_api` to verify

> 💡 To switch between cloud and local: modify the three values at the top of the code -> restart the client.

---

> 🔐 **Security Reminder**: Never commit code containing real API keys to public repositories. Use environment variables or a `.env` file with `.gitignore` to manage keys. If you prefer hardcoding, keep it strictly local and always review the file before each commit.

---

## ⏱️ Timeout & Smart Summarization Constants (at top of file)

```python
MCP_SERVER_NAME = "mcp-websearch-ai"
MCP_SERVER_VERSION = "1.0.0"
SEARCH_TIMEOUT = 15
AI_TIMEOUT = 300

AUTO_SUMMARIZE_DEFAULT = True
AUTO_SUMMARIZE_THRESHOLD = 2000
```

> ⚠️ **For local models**: The default `AI_TIMEOUT` of 60 seconds will likely time out — set it to 300. If `test_api` also times out, change the hardcoded `timeout=15` inside that function to `timeout=AI_TIMEOUT`.

---

## 🚀 Quick Start

**1. Register the MCP Server (Claude Desktop example)**

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "websearch-ai": {
      "command": "python",
      "args": ["C:\\your-full-path\\mcp_websearch_server.py"]
    }
  }
}
```

For other MCP clients, fill in the startup command and script path in their respective settings interface.

**2. Restart the Client** -> Fully exit and reopen.

**3. Verify Connectivity** -> Enter `test_api` in the conversation, returns `"status": "ok"` if configured correctly.

**4. Start Using**

```
search_and_summarize(query="2024年中国GDP (China's GDP in 2024)", purpose="了解中国经济形势 (understand China's economic situation)", num_results=5)
```

---

## 📋 Author-Tested Compatible Clients

The following MCP clients have been tested and verified to work with this tool:

- Claude Desktop
- DeepSeek Harness
- LM Studio
- AnythingLLM
- Cursor

> **Compatibility Note**: This tool strictly follows the **MCP (Model Context Protocol) standard call format** and is theoretically compatible with all clients that support the MCP protocol. The list above represents environments the author has personally tested and does **not imply that only these clients are supported**. Users are encouraged to try configuring this tool in other MCP clients.

> **Disclaimer**: The software names listed above are provided solely to describe the test environment for this tool and **do not constitute any commercial promotion**. The list is for reference only and does not imply any partnership, affiliation, endorsement, or recommendation between the author and the respective software vendors. Users should independently evaluate and comply with each software's terms of use.

---

## 🛠️ Tool Reference

### 1️⃣ search_and_summarize (✅ Preferred)

One-click search + AI summary, returns a complete JSON analysis report.

| Parameter | Required | Description |
| :--- | :--- | :--- |
| `query` | ✅ | Search keywords |
| `purpose` | ✅ | Purpose of the summary |
| `num_results` | ❌ | Number of results (default 5) |
| `smart_summarize` | ❌ | Smart summary toggle: `True`=on (summarize only above threshold); `False`=off (always summarize); not set = uses default constant |
| `summarize_threshold` | ❌ | Character threshold for summary trigger; not set = uses `AUTO_SUMMARIZE_THRESHOLD` |

**Smart Summarization Behavior:**

| `SMART_SUMMARIZE` | Content < Threshold | Content >= Threshold | Effect |
| :--- | :--- | :--- | :--- |
| `True` (or default) | Returns only search results, no AI | Auto‑triggers AI summary | Saves tokens, fast |
| `False` | Always summarizes | Always summarizes | Restores "always summarize" behavior |
| Not set | Uses default constant (default `True`) | Same as above | Controlled by code header |

**Examples:**

```python
search_and_summarize(query="2025年人工智能趋势 (AI trends in 2025)", purpose="了解AI产业动向 (understand AI industry dynamics)")

search_and_summarize(query="人工智能趋势 (AI trends)", purpose="深度调研 (deep research)", smart_summarize=True, summarize_threshold=5000)

search_and_summarize(query="今天的新闻 (today's news)", purpose="了解热点 (understand hot topics)", smart_summarize=False)
```

**Return Format:**

```json
{
  "summary": "Overall summary",
  "key_points": [{"point": "Key point", "detail": "Details"}],
  "analysis": "In-depth analysis",
  "sources": ["Source URLs"],
  "limitations": "Limitations description",
  "follow_up_queries": ["Follow-up questions"]
}
```

When summarization is not triggered: returns `auto_summarized: false` + full search result list + explanatory message.

---

### 2️⃣ web_search

Performs a search only, returns raw results (title/URL/snippet).

| Parameter | Required | Description |
| :--- | :--- | :--- |
| `query` | ✅ | Search keywords |
| `num_results` | ❌ | Number of results (default 8) |

---

### 3️⃣ fetch_webpage

Fetches plain text from a specified webpage.

| Parameter | Required | Description |
| :--- | :--- | :--- |
| `url` | ✅ | Webpage URL |
| `max_chars` | ❌ | Maximum characters (default 5000) |

---

### 4️⃣ ai_summarize

Runs AI‑powered structured summary on provided text content.

| Parameter | Required | Description |
| :--- | :--- | :--- |
| `search_context` | ✅ | Existing content |
| `purpose` | ✅ | Summary purpose |

---

### 5️⃣ set_ai_config

Temporarily modifies AI configuration (resets to code‑header values on restart).

| Parameter | Description |
| :--- | :--- |
| `api_key` | API key (optional) |
| `api_url` | API endpoint URL (optional) |
| `model` | Model name (optional) |

---

### 6️⃣ test_api

Tests API connectivity. No parameters. Returns key, URL, and network status.

---

### 7️⃣ get_tutorial

Retrieves the built‑in server tutorial. No parameters.

---

## 🧪 Debugging & Self-Test Scripts

This tool includes three test scripts for different verification and debugging scenarios.

> **Test Environment Note**: This tool and its test scripts have been tested and debugged **only on Windows 11**. Other operating systems may have compatibility issues.

---

### 📁 Script Overview

| Script | Purpose | Use Case |
| :--- | :--- | :--- |
| `text_client.py` | Functional integrity test | Verify all tools are working properly |
| `text_isolated.py` | Isolated refinement test | Verify AI auto‑refine logic |
| `text_all.py` | One‑click full test | Run both scripts and check logs |

---

### 1️⃣ text_client.py — Functional Integrity Test

**How it works**: Simulates MCP protocol tool calls to sequentially invoke the 7 core tools, checking return values to verify each function.

**Test Coverage**:

| # | Test | Target |
| :--- | :--- | :--- |
| ① | `test_api` | API connectivity, key validity |
| ② | `web_search` (Chinese) | UTF‑8 encoding, search availability |
| ③ | `ai_summarize` (deep thinking) | AI returns structured JSON summary |
| ④ | `search_and_summarize` (large threshold) | Smart summarize correctly skips when content is insufficient |
| ⑤ | `search_and_summarize` (small threshold) | Smart summarize correctly triggers when content is sufficient |
| ⑥ | `search_and_summarize` (new params) | `thinking_level`, `fidelity`, `max_refine_rounds` work correctly |
| ⑦ | `get_tutorial` | Tutorial includes new parameter descriptions |

**Run**:
```bash
python text_client.py
```

**Output**:
- Each test shows ✅ / ❌
- Failed items show **missing keywords** and **actual returned content**
- Final summary: `X items total, Y passed, Z failed`

---

### 2️⃣ text_isolated.py — Isolated Refinement Test

**How it works**: Uses **process-level network isolation** + **local simulated websites** to verify the AI auto-refine logic in a fully controlled environment.

**Implementation**:

1. **Launches 15 local virtual websites** (ports 8001–8015):
   - **2 useful sites**: Contain precise 2024 China GDP data from the National Bureau of Statistics (CNY 134.9084 trillion, 5.0% growth, etc.)
   - **13 noise sites**: Titles and content heavily mention "GDP", "economy", "growth", etc., but **contain no precise official data**

2. **Process-level network isolation**:
   - Uses `monkey-patch` to intercept `socket.create_connection`
   - Only allows connections to: **local virtual sites (127.0.0.1)** and the **user-configured AI API domain**
   - **All other external connections are blocked**, ensuring the test does not rely on the real internet
   - Isolation only affects the current process; other system programs are unaffected. The isolation automatically disables when the process exits

3. **Search engine replacement**:
   - Temporarily replaces `BingSearchEngine.search` with a "local fake search"
   - The fake search only matches keywords against the 15 local virtual sites and returns results based on match quality

4. **Test logic**:
   - **1st search**: Fake search returns only the 13 noise sites -> AI finds no precise data -> automatically requests refinement
   - **2nd search (refinement)**: AI generates follow‑up queries -> fake search re‑matches -> useful sites (with +100 base score) are prioritized -> AI receives precise data -> generates final summary

5. **Pass criteria**:
   - Search calls >= 2 (proves refinement was triggered)
   - Final output contains "134.9" or "1349084" (GDP total)
   - Final output contains "5.0" (GDP growth rate)
   - Sources point to local useful sites (port 8001 or 8002)
   - Complete JSON structure (with `summary` and `key_points`)

**Run**:
```bash
python text_isolated.py
```

**Output**:
- Shows startup status of 15 local sites
- Shows process-level isolation is active
- Shows each search call log and hits
- Lists 5 verification criteria with pass/fail status
- Final test conclusion

---

### 3️⃣ text_all.py — One‑Click Full Test

**How it works**: Sequentially runs `text_client.py` and `text_isolated.py`, then automatically checks whether complete refinement logs are present in the `logs/` directory.

**Execution Flow**:

1. Runs `text_client.py` (7 functional tests)
2. Runs `text_isolated.py` (isolated refinement test)
3. Checks the `logs/` directory

**Run**:
```bash
python text_all.py
```

**Output**:
- Shows output from both sub‑scripts
- Shows log check results
- Final summary: whether all three items passed

---

### 📊 Relationship Between the Three Scripts

```
+---------------------------------------------+
|              text_all.py                    |
|         (One-Click Full Test)               |
|    +--------------------------------+       |
|    |      text_client.py           |       |
|    |   (7 Functional Tests)        |       |
|    +--------------------------------+       |
|    +--------------------------------+       |
|    |      text_isolated.py         |       |
|    |  (Isolated Refinement Test)   |       |
|    +--------------------------------+       |
|    +--------------------------------+       |
|    |      Check logs/ directory     |       |
|    |   (Verify logs are generated)  |       |
|    +--------------------------------+       |
+---------------------------------------------+
```

---

## 📋 Recommended Workflows

```
★ Daily queries (recommended):
   search_and_summarize(query="搜索词 (search term)", purpose="总结目的 (summary purpose)")

★ Deep research:
   ① web_search(query="搜索词 (search term)", num_results=8)
   ② fetch_webpage(url="权威链接 (authoritative link)")
   ③ ai_summarize(search_context=已获取内容 (retrieved content), purpose="深度分析 (deep analysis)")

★ Troubleshooting:
   ① test_api -> confirm API is healthy
   ② set_ai_config -> correct config if needed
   ③ retry
```

---

## 🤖 Recommended System Prompt

Provide this prompt to your AI assistant in the MCP client to standardize usage of this tool:

```
You are a professional web information retrieval and analysis assistant, connected to real-time web search and AI summarization capabilities via the MCP server "mcp-websearch-ai".

【Available Tools】
1. search_and_summarize (preferred): One-click search + AI summary. Params: query (required), purpose (required), num_results (optional, default 5), smart_summarize (optional), summarize_threshold (optional)
2. web_search: Search only. Params: query (required), num_results (optional, default 8)
3. fetch_webpage: Fetch webpage text. Params: url (required), max_chars (optional, default 5000)
4. ai_summarize: Structured JSON summary of existing text. Params: search_context (required), purpose (required)
5. set_ai_config: Temporarily modify AI config (api_key/api_url/model all optional)
6. test_api: Test API connectivity, call first on errors
7. get_tutorial: Get full tutorial

【Recommended Workflows】
- Preferred: search_and_summarize(query="...", purpose="...") -> one-step analysis report
- Deep research: web_search -> fetch_webpage(authoritative link) -> ai_summarize
- Troubleshooting: test_api -> set_ai_config -> retry

【Output Guidelines】
1. Key data must include sources (URL or authoritative media name), prefer tables for comparison
2. Convert JSON analysis report to readable format, keep summary/key_points/analysis/sources/follow_up_queries
3. Data reliability priority: government websites > mainstream media/academic databases > reputable industry reports > general information sites
4. For sensitive topics (policies, statistics, healthcare), add "please refer to official sources"

【Notes】
- Both Chinese and English search are supported (Bing global), but the internal prompts are written in Chinese — ensure the API model you use has strong Chinese comprehension capabilities
- Search engine is Bing (accessible from China, no proxy required)
- AI backend requires user configuration; run test_api first on errors
- num_results recommended 3-8; more can dilute summary quality
- If search results are empty or low-relevance, retry with different keywords
- When user doesn't specify, prefer search_and_summarize

【Tool Call Format】
search_and_summarize(query="2024年中国GDP (China's GDP in 2024)", purpose="了解经济形势 (understand economic situation)", num_results=5)
web_search(query="人工智能 2025 趋势 (AI trends 2025)", num_results=8)
fetch_webpage(url="https://www.stats.gov.cn/...")
ai_summarize(search_context="已获取的文本内容 (retrieved content)...", purpose="深度分析 (deep analysis)")
test_api
get_tutorial
```

---

## ⚠️ Legal & Compliance Notice

- **Bing Search**: This tool accesses Bing's public web pages via simulated browser requests. It is intended **for personal learning and research purposes only**. For commercial projects or large-scale deployment, please use the official [Bing Web Search API](https://www.microsoft.com/en-us/bing/apis/bing-web-search-api) to comply with their terms of service.
- **AI-Generated Content**: This tool's code was generated with AI assistance and reviewed by the author. Users should independently assess its suitability and security.
- **License**: This tool is licensed under the MIT License — see the [License](#-license) section below.

---

## 📦 File Migration / Deployment (New Computer)

Core file: `mcp_websearch_server.py` (single-file run, configs written inside).

1. Copy `mcp_websearch_server.py` to the new computer
2. Install Python 3.9+ on new computer -> `pip install requests`
3. Configure MCP client to point to the new path
4. Fully restart client -> `test_api` to verify

> 💡 Avoid Chinese characters and spaces in the path (e.g., `C:\mcp\`) to prevent client parsing issues.
> 💡 API keys are account-level and remain valid across computers.
> ⚠️ The key is in plain text in the file — do not share it or commit it to public repositories.

---

## ❓ FAQ

**Q1: Chinese characters appear garbled?**

The server forces UTF-8 on stdin/stdout/stderr. Garbled output in CMD is due to the terminal's default GBK encoding — MCP clients (which parse UTF-8) display correctly.

**Q2: test_api times out / connection fails?**

- Cloud: Check `YOUR_API_URL`
- Local: Confirm local API service is running and the port is not occupied
- Timeout too short: Increase `AI_TIMEOUT` (300 for local models); also change the hardcoded `timeout=15` inside `test_api` to `timeout=AI_TIMEOUT`

**Q3: test_api returns 401 invalid key?**

- Check that `YOUR_API_KEY` is complete; check if the key has expired (cloud)
- Local API services typically don't validate keys — use any placeholder (must not be empty)

**Q4: Model not found?**

- Local: Query the model list endpoint from your service to get the exact model name and put it into `YOUR_MODEL`
- Cloud: Confirm the model name matches your provider

**Q5: search_and_summarize did not trigger summarization?**

Smart summarization is enabled by default — content below the threshold returns only search results (this is normal). To force summarization: set `smart_summarize=False` or lower `summarize_threshold`.

**Q6: Model returns poor quality results?**

The internal prompts are written in Chinese — ensure the API model you use has strong Chinese comprehension capabilities. Weaker Chinese understanding may degrade summary quality.

---

## 📄 Version & Update Policy

This tool is written to address current needs. **No regular updates or version iterations are promised**. Please do not have high expectations for future updates. Barring major issues, this version is intended for long-term use.

Current version: **v1.0.0**

---

## 📄 License

This project is licensed under the **MIT License**.

The MIT License is a permissive open-source license that allows anyone to:

- ✅ Freely use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software
- ✅ Use the Software for any purpose, including commercial
- ✅ Modify source code and keep modifications closed-source

**The only requirement**: In all copies or substantial portions of the Software, the original copyright notice and this permission notice must be retained.

**Disclaimer**: The Software is provided "AS IS", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the Software or the use or other dealings in the Software.

```
Copyright (c) 2026 lamsam2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
