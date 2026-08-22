# -*- coding: utf-8 -*-
"""
================================================================
search_and_summarize 补搜功能 · 隔离网络集成测试（v1.0）
search_and_summarize Refinement Test - Isolated Network Integration (v1.0)
================================================================
设计：                          |  Design:
  1. 本地启动 15 个模拟网站     |  1. Start 15 local mock websites (2 useful + 13 high-noise)
  2. 替换为本地假搜索           |  2. Replace BingSearchEngine.search with local fake search
  3. ★ 进程级网络隔离           |  3. ★ Process-level network isolation
  4. 调用 search_and_summarize  |  4. Call search_and_summarize
  5. 无需管理员权限             |  5. No admin privileges needed
用法：                          |  Usage:
  python test_isolated.py      |  python test_isolated.py
"""
import sys, os, json, re, time, socket, atexit, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ========== 强制 UTF-8 输出 / Force UTF-8 output ==========
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# =================================================================
# 一、15 个模拟网站内容（写死，2 有用 + 13 高干扰）
# 1. 15 Mock Websites (2 useful + 13 high-noise)
# =================================================================
# 有用网站①：含真实官方精确数据 / Useful site 1: contains official precise data
SITE_GOOD_1 = {
    "title": "国家统计局发布2024年国民经济和社会发展统计公报",
    "content": """
2024年国民经济和社会发展统计公报
（国家统计局 2025年2月28日发布）

初步核算，全年国内生产总值1349084亿元，按不变价格计算，比上年增长5.0%。
分产业看，第一产业增加值91414亿元，增长3.5%；第二产业增加值492087亿元，增长5.3%；第三产业增加值765583亿元，增长5.0%。三次产业增加值占GDP比重分别为6.8%、36.5%、56.7%。

全年居民消费价格指数（CPI）比上年上涨0.2%，其中食品价格下降0.2%。工业生产者出厂价格指数（PPI）下降2.2%。

全年全国城镇调查失业率平均值为5.1%，年末全国城镇调查失业率为5.1%。

全年全国居民人均可支配收入41314元，比上年名义增长5.3%，扣除价格因素实际增长5.1%。按常住地分，城镇居民人均可支配收入54188元，增长4.6%；农村居民人均可支配收入23119元，增长6.6%。

全年货物进出口总额438468亿元，比上年增长5.0%。其中，出口254545亿元，增长7.1%；进口183923亿元，增长2.3%。进出口相抵，贸易顺差70622亿元。

年末全国人口140828万人，比上年末减少139万人。全年出生人口954万人，死亡人口1093万人。

全年全社会固定资产投资514374亿元，比上年增长3.2%。全年社会消费品零售总额487895亿元，比上年增长3.5%。

全年全国一般公共预算收入219702亿元，比上年增长1.3%。年末广义货币供应量(M2)余额313.53万亿元，比上年末增长7.3%。

年末国家外汇储备32024亿美元，比上年末增加1138亿美元。

全年规模以上工业增加值比上年增长5.8%。全年服务业增加值比上年增长5.0%。

粮食总产量70650万吨，比上年增加1109万吨，增长1.6%。

上述数据均来自国家统计局官方统计公报，为最终核实口径。
""".strip(),
}

# 有用网站②：政府网口径 / Useful site 2: government source
SITE_GOOD_2 = {
    "title": "2024年国民经济运行情况主要经济指标发布",
    "content": """
2024年国民经济运行情况
（国家统计局综合司发布）

一、国内生产总值
初步核算，2024年全年国内生产总值1349084亿元，按不变价格计算，比上年增长5.0%。其中，一季度同比增长5.3%，二季度增长4.7%，三季度增长4.6%，四季度增长5.4%。

二、三次产业
第一产业增加值91414亿元，比上年增长3.5%；第二产业增加值492087亿元，增长5.3%；第三产业增加值765583亿元，增长5.0%。

三、价格水平
全年居民消费价格（CPI）比上年上涨0.2%。其中，城市上涨0.2%，农村上涨0.3%。

四、就业
全年城镇调查失业率平均值为5.1%。12月份，全国城镇调查失业率为5.1%。

五、居民收入
全年全国居民人均可支配收入41314元，比上年名义增长5.3%，扣除价格因素实际增长5.1%。

六、对外贸易
全年货物进出口总额438468亿元，比上年增长5.0%。其中出口254545亿元，增长7.1%；进口183923亿元，增长2.3%。

七、固定资产投资
全年全国固定资产投资（不含农户）514374亿元，比上年增长3.2%。

八、社会消费品零售
全年社会消费品零售总额487895亿元，比上年增长3.5%。

以上数据为官方公布口径，可用于权威引用。
""".strip(),
}

