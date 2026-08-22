# -*- coding: utf-8 -*-
"""
MCP 服务器完整测试客户端（v3.2）
========================================
自动测试 7 项：
  ① test_api                 - API 连通性
  ② web_search               - 中文搜索（验证编码修复）
  ③ ai_summarize（深度思考） - AI 结构化摘要 + thinking_level 参数
  ④ search_and_summarize     - 智能转总结【未触发】（大阈值）
  ⑤ search_and_summarize     - 智能转总结【已触发】（小阈值）
  ⑥ search_and_summarize     - 新参数兼容（thinking_level + fidelity + 关补搜）
  ⑦ get_tutorial             - 教程已更新（含新参数说明）

v3.2：④⑤ 显式传 max_refine_rounds=0，功能测试不产生 logs 日志
      （logs 日志只由 text_isolated.py 补搜测试产生，便于检查）
"""
import subprocess, sys, json, os

# ========== 配置 ==========
SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_websearch_server.py")
TIMEOUT = 300

# 强制 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def call_tool(name, arguments, timeout=TIMEOUT):
    msg = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments}
    }
    proc = subprocess.Popen(
        [sys.executable, SERVER],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace"
    )
    try:
        stdout, stderr = proc.communicate(json.dumps(msg, ensure_ascii=False), timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        return "(调用超时)", stderr + "\n[脚本] 超过 %d 秒无响应，已终止" % timeout
    return stdout, stderr


def extract_text(out):
    raw = out
    try:
        resp = json.loads(out)
        raw = resp["result"]["content"][0]["text"]
    except Exception:
        pass
    try:
        parsed = json.loads(raw)
        return json.dumps(parsed, ensure_ascii=False)
    except Exception:
        return raw.replace('\\"', '"')


def run_one(name, arguments, check_keywords, display_name, desc=""):
    print("▶ [%s] %s ..." % (display_name, name))
    if desc:
        print("  📋 测试内容：%s" % desc)
    out, err = call_tool(name, arguments)
    text = extract_text(out)
    combined = text + "\n" + (err or "")
    missing = [k for k in check_keywords if k not in combined]
    passed = len(missing) == 0
    brief = combined.strip()[:150].replace("\n", " ")
    print("  %s" % brief)
    print()
    return {"name": name, "passed": passed, "detail": combined[:500],
            "missing": missing, "desc": desc}


def main():
    print("=" * 60)
    print("  MCP 服务器完整测试（共 7 项）")
    print("  服务器：%s" % SERVER)
    print("=" * 60)
    print()

    results = []

    # ① test_api
    results.append(run_one("test_api", {}, ['"status": "ok"'], "①",
        "验证 API 密钥与地址连通性，应返回 status=ok"))

    # ② web_search
    results.append(run_one("web_search",
        {"query": "今天天气怎么样", "num_results": 3},
        ['"title"', '"snippet"'], "②",
        "中文搜索验证：Bing 应返回 title/snippet 字段（验证 UTF-8 编码）"))

    # ③ ai_summarize（深度思考）
    results.append(run_one("ai_summarize",
        {
            "search_context": "2024年中国GDP总量134.9万亿元，同比增长5.0%。第一产业增长3.5%，第二产业增长5.3%，第三产业增长5.0%。",
            "purpose": "我想了解2024年中国经济形势",
            "thinking_level": "deep"
        },
        ['"summary"', '"key_points"'], "③",
        "AI 结构化摘要：对给定文本进行深度思考分析，应返回 summary/key_points"))

    # ④ 智能转总结【未触发】（max_refine_rounds=0 不产生日志）
    results.append(run_one("search_and_summarize",
        {
            "query": "2024年中国GDP", "purpose": "了解经济形势",
            "num_results": 3, "smart_summarize": True, "summarize_threshold": 999999,
            "max_refine_rounds": 0
        },
        ['"auto_summarized": false', '"results"'], "④",
        "智能转总结【未触发】：阈值设为999999，搜索内容(约100字)远低于阈值，"
        "应只返回搜索结果(auto_summarized=false)且不调用AI"))

    # ⑤ 智能转总结【已触发】（max_refine_rounds=0 不产生日志）
    results.append(run_one("search_and_summarize",
        {
            "query": "2024年中国GDP", "purpose": "了解经济形势",
            "num_results": 3, "smart_summarize": True, "summarize_threshold": 50,
            "max_refine_rounds": 0
        },
        ['"summary"'], "⑤",
        "智能转总结【已触发】：阈值设为50，搜索内容超过阈值，"
        "应自动调用AI总结并返回 summary 字段"))

    # ⑥ 新参数兼容（已传 max_refine_rounds=0）
    results.append(run_one("search_and_summarize",
        {
            "query": "2024年中国GDP", "purpose": "了解经济形势",
            "num_results": 3, "smart_summarize": True, "summarize_threshold": 50,
            "thinking_level": "deep", "fidelity": 4, "max_refine_rounds": 0
        },
        ['"summary"'], "⑥",
        "新参数兼容：深度思考(deep)+高保真(fidelity=4)+关闭补搜(max_refine_rounds=0)，"
        "应正常返回 summary"))

    # ⑦ get_tutorial
    results.append(run_one("get_tutorial",
        {},
        ['"search_and_summarize"', '"thinking_level"', '"max_refine_rounds"'], "⑦",
        "教程已更新：get_tutorial 应包含新参数 thinking_level/max_refine_rounds 说明"))

    # ========== 汇总 ==========
    print()
    print("=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    passed_cnt = 0
    failed_cnt = 0
    for r in results:
        if r["passed"]:
            passed_cnt += 1
            print("  ✅ [通过] %s" % r["name"])
        else:
            failed_cnt += 1
            print("  ❌ [失败] %s" % r["name"])
            print("      缺少关键字: %s" % ", ".join(r["missing"]))
            print("      返回内容: %s" % r["detail"][:200])
        if r["desc"]:
            print("      📋 %s" % r["desc"])
    print("=" * 60)
    print("  共 %d 项：✅ 通过 %d 项，❌ 失败 %d 项" % (len(results), passed_cnt, failed_cnt))
    if failed_cnt == 0:
        print("  🎉 全部测试通过！服务器完全可用！")
    else:
        print("  ⚠️  有 %d 项失败，请根据上方失败详情排查。" % failed_cnt)
    print("=" * 60)
    print()
    print("测试结束，退出。")
    sys.exit(0 if failed_cnt == 0 else 1)


if __name__ == "__main__":
    main()
