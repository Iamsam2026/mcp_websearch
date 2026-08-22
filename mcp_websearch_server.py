#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP WebSearch + AISummary Server（最终版 v2.0）
==============================================
功能：web_search / fetch_webpage / ai_summarize / set_ai_config /
      get_tutorial / test_api / search_and_summarize
协议：MCP (Model Context Protocol) / JSON-RPC 2.0 over stdio

✅ 本版本特性：
  1. 中文编码彻底修复（stdin/stdout/stderr 全 UTF-8）
  2. search_and_summarize 一键搜索+总结（推荐）
     - 智能转总结开关（smart_summarize / summarize_threshold）
     - 思考深度（thinking_level: normal/deep）
     - 数据保真度（fidelity 1~5，默认3）
     - 自动补搜（max_refine_rounds）：AI 申请补搜时自动继续搜索
     - ★ 完整思考日志：一次调用 = logs/申请搜索内容和数据_xxx/ 一个文件夹
       内含每轮搜索词、结果网址、AI原始输出、补搜决策、最终结果
  3. ai_summarize 支持思考深度
  4. AI 温度可配置（AI_TEMPERATURE，越低越客观稳定，防幻觉）
  5. 提示词强化：数据保真铁律、禁止编造、来源可溯、置信度分级、信息缺口诚实报告