# 13 个高干扰网站：大量使用 GDP、经济等词，但无精确数据
# 13 high-noise sites: lots of GDP/economy mentions but NO precise official data
SITES_NOISE = [
    # ...（原有 13 个干扰站内容保持不变，篇幅原因此处省略，你直接保留原来的即可）
]

# 汇总所有站点 / Aggregate all sites: 2 useful + 13 noise = 15
SITES = [{"id": i, "port": 8001 + i, "good": True, **SITE_GOOD_1} for i in [0]] + \
        [{"id": i, "port": 8001 + i, "good": True, **SITE_GOOD_2} for i in [1]] + \
        [{"id": i + 2, "port": 8003 + i, "good": False, **s} for i, s in enumerate(SITES_NOISE)]

GOOD_SITES = [s for s in SITES if s["good"]]
NOISE_SITES = [s for s in SITES if not s["good"]]

# =================================================================
# 二、本地网站服务器（15 个端口） / Local Web Server (15 ports)
# =================================================================
class SiteHandler(BaseHTTPRequestHandler):
    site = None
    def do_GET(self):
        s = self.site
        body = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>{s['title']}</title></head><body>
<h1>{s['title']}</h1>
<article>{s['content']}</article>
<footer>本页面为本地测试站点（端口{s['port']}）</footer>
</body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
    def log_message(self, *a):
        pass

def make_handler(site):
    return type("Handler_%d" % site["port"], (SiteHandler,), {"site": site})

def start_site_servers():
    """启动所有模拟网站服务器（守护线程） / Start all mock website servers in daemon threads."""
    servers = []
    for site in SITES:
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", site["port"]), make_handler(site))
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            servers.append(srv)
            site["url"] = f"http://127.0.0.1:{site['port']}/"
        except Exception as e:
            print(f"  ⚠️ 站点 {site['port']} 启动失败: {e}")
    return servers

def stop_site_servers(servers):
    """关闭所有模拟网站服务器 / Stop all mock website servers."""
    for srv in servers:
        try:
            srv.shutdown(); srv.server_close()
        except Exception:
            pass

# =================================================================
# 三、★ 进程级网络隔离 / Process-Level Network Isolation ★
# =================================================================
_API_DOMAIN = None
_API_IPS = set()
_ALLOWED_EXTRA = set()   # 可额外放行的域名/IP（如代理）/ Extra domains/IPs to whitelist

_orig_create_connection = socket.create_connection

def _is_allowed(host):
    """判断目标地址是否在白名单内 / Check if target host is in whitelist."""
    if host in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
        return True
    if _API_DOMAIN and host == _API_DOMAIN:
        return True
    if host in _API_IPS:
        return True
    if host in _ALLOWED_EXTRA:
        return True
    return False

def _patched_create_connection(address, *args, **kwargs):
    """拦截非白名单地址的 socket 连接 / Block non-whitelisted addresses."""
    host = address[0] if isinstance(address, tuple) else address
    if not _is_allowed(host):
        raise socket.error(
            f"[进程级隔离] 已阻止访问非白名单地址: {host}（仅允许本地网站127.0.0.1与AI API）"
        )
    return _orig_create_connection(address, *args, **kwargs)

def apply_socket_isolation(api_url):
    """
    启用进程内 socket 隔离
    Enable process-level socket isolation.
    """
    global _API_DOMAIN
    domain = re.sub(r"^https?://", "", api_url).split("/")[0].split(":")[0]
    _API_DOMAIN = domain
    try:
        for info in socket.getaddrinfo(domain, 443):
            ip = info[4][0]
            if ip not in _API_IPS:
                _API_IPS.add(ip)
    except Exception as e:
        print(f"  ⚠️ 解析 API 域名失败: {e}")
    socket.create_connection = _patched_create_connection
    print(f"  ✅ 进程级隔离已生效：仅允许本地网站 + API 域名 {domain}（IP: {sorted(_API_IPS) or '未知'}）")
    print(f"     其他所有外网连接将被拦截（仅影响当前进程）")

# =================================================================
# 四、本地假搜索（替换 BingSearchEngine.search）
# 4. Local Fake Search (replaces BingSearchEngine.search)
# =================================================================
search_call_log = []   # 记录每次搜索的 query 与命中 / Logs each search query and hits

def fake_search(query, num_results=8):
    """
    模拟 Bing 搜索：第1次只返回干扰站，补搜时有用站+100分必然命中
    Mock Bing search: round 1 returns noise only, refine rounds prioritize useful sites (+100 score).
    """
    query = query or ""
    search_call_log.append({"query": query, "time": time.strftime("%H:%M:%S")})
    is_refine = len(search_call_log) > 1   # 第2次及以后 = 补搜 / 2nd+ call = refine round

    # 细粒度分词 / Tokenize: Chinese words + English/numbers
    words = re.findall(r'[\u4e00-\u9fff]+|[A-Za-z0-9.]+', query)

    scored = []
    for site in SITES:
        score = 0
        if site["good"]:
            score += 100          # 有用站基础分 / Useful sites get high base score
        for w in words:
            if w and w in site["title"]:
                score += 10
            if w and w in site["content"]:
                score += 3
        scored.append((score, site))
    scored.sort(key=lambda x: -x[0])

    if not is_refine:
        # 第1次搜索：只返回干扰站 / Round 1: return only noise sites
        top = [item for item in scored if not item[1]["good"]][:num_results]
    else:
        # 补搜：有用站 +100 基础分，必然排最前 / Refine: useful sites with +100 score prioritized
        top = scored[:num_results]

    results = []
    for _, site in top:
        snippet = site["content"].replace("\n", " ").strip()[:150]
        results.append({"title": site["title"], "url": site["url"], "snippet": snippet})
        search_call_log[-1].setdefault("hits", []).append(site["title"])
    return results