"""
import sys, json, requests, html, re, os, traceback, io, time
from typing import Any, Dict, List, Optional

# ========== 【终极编码修复】强制 stdin/stdout/stderr 全部 UTF-8 ==========
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

if sys.stdin and hasattr(sys.stdin, 'buffer') and not hasattr(sys.stdin, '_utf8_wrapped'):
    try:
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        sys.stdin._utf8_wrapped = True
    except Exception:
        pass
if sys.stdout and hasattr(sys.stdout, 'buffer') and not hasattr(sys.stdout, '_utf8_wrapped'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        sys.stdout._utf8_wrapped = True
    except Exception:
        pass
# ========================================================================


# ========== 配置区 ==========
MCP_SERVER_NAME = "mcp-websearch-ai"
MCP_SERVER_VERSION = "2.0.0"
SEARCH_TIMEOUT = 15      # Bing搜索/网页抓取 超时（秒）
AI_TIMEOUT = 300         # AI 模型返回 超时（秒）

# 【智能转总结】配置
AUTO_SUMMARIZE_DEFAULT = True      # 智能转总结默认开关：True=开启，False=关闭
AUTO_SUMMARIZE_THRESHOLD = 2000    # 触发自动总结的字数阈值

# 【AI 温度】配置（越低越客观稳定；0=完全确定；1=最随机）
AI_TEMPERATURE = 0.05

# 【高级参数】默认值
THINKING_LEVEL_DEFAULT = "normal"  # 思考深度：normal=标准，deep=深度思考
FIDELITY_DEFAULT = 3               # 数据保真度 1~5：1宽松 / 3标准 / 5逐字保真
MAX_REFINE_ROUNDS_DEFAULT = 1      # 自动补搜轮数：0=关闭


# ============================================================
# 👇 请在这里填写你的 API 配置（不用 config.json 了）
# ============================================================
YOUR_API_KEY = "your api key"                                        # ← 你的密钥
YOUR_API_URL = "your api url"      # ← API 地址
YOUR_MODEL   = "your model"                                       # ← 模型名称
# ============================================================

_ai_config = {
    "api_key": YOUR_API_KEY or "",
    "api_url": YOUR_API_URL or "",
    "model": YOUR_MODEL or "",
    "temperature": AI_TEMPERATURE
}


# ========== 字符清洗（解决中文崩溃） ==========
def _clean_surrogates(text):
    if not isinstance(text, str):
        return text
    try:
        return text.encode('utf-8', 'replace').decode('utf-8')
    except Exception:
        try:
            return ''.join(c if ord(c) < 0xD800 or ord(c) > 0xDFFF else '?' for c in text)
        except:
            return str(text)


def _clean_surrogates_deep(obj):
    if isinstance(obj, str):
        return _clean_surrogates(obj)
    elif isinstance(obj, dict):
        return {k: _clean_surrogates_deep(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_surrogates_deep(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(_clean_surrogates_deep(v) for v in obj)
    return obj


def _json_safe(obj):
    try:
        cleaned = _clean_surrogates_deep(obj)
        line = json.dumps(cleaned, ensure_ascii=False, default=str)
        return _clean_surrogates(line)
    except Exception:
        try:
            line = json.dumps(obj, ensure_ascii=True, default=str)
            return _clean_surrogates(line)
        except Exception as e:
            return json.dumps({"error": f"JSON序列化失败: {str(e)}"})


# ========== 内置教程（最新版） ==========
_TUTORIAL = {
    "server_name": "mcp-websearch-ai",
    "version": "2.0.0",
    "description": "集成了Bing搜索引擎和AI摘要功能的MCP服务器，支持一键搜索+总结",
    "config_note": "API配置直接在代码开头的变量中填写（YOUR_API_KEY / YOUR_API_URL / YOUR_MODEL），无需config.json",
    "quick_start": [
        "1. 打开 mcp_websearch_server.py，在开头 YOUR_API_KEY 处填入密钥",
        "2. 保存文件，重启 MCP 客户端",
        "3. 输入 test_api 验证连通性",
        "4. 输入 search_and_summarize(query='xxx', purpose='xxx') 一键完成搜索+总结"
    ],
    "tools": [
        {
            "name": "search_and_summarize",
            "desc": "✅ 一键搜索+总结（推荐）",
            "params": {
                "query": "搜索关键词（必填）",
                "purpose": "总结目的（必填）",
                "num_results": "搜索条数，默认5，可1~10灵活调整",
                "smart_summarize": "智能转总结开关：True=超阈值才总结；False=总是总结；不填=默认常量",
                "summarize_threshold": "触发总结字数阈值，不填=默认常量",
                "thinking_level": "思考深度：normal=标准（快）；deep=深度思考（全面、慢）",
                "fidelity": "数据保真度1~5（默认3）：1宽松；3标准（保留关键数字日期）；5逐字保真",
                "max_refine_rounds": "自动补搜轮数（默认1）：信息不足时自动用追问词补搜；0=关闭（不足时返回提示）"
            }
        },
        {"name": "web_search", "desc": "搜索网页", "params": {"query": "必填", "num_results": "可选(默认8)"}},
        {"name": "fetch_webpage", "desc": "获取网页正文", "params": {"url": "必填", "max_chars": "可选(默认5000)"}},
        {"name": "ai_summarize", "desc": "AI摘要分析（需先有搜索内容）", "params": {"search_context": "必填", "purpose": "必填", "thinking_level": "可选(normal/deep)"}},
        {"name": "set_ai_config", "desc": "临时修改AI配置", "params": {"api_key": "可选", "api_url": "可选", "model": "可选", "temperature": "可选"}},
        {"name": "test_api", "desc": "测试API连通性", "params": {}},
        {"name": "get_tutorial", "desc": "获取本教程", "params": {}}
    ],
    "search_and_summarize_behavior": {
        "数据充分": "无论是否开启自动补搜，正常返回结果并附上来源链接",
        "数据不足+开启自动补搜": "自动用AI建议的追问词补充搜索并修订，最终只返回结果与来源链接；完整思考过程记录在程序目录 logs/申请搜索内容和数据_xxx/ 文件夹",
        "数据不足+关闭自动补搜": "返回提示：本轮搜索无有效数据，需要进一步搜索，请打开自动补搜（max_refine_rounds>0）或更换关键词后重试"
    },
    "workflow": [
        "推荐：search_and_summarize(query='搜索词', purpose='总结目的') 一步完成",
        "进阶：search_and_summarize(..., thinking_level='deep', fidelity=4, max_refine_rounds=2) 深度调研",
        "诊断：test_api → set_ai_config(如有需要) → 正常使用"
    ]
}


# ========== MCP 协议 ==========
class MCPProtocol:
    def __init__(self, tools: Dict[str, callable]):
        self.tools = tools

    def _send(self, message: dict):
        message = _clean_surrogates_deep(message)
        try:
            line = json.dumps(message, ensure_ascii=False, default=str)
            line = _clean_surrogates(line)
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
            return
        except Exception:
            pass
        try:
            line = json.dumps(message, ensure_ascii=True, default=str)
            line = _clean_surrogates(line)
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
            return
        except Exception:
            pass
        try:
            fallback = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {"content": [{"type": "text", "text": str(message.get("result", {}))}]}
            }
            sys.stdout.write(json.dumps(fallback, ensure_ascii=True) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"[MCP FATAL] 无法输出: {e}\n")
            sys.stderr.flush()

    def _send_response(self, req_id, result=None, error=None):
        msg = {"jsonrpc": "2.0", "id": req_id}
        if error:
            msg["error"] = error
        else:
            msg["result"] = result
        self._send(msg)

    def _get_tool_definitions(self) -> List[dict]:
        tools_list = []
        for name, func in self.tools.items():
            meta = getattr(func, "__mcp_meta__", {})
            tools_list.append({
                "name": name,
                "description": meta.get("description", ""),
                "inputSchema": meta.get("input_schema", {"type": "object", "properties": {}})
            })
        return tools_list

    def handle_message(self, message: dict):
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {}) or {}
        if msg_id is None:
            return
        try:
            if method == "initialize":
                self._send_response(msg_id, {
                    "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": MCP_SERVER_NAME, "version": MCP_SERVER_VERSION}
                })
            elif method == "tools/list":
                self._send_response(msg_id, {"tools": self._get_tool_definitions()})
            elif method == "tools/call":
                name = params.get("name", "")
                args = params.get("arguments", {}) or {}
                args = _clean_surrogates_deep(args)
                if name not in self.tools:
                    self._send_response(msg_id, error={"code": -32602, "message": f"未知工具: {name}"})
                    return
                result = self.tools[name](**args)
                if isinstance(result, str):
                    result = _clean_surrogates(result)
                self._send_response(msg_id, {"content": [{"type": "text", "text": result}]})
            elif method == "ping":
                self._send_response(msg_id, {})
            else:
                self._send_response(msg_id, error={"code": -32601, "message": f"未知方法: {method}"})
        except Exception as e:
            err_msg = _clean_surrogates(str(e))
            self._send_response(msg_id, error={
                "code": -32603,
                "message": err_msg,
                "data": _clean_surrogates(traceback.format_exc())
            })

    def run(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                self.handle_message(json.loads(line))
            except (json.JSONDecodeError, EOFError):
                break
            except Exception as e:
                sys.stderr.write(f"[MCP] Error: {_clean_surrogates(str(e))}\n")
                sys.stderr.flush()
                break


def mcp_tool(name=None, description="", input_schema=None):
    def decorator(func):
        func.__mcp_meta__ = {
            "name": name or func.__name__,
            "description": description,
            "input_schema": input_schema or {"type": "object", "properties": {}}
        }
        return func
    return decorator


# ========== Bing 搜索 ==========
class BingSearchEngine:
    SEARCH_URL = "https://www.bing.com/search"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }

    @classmethod
    def search(cls, query: str, num_results: int = 8) -> List[Dict[str, str]]:
        query = _clean_surrogates(query)
        try:
            resp = requests.get(
                cls.SEARCH_URL,
                params={"q": query, "count": min(num_results * 2, 30)},
                headers=cls.HEADERS,
                timeout=SEARCH_TIMEOUT
            )
            resp.raise_for_status()
        except Exception as e:
            return [{"title": f"搜索请求失败: {_clean_surrogates(str(e))}", "url": "", "snippet": ""}]

        results = []
        for block in re.findall(
            r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>(.*?)</li>',
            resp.text, re.DOTALL | re.IGNORECASE
        )[:num_results]:
            try:
                h2 = re.search(
                    r'<h2[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                    block, re.DOTALL | re.IGNORECASE
                )
                if h2 and h2.group(1).startswith("http"):
                    url = h2.group(1)
                    title = re.sub(r'<[^>]+>', '', h2.group(2)).strip()
                    snippet = ""
                    cap = re.search(
                        r'<div class="b_caption">(.*?)</div>',
                        block, re.DOTALL | re.IGNORECASE
                    )
                    if cap:
                        p = re.search(
                            r'<p[^>]*>(.*?)</p>',
                            cap.group(1), re.DOTALL | re.IGNORECASE
                        )
                        if p:
                            snippet = re.sub(r'<[^>]+>', '', p.group(1)).strip()
                    results.append({
                        "title": _clean_surrogates(html.unescape(title)),
                        "url": url,
                        "snippet": _clean_surrogates(html.unescape(snippet))
                    })
            except:
                continue
        return results

    @classmethod
    def fetch_page_text(cls, url: str, max_chars: int = 5000) -> str:
        try:
            resp = requests.get(url, headers=cls.HEADERS, timeout=SEARCH_TIMEOUT)
            resp.raise_for_status()
            text = re.sub(
                r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>',
                '', resp.text, flags=re.DOTALL | re.IGNORECASE
            )
            text = re.sub(r'<[^>]+>', ' ', text)
            return _clean_surrogates(html.unescape(re.sub(r'\s+', ' ', text).strip()))[:max_chars]
        except Exception as e:
            return f"[获取失败: {_clean_surrogates(str(e))}]"


# ========== AI 客户端（支持温度） ==========
class AIAPIClient:
    @staticmethod
    def chat_completion(api_key, api_url, model, messages,
                        temperature=None, max_tokens=2000):
        if temperature is None:
            temperature = _ai_config.get("temperature", AI_TEMPERATURE)
        resp = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=AI_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
            if "text" in choice:
                return choice["text"]
        raise ValueError(f"API响应异常: {str(data)[:300]}")


# ========== 日志记录函数（一次调用 = 一个文件夹，记录完整思考过程） ==========

def _make_log_folder():
    """创建本次调用的日志文件夹 logs/申请搜索内容和数据_xxx/，返回路径。
    无论成功失败都向 stderr 打印，方便测试程序与用户确认。"""
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isdir(base):
            base = os.getcwd()
        # ⚠️ Windows 的 time.strftime 不支持 %f（微秒），必须用 datetime
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]   # 毫秒级唯一时间戳
        folder = os.path.join(base, "logs", f"申请搜索内容和数据_{ts}")
        os.makedirs(folder, exist_ok=True)
        try:
            sys.stderr.write(f"[日志] 本次调用日志目录: {folder}\n")
            sys.stderr.flush()
        except Exception:
            pass
        return folder
    except Exception as e:
        try:
            sys.stderr.write(f"[日志] ❌ 创建日志目录失败: {_clean_surrogates(str(e))}\n")
            sys.stderr.flush()
        except Exception:
            pass
        return None



def _write_log(folder, filename, data):
    """写一条日志记录到文件夹（失败时向 stderr 报告，不影响主流程）"""
    if not folder:
        try:
            sys.stderr.write(f"[日志] ⚠️ 日志文件夹为空，跳过写入 {filename}\n")
            sys.stderr.flush()
        except Exception:
            pass
        return
    try:
        path = os.path.join(folder, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_clean_surrogates_deep(data), f, ensure_ascii=False, indent=2)
    except Exception as e:
        try:
            sys.stderr.write(f"[日志] ⚠️ 写入 {filename} 失败: {_clean_surrogates(str(e))}\n")
            sys.stderr.flush()
        except Exception:
            pass


# ========== MCP 工具函数 ==========

@mcp_tool(
    name="web_search",
    description="【搜索工具】使用Bing搜索引擎搜索网页。传入query(搜索词)和可选的num_results(结果数量，默认8)。返回JSON包含title/url/snippet。已修复中文编码问题。",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词，如'今天天气怎么样'"},
            "num_results": {"type": "integer", "description": "返回结果数量，默认8", "default": 8}
        },
        "required": ["query"]
    }
)
def web_search(query: str, num_results: int = 8) -> str:
    results = BingSearchEngine.search(query, num_results)
    output = {
        "query": query,
        "result_count": len(results),
        "results": [{"index": i + 1, **r} for i, r in enumerate(results)]
    }
    return _json_safe(output)


@mcp_tool(
    name="fetch_webpage",
    description="【抓取工具】获取网页正文文本。传入url(网页链接)和可选的max_chars(最大字符数，默认5000)。返回JSON包含url/content_length/content。",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "要获取的网页URL"},
            "max_chars": {"type": "integer", "description": "最大字符数，默认5000", "default": 5000}
        },
        "required": ["url"]
    }
)
def fetch_webpage(url: str, max_chars: int = 5000) -> str:
    text = BingSearchEngine.fetch_page_text(url, max_chars)
    return _json_safe({"url": url, "content_length": len(text), "content": text})


@mcp_tool(
    name="ai_summarize",
    description="【AI摘要工具】调用AI对已有内容进行结构化JSON摘要分析。传入search_context(已有内容)、purpose(总结目的)和可选的thinking_level(思考深度：normal=标准，deep=深度分析)。",
    input_schema={
        "type": "object",
        "properties": {
            "search_context": {"type": "string", "description": "已有的搜索内容"},
            "purpose": {"type": "string", "description": "总结目的，如'我想了解经济形势'"},
            "thinking_level": {"type": "string", "description": "思考深度（可选）：normal=标准（快）；deep=深度分析（更全面，较慢）", "default": "normal"},
            "api_key": {"type": "string", "description": "API密钥（可选）"},
            "api_url": {"type": "string", "description": "API端点URL（可选）"},
            "model": {"type": "string", "description": "模型名称（可选）"}
        },
        "required": ["search_context", "purpose"]
    }
)
def ai_summarize(search_context: str, purpose: str, thinking_level: str = "normal",
                 api_key=None, api_url=None, model=None) -> str:
    key = api_key if api_key is not None else _ai_config.get("api_key", "")
    url = api_url if api_url is not None else _ai_config.get("api_url", "")
    mdl = model if model is not None else _ai_config.get("model", "")
    key = key or ""
    url = url or ""
    mdl = mdl or ""

    if not key:
        return _json_safe({
            "status": "not_configured",
            "message": "⚠️ 未配置API密钥",
            "hint": "请打开 mcp_websearch_server.py，在开头的 YOUR_API_KEY 变量中填入你的密钥，保存后重启"
        })

    depth_part = ""
    if thinking_level == "deep":
        depth_part = "\n【深度思考模式】请多角度审视问题、给出完整逻辑链、对矛盾信息细致评估，analysis部分需更充实完整（可500字以上）。"

    system_prompt = """你是一个专业AI信息分析助手。请严格按照以下JSON格式输出（不要markdown标记）：
{
    "summary": "整体摘要（2-3句话）",
    "key_points": [{"point": "关键点标题", "detail": "详细说明"}],
    "analysis": "根据搜索目的给出的分析判断",
    "sources": ["来源1", "来源2"],
    "limitations": "信息局限性说明",
    "follow_up_queries": ["进一步搜索的问题"]
}
【数据真实性铁律】
1. 所有数据、数字、日期、人名、机构名必须来自用户提供的内容，禁止编造。
2. 若内容中未明确给出某数据，必须标注"材料中未提供"，严禁估算或猜测。
3. 来源必须来自内容中出现的真实信息，禁止编造来源。
4. 保留关键数字、日期、专有名词，不得遗漏。""" + depth_part

    try:
        text = AIAPIClient.chat_completion(key, url, mdl, [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"## 搜索目的\n{purpose}\n\n## 搜索到的内容\n{search_context}"}
        ])
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if m:
            try:
                json.loads(m.group())
                return m.group()
            except:
                pass
        return _json_safe({"warning": "AI返回非标准JSON", "raw": text[:500]})
    except requests.exceptions.Timeout:
        return _json_safe({
            "error": True,
            "message": f"AI请求超时（{AI_TIMEOUT}秒）",
            "hint": "请运行 test_api 诊断网络和密钥问题"
        })
    except requests.exceptions.HTTPError as e:
        return _json_safe({
            "error": True,
            "message": f"HTTP错误: {_clean_surrogates(str(e))}",
            "hint": f"HTTP {e.response.status_code}: {'密钥无效' if e.response.status_code == 401 else '请检查API地址'}"
        })
    except Exception as e:
        return _json_safe({
            "error": True,
            "message": f"AI调用失败: {_clean_surrogates(str(e))}",
            "hint": "运行 test_api 诊断问题"
        })


@mcp_tool(
    name="search_and_summarize",
    description="【✅ 一键搜索+总结（推荐使用）】自动执行：Bing搜索 → 拼接结果 → AI智能总结。支持：①智能转总结开关 ②思考深度(normal/deep) ③数据保真度(1~5) ④自动补搜(max_refine_rounds)。只返回最终结果与来源链接；数据不足且未开补搜时返回提示。开补搜时完整思考过程记录在logs文件夹。",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词，如'2024年中国GDP'"},
            "purpose": {"type": "string", "description": "总结目的，如'我想了解经济形势'"},
            "num_results": {"type": "integer", "description": "搜索结果数量，默认5，可1~10灵活调整", "default": 5},
            "smart_summarize": {"type": "boolean", "description": "智能转总结开关（可选）：True=超阈值才总结；False=总是总结；不填=用默认常量", "default": None},
            "summarize_threshold": {"type": "integer", "description": "触发总结的字数阈值（可选），不填用默认常量", "default": None},
            "thinking_level": {"type": "string", "description": "思考深度（可选）：normal=标准（快）；deep=深度思考（更全面，较慢）", "default": None},
            "fidelity": {"type": "integer", "description": "数据保真度（可选，1~5）：1宽松概括；3标准（保留关键数字日期）；5逐字保真", "default": None},
            "max_refine_rounds": {"type": "integer", "description": "自动补搜轮数（可选）：信息不足时自动用追问词补搜；0=关闭（不足时返回提示）；不填=用默认常量", "default": None}
        },
        "required": ["query", "purpose"]
    }
)
def search_and_summarize(query: str, purpose: str, num_results: int = 5,
                         smart_summarize: bool = None, summarize_threshold: int = None,
                         thinking_level: str = None, fidelity: int = None,
                         max_refine_rounds: int = None) -> str:
    """一键：自动搜索 + 智能总结（智能转总结 + 思考深度 + 数据保真 + 自动补搜 + 完整日志）"""

    # ---- 解析默认参数 ----
    if smart_summarize is None:
        smart_summarize = AUTO_SUMMARIZE_DEFAULT
    threshold = summarize_threshold if summarize_threshold is not None else AUTO_SUMMARIZE_THRESHOLD
    if thinking_level is None:
        thinking_level = THINKING_LEVEL_DEFAULT
    if fidelity is None:
        fidelity = FIDELITY_DEFAULT
    if max_refine_rounds is None:
        max_refine_rounds = MAX_REFINE_ROUNDS_DEFAULT

    # ---- 本次调用的日志文件夹（仅开启补搜时创建） ----
    log_folder = None
    if max_refine_rounds > 0:
        log_folder = _make_log_folder()
        _write_log(log_folder, "00_调用参数.json", {
            "时间": time.strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "purpose": purpose,
            "num_results": num_results,
            "smart_summarize": smart_summarize,
            "summarize_threshold": threshold,
            "thinking_level": thinking_level,
            "fidelity": fidelity,
            "max_refine_rounds": max_refine_rounds
        })

    # ---- 动态构建提示词（深度思考 + 数据保真 + 防编造铁律） ----
    def _build_prompt():
        fidelity_rules = {
            1: "允许宽松概括，但不得编造数据，保留结论即可。",
            2: "保留主要数字与结论，次要细节可省略。",
            3: "标准保真：关键数字、日期、专有名词必须保留，禁止'大约''很多'等模糊表述。",
            4: "严格保真：所有数字、百分比、日期、人名、机构名必须与原文一致，不得遗漏或改写。",
            5: "逐字保真：关键数据段落需原文摘录。",
        }
        fr = fidelity_rules.get(fidelity, fidelity_rules[3])
        depth_part = ""
        if thinking_level == "deep":
            depth_part = "\n【深度思考模式】请多角度审视问题、给出完整逻辑链、对矛盾信息细致评估，analysis部分需更充实完整（可500字以上）。"

        return (
            "你是一个严谨的专业信息分析助手。请基于下方搜索材料回答，严格输出JSON（不要markdown标记，不要额外说明）：\n"
            "{\n"
            '  "summary": "整体摘要（2-4句话，涵盖最重要数据点）",\n'
            '  "key_points": [{"point": "要点标题", "detail": "说明（遵守保真要求）", "source": "对应来源链接", "confidence": "高/中/低"}],\n'
            '  "data_facts": [{"fact": "具体数据", "source": "来源链接"}],\n'
            '  "analysis": "分析判断",\n'
            '  "sources": ["全部有用来源链接"],\n'
            '  "information_gaps": "信息不足时说明缺口；充分则填\'信息充分\'",\n'
            '  "follow_up_queries": ["信息不足时给出1-3条补搜关键词（这是申请补充搜索的命令）；充分则留空[]"]\n'
            "}\n"
            f"【数据保真等级 {fidelity}/5】{fr}\n"
            "【数据真实性铁律】\n"
            "1. 所有数据、数字、日期、人名、机构名必须逐字来自搜索材料原文，禁止编造、估算或凭常识推断。\n"
            "2. 若材料中未明确给出某数据，必须填写'材料中未提供'，宁可数据缺失，不可数据错误。\n"
            "3. 来源链接必须来自材料中出现的真实网址，禁止编造来源。\n"
            "4. 多来源数据矛盾时，在 information_gaps 中并列说明，不得自行取其一。\n"
            "5. 若材料不足以回答用户目的，务必在 information_gaps 说明缺什么，并在 follow_up_queries 给出具体补搜关键词。\n"
            "6. 若材料已充分，follow_up_queries 必须返回空数组 []，information_gaps 填'信息充分'。\n"
            "7. sources 字段收集所有用到的来源链接，用于附在回复最后。\n"
            + depth_part
        )

    # ---- 第一轮搜索 ----
    results = BingSearchEngine.search(query, num_results)
    if not results:
        _write_log(log_folder, "99_结果_搜索无结果.json", {"错误": "搜索无结果", "query": query})
        return _json_safe({"error": True, "message": "搜索无结果，请更换关键词"})

    lines = [f"搜索词：{query}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] 标题：{r['title']}\n链接：{r['url']}\n摘要：{r['snippet']}\n")
    search_context = "\n".join(lines)
    content_len = len(search_context)

    # ---- 智能转总结开关 ----
    if smart_summarize and content_len < threshold:
        _write_log(log_folder, "99_结果_未触发总结.json", {
            "原因": f"搜索内容{content_len}字 < 阈值{threshold}字",
            "query": query,
            "result_count": len(results),
            "results": results
        })
        return _json_safe({
            "smart_summarize": True, "auto_summarized": False,
            "content_length": content_len, "threshold": threshold,
            "message": f"搜索内容共{content_len}字，未达到自动总结阈值{threshold}字，未触发AI总结（如需强制总结请设smart_summarize=False）",
            "query": query, "result_count": len(results),
            "results": [{"index": i + 1, **r} for i, r in enumerate(results)]
        })

    # ---- 调用 AI（含自动补搜循环） ----
    key = _ai_config.get("api_key", "") or ""
    url = _ai_config.get("api_url", "") or ""
    mdl = _ai_config.get("model", "") or ""
    if not key:
        _write_log(log_folder, "99_结果_未配置密钥.json", {"错误": "未配置API密钥"})
        return _json_safe({"error": True, "message": "未配置API密钥，请检查代码开头YOUR_API_KEY", "search_results": results})

    current_query = query
    round_no = 0
    final_parsed = None
    refine_log = []
    current_results = results

    while True:
        system_prompt = _build_prompt()
        round_hint = ""
        if round_no > 0:
            round_hint = f"\n\n【提示】这是第{round_no}轮补充搜索后的修订。请综合全部材料修订结论，若已充分则 follow_up_queries 返回空数组。"

        # 记录本轮搜索
        if log_folder:
            _write_log(log_folder, f"round_{round_no}_搜索.json", {
                "轮次": round_no,
                "搜索词": current_query,
                "时间": time.strftime("%Y-%m-%d %H:%M:%S"),
                "搜索结果": [
                    {"标题": r.get("title"), "网址": r.get("url"), "摘要": r.get("snippet")}
                    for r in current_results
                ]
            })

        try:
            text = AIAPIClient.chat_completion(key, url, mdl, [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"## 搜索目的\n{purpose}\n\n## 搜索材料\n{search_context}{round_hint}"}
            ])
        except requests.exceptions.Timeout:
            _write_log(log_folder, f"round_{round_no}_AI超时.json", {"错误": f"AI请求超时（{AI_TIMEOUT}秒）"})
            return _json_safe({"error": True, "message": f"AI请求超时（{AI_TIMEOUT}秒）"})
        except Exception as e:
            _write_log(log_folder, f"round_{round_no}_AI失败.json", {"错误": _clean_surrogates(str(e))})
            return _json_safe({"error": True, "message": f"AI调用失败: {_clean_surrogates(str(e))}"})

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            _write_log(log_folder, f"round_{round_no}_AI非标准JSON.json", {"原始输出": text[:2000]})
            return _json_safe({"warning": "AI返回非标准JSON", "raw": cleaned[:800]})

        final_parsed = parsed
        fq = parsed.get("follow_up_queries") or []
        gaps = str(parsed.get("information_gaps", ""))

        # 记录 AI 完整思考输出与决策
        if log_folder:
            decision = ""
            if not fq or "信息充分" in gaps:
                decision = "数据充分，正常结束"
            elif round_no >= max_refine_rounds:
                decision = "数据不足但已达补搜上限，返回提示"
            else:
                decision = f"数据不足，申请补搜 → 用 '{fq[0] if fq else ''}' 继续搜索"
            _write_log(log_folder, f"round_{round_no}_AI思考与决策.json", {
                "轮次": round_no,
                "AI完整思考输出(原始返回)": text,
                "AI是否申请补搜": bool(fq),
                "AI提出的补搜关键词": fq,
                "AI判断的信息缺口": gaps,
                "本次决策": decision
            })

        # 情况A：数据充分 → 正常结束（无论补搜开关，都正常返回结果+来源链接）
        if not fq or "信息充分" in gaps:
            break

        # 情况B：数据不足且没有剩余补搜轮次 → 返回提示
        if round_no >= max_refine_rounds:
            final_parsed["status"] = "insufficient"
            final_parsed["message"] = "本轮搜索无有效数据，需要进一步搜索，请打开自动补搜（max_refine_rounds>0）或更换关键词后重试"
            break

        # 情况C：数据不足且有补搜轮次 → 自动用 AI 建议的追问词补搜
        current_query = fq[0] if fq else (query + " 详细资料")
        refine_log.append(current_query)
        new_results = BingSearchEngine.search(current_query, min(num_results, 5))
        if new_results:
            lines = [f"\n\n===== 补充搜索：{current_query} =====\n"]
            for i, r in enumerate(new_results, 1):
                lines.append(f"[{i}] 标题：{r['title']}\n链接：{r['url']}\n摘要：{r['snippet']}\n")
            search_context += "\n".join(lines)
            current_results = new_results
        round_no += 1

    # ---- 最终返回：只返回结果 + 来源链接 ----
    if final_parsed is None:
        _write_log(log_folder, "99_结果_无有效返回.json", {"错误": "AI未返回有效结果"})
        return _json_safe({"error": True, "message": "AI未返回有效结果"})

    # 确保 sources 链接齐全
    if not final_parsed.get("sources"):
        srcs = []
        for kp in final_parsed.get("key_points", []):
            if kp.get("source") and kp["source"] not in srcs:
                srcs.append(kp["source"])
        for df in final_parsed.get("data_facts", []):
            if df.get("source") and df["source"] not in srcs:
                srcs.append(df["source"])
        final_parsed["sources"] = srcs

    # 记录最终结果到日志
    if log_folder:
        _write_log(log_folder, "99_最终结果.json", {
            "最终结果": final_parsed,
            "总搜索轮次": round_no + 1,
            "补充搜索词记录": refine_log
        })

    return _json_safe(final_parsed)


@mcp_tool(
    name="set_ai_config",
    description="【配置工具】临时修改AI配置（仅本次会话有效，重启后仍使用代码开头的变量值）。所有参数均可选。",
    input_schema={
        "type": "object",
        "properties": {
            "api_key": {"type": "string", "description": "API密钥（可选）"},
            "api_url": {"type": "string", "description": "API端点URL（可选）"},
            "model": {"type": "string", "description": "模型名称（可选）"},
            "temperature": {"type": "number", "description": "AI温度（可选，0~1）：越低越客观稳定，防幻觉", "default": None}
        }
    }
)
def set_ai_config(api_key=None, api_url=None, model=None, temperature=None) -> str:
    global _ai_config
    if api_key is not None:
        _ai_config["api_key"] = api_key
    if api_url is not None:
        _ai_config["api_url"] = api_url
    if model is not None:
        _ai_config["model"] = model
    if temperature is not None:
        _ai_config["temperature"] = temperature

    raw_key = _ai_config.get("api_key") or ""
    if raw_key:
        masked = raw_key[:8] + "..." + raw_key[-4:] if len(raw_key) > 12 else "***"
    else:
        masked = "(空)"

    return _json_safe({
        "success": True,
        "message": "AI配置已更新（仅本次会话有效，重启后仍读取代码开头的变量）",
        "current_config": {
            "api_key": masked,
            "api_url": _ai_config.get("api_url", ""),
            "model": _ai_config.get("model", ""),
            "temperature": _ai_config.get("temperature", AI_TEMPERATURE)
        }
    })


@mcp_tool(
    name="get_tutorial",
    description="【教程工具】获取本服务器完整使用教程（含最新版工具参数说明）。无需传任何参数。返回JSON格式的使用说明。",
    input_schema={"type": "object", "properties": {}}
)
def get_tutorial() -> str:
    return _json_safe(_TUTORIAL)


@mcp_tool(
    name="test_api",
    description="【诊断工具】测试当前AI API配置是否能连通。无需参数。返回连接测试结果，帮助你快速排查API密钥和网络问题。",
    input_schema={"type": "object", "properties": {}}
)
def test_api() -> str:
    key = _ai_config.get("api_key", "") or ""
    url = _ai_config.get("api_url", "") or ""
    model = _ai_config.get("model", "") or ""

    if not key:
        return _json_safe({
            "status": "error",
            "message": "❌ 未配置API密钥",
            "hint": "请打开 mcp_websearch_server.py，在开头的 YOUR_API_KEY 变量中填入你的密钥"
        })

    if not url:
        return _json_safe({
            "status": "error",
            "message": "❌ 未配置API地址",
            "hint": "请检查 YOUR_API_URL 是否正确"
        })

    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "返回ok"}], "max_tokens": 10},
            timeout=AI_TIMEOUT
        )
        if resp.status_code == 200:
            return _json_safe({
                "status": "ok",
                "message": "✅ API连接正常！密钥和地址都正确。",
                "api_url": url,
                "model": model
            })
        elif resp.status_code == 401:
            return _json_safe({
                "status": "error",
                "message": "❌ API密钥无效（HTTP 401）",
                "hint": "请检查 YOUR_API_KEY 是否正确，或去API平台检查密钥是否过期"
            })
        else:
            return _json_safe({
                "status": "error",
                "message": f"❌ HTTP {resp.status_code}: {resp.reason}",
                "url": url
            })
    except requests.exceptions.ConnectionError:
        return _json_safe({
            "status": "error",
            "message": "❌ 网络连接失败",
            "hint": "请检查 YOUR_API_URL 是否正确，或网络是否能访问该地址"
        })
    except requests.exceptions.Timeout:
        return _json_safe({
            "status": "error",
            "message": f"❌ 连接超时（{AI_TIMEOUT}秒）",
            "hint": "API地址可能无法访问，请检查网络"
        })
    except Exception as e:
        return _json_safe({
            "status": "error",
            "message": f"❌ 错误: {_clean_surrogates(str(e))}"
        })


def main():
    if YOUR_API_KEY and "在此填入" not in YOUR_API_KEY:
        sys.stderr.write(f"[信息] ✅ API密钥已配置（{YOUR_API_KEY[:8]}...），模型: {YOUR_MODEL}\n")
    else:
        sys.stderr.write("[信息] ⚠️ 未配置API密钥！请打开本文件，在开头的 YOUR_API_KEY 变量中填入你的密钥\n")
    sys.stderr.write(f"[信息] API地址: {YOUR_API_URL}\n")
    sys.stderr.write(f"[信息] 温度: {_ai_config.get('temperature', AI_TEMPERATURE)}（越低越客观）\n")
    sys.stderr.write("[信息] 配置直接写在代码中，无需 config.json\n")
    sys.stderr.flush()

    server = MCPProtocol({
        "web_search": web_search,
        "fetch_webpage": fetch_webpage,
        "ai_summarize": ai_summarize,
        "search_and_summarize": search_and_summarize,
        "set_ai_config": set_ai_config,
        "get_tutorial": get_tutorial,
        "test_api": test_api
    })
    try:
        server.run()
    except KeyboardInterrupt:
        sys.stderr.write("[MCP] 关闭\n")
        sys.stderr.flush()


if __name__ == "__main__":
    main()