# =================================================================
# 五、主测试流程 / Main Test Flow
# =================================================================
def main():
    print("=" * 66)
    print("  search_and_summarize 补搜功能 · 进程级隔离测试")
    print("=" * 66)
    print()

    # ---- 导入主程序 / Import main program ----
    print("▶ 导入主程序 mcp_websearch_server ...")
    import importlib.util
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(base_dir, "mcp_websearch_server.py")
    spec = importlib.util.spec_from_file_location("mcp_websearch_server", server_path)
    server_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_mod)
    # 恢复测试程序自身 stdio 编码 / Restore test program's own stdio encoding
    if hasattr(sys.stdout, "reconfigure"):
        try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass

    api_url = server_mod._ai_config.get("api_url", "")
    api_key = server_mod._ai_config.get("api_key", "")
    print(f"  API 地址: {api_url}")
    print(f"  API 密钥: {'已配置 (' + api_key[:6] + '...)' if api_key else '未配置'}")

    # ---- 启动 15 个本地网站 / Start 15 local mock websites ----
    print("\n▶ 启动 15 个本地模拟网站 ...")
    servers = start_site_servers()
    time.sleep(0.5)
    print(f"  已启动 {len(servers)} 个站点（端口 8001~8015）")
    print(f"  其中有用站点 {len(GOOD_SITES)} 个，干扰站点 {len(NOISE_SITES)} 个")

    # ---- 进程级网络隔离 / Apply process-level network isolation ----
    print("\n▶ 应用进程级网络隔离 ...")
    apply_socket_isolation(api_url)

    # 注册恢复 / Register cleanup (socket patch auto-resets on process exit)
    atexit.register(stop_site_servers, servers)

    try:
        # ---- 替换搜索为本地假搜索 / Replace search engine with local fake search ----
        server_mod.BingSearchEngine.search = staticmethod(fake_search)
        print("\n▶ 已替换 BingSearchEngine.search 为本地假搜索（仅匹配 15 个网站）")

        # ---- 调用 search_and_summarize ----
        print("\n▶ 调用 search_and_summarize ...")
        print("  query='2024年中国GDP是多少'  purpose='获取2024年中国GDP官方精确数据'")
        print("  num_results=2  smart_summarize=False  max_refine_rounds=2  fidelity=4")
        result_str = server_mod.search_and_summarize(
            query="2024年中国GDP是多少",
            purpose="获取2024年中国GDP官方精确数据",
            num_results=2,
            smart_summarize=False,
            max_refine_rounds=2,
            fidelity=4,
            thinking_level="normal",
        )

        try:
            result = json.loads(result_str)
        except Exception:
            result = {"raw": result_str[:800]}
            print("\n  ⚠️ 返回非 JSON：")
            print("  " + result_str[:500])

        # ---- 输出搜索调用日志 / Output search call log ----
        print("\n" + "-" * 66)
        print("📡 假搜索调用记录（验证是否触发补搜）")
        print("-" * 66)
        for i, log in enumerate(search_call_log, 1):
            hits = "、".join(log.get("hits", [])) or "(无命中)"
            print(f"  第{i}次搜索: {log['query']}")
            print(f"    命中: {hits[:100]}")

        # ---- 验证 / Verification ----
        print("\n" + "-" * 66)
        print("🔍 测试验证")
        print("-" * 66)
        all_text = json.dumps(result, ensure_ascii=False)
        flat = all_text.replace(",", "")   # 兼容 AI 输出的千分位逗号 / Handle thousand separators
        sources = result.get("sources", []) if isinstance(result, dict) else []
        if not sources:
            for kp in result.get("key_points", []):
                if kp.get("source"): sources.append(kp["source"])
            for df in result.get("data_facts", []):
                if df.get("source"): sources.append(df["source"])

        checks = {
            "触发自动补搜（搜索调用≥2次）": len(search_call_log) >= 2,
            "找到GDP总量（134.9万亿/1349084亿）": ("134.9" in flat or "1349084" in flat),
            "找到GDP增速（5.0%）": ("5.0" in flat),
            "来源包含本地有用站（8001/8002）": any(("8001" in s or "8002" in s) for s in sources),
            "返回完整JSON结构（summary/key_points）": ("summary" in all_text and "key_points" in all_text),
        }
        passed = 0
        for name, ok in checks.items():
            print(f"  {'✅' if ok else '❌'} {name}")
            passed += bool(ok)

        # ---- 输出最终结果摘要 / Output final result summary ----
        print("\n" + "-" * 66)
        print("📄 最终返回摘要")
        print("-" * 66)
        if isinstance(result, dict):
            print("  summary: " + str(result.get("summary", ""))[:150])
            print("  来源链接:")
            for s in sources:
                print(f"    · {s}")
            if result.get("status") == "insufficient":
                print("\n  ⚠️ 状态: insufficient（数据不足，未找到有用信息）")
                print("  " + str(result.get("message", "")))
        print("\n" + "=" * 66)
        print(f"  测试结论: {'🎉 全部通过' if passed == len(checks) and all(checks.values()) else '⚠️ 存在失败项'}")
        print(f"  通过 {passed}/{len(checks)} 项")
        print("=" * 66)

    except Exception as e:
        import traceback
        print("\n❌ 测试异常:")
        traceback.print_exc()
    finally:
        print("\n▶ 正在关闭本地站点服务器 ...")
        stop_site_servers(servers)
        print("▶ 进程级隔离随进程退出自动失效，系统无任何残留")
        print("▶ 测试结束")

if __name__ == "__main__":
    main()
