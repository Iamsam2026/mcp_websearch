# -*- coding: utf-8 -*-
"""
============================================================
MCP 全量总测试（v2.0）         |  MCP Full Test Suite (v2.0)
============================================================
流程：                          |  Workflow:
  1. 依次运行 text_client.py   |  1. Run text_client.py (7 functional tests, no logs)
     （7 项功能测试，不产生 logs）|  2. Run text_isolated.py (isolated refinement test, generates full logs)
  2. 运行 text_isolated.py     |  3. Check logs/ directory
     （隔离补搜测试，产生完整 logs）|  4. Output summary
  3. 检查 logs/ 目录
  4. 汇总输出

v2.0 修复：                     |  v2.0 Fixes:
  - 日志检查宽容化              |  - Log check relaxed
  - 自动识别 text_/test_ 前缀   |  - Auto-recognizes text_/test_ prefix

用法：                          |  Usage:
  python text_all.py            |  python text_all.py
"""
import subprocess, sys, os, glob, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_ROOT = os.path.join(BASE_DIR, "logs")

# 强制 UTF-8 输出 / Force UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def find_script(*names):
    """查找脚本文件（支持多个候选名称） / Find script by trying multiple possible names."""
    for n in names:
        p = os.path.join(BASE_DIR, n)
        if os.path.isfile(p):
            return p
    return None


def run_script(display_name, candidates, timeout=900):
    """运行脚本并捕获输出 / Run a script and capture its output."""
    path = find_script(*candidates)
    print("\n" + "=" * 66)
    print("▶ 运行 %s ..." % display_name)
    print("=" * 66)
    if not path:
        print("  ❌ 找不到脚本文件（尝试过: %s）" % ", ".join(candidates))
        return -2
    print("  路径：%s" % path)
    try:
        proc = subprocess.run(
            [sys.executable, path],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        print("  ❌ %s 超时（>%d秒）" % (display_name, timeout))
        return -1
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr and proc.stderr.strip():
        print("[stderr 尾部]\n" + proc.stderr.strip()[-1500:])
    return proc.returncode


def check_logs():
    """
    检查 logs 目录：宽容化判定
    Check logs directory with relaxed criteria.
    - 完整日志：含 AI思考与决策 + 99_最终结果 且非空 / Complete log: contains AI思考与决策 + 99_最终结果 with content
    - 跳过日志：仅 00 + 99_结果_未触发（正常跳过） / Skipped: only 00 + 99_结果_未触发 (normal skip)
    """
    print("\n" + "=" * 66)
    print("🔍 检查 logs 日志目录")
    print("=" * 66)

    if not os.path.isdir(LOG_ROOT):
        print("  ❌ logs 目录不存在！（程序目录下应有 logs/ 文件夹）")
        return False

    folders = sorted(glob.glob(os.path.join(LOG_ROOT, "申请搜索内容和数据_*")))
    if not folders:
        print("  ⚠️ logs 目录存在，但没有任何 '申请搜索内容和数据_*' 文件夹")
        print("  （说明 search_and_summarize 未被调用，或调用时 max_refine_rounds=0）")
        return False

    complete_count = 0      # 完整日志 / Complete logs
    skip_count = 0          # 未触发总结的日志（正常跳过）/ Not-triggered logs (normal skip)
    empty_file_count = 0    # 空文件数 / Empty files count
    print("  ✅ 找到 %d 个日志文件夹：" % len(folders))

    for f in folders:
        files = os.listdir(f)
        has_decision = any("AI思考与决策" in fn for fn in files)
        has_final = any("99_最终结果" in fn for fn in files)

        # 检查空文件 / Check for empty files
        for fn in files:
            fp = os.path.join(f, fn)
            try:
                if os.path.getsize(fp) == 0:
                    print("        ⚠️ %s 内容为空（0字节）" % fn)
                    empty_file_count += 1
            except Exception:
                pass

        if has_decision and has_final:
            complete_count += 1
            print("    · %s/  （%d 个文件）✅ 完整日志" % (os.path.basename(f), len(files)))
            # 展示 AI 思考决策 / Preview AI decision
            for fn in files:
                if "AI思考与决策" in fn:
                    fp = os.path.join(f, fn)
                    try:
                        with open(fp, "r", encoding="utf-8") as fh:
                            data = json.load(fh)
                        print("        📄 %s 预览:" % fn)
                        print("          轮次: %s" % data.get("轮次"))
                        print("          AI是否申请补搜: %s" % data.get("AI是否申请补搜"))
                        print("          补搜关键词: %s" % data.get("AI提出的补搜关键词"))
                        print("          决策: %s" % str(data.get("本次决策"))[:80])
                    except Exception:
                        pass
                    break
        else:
            skip_count += 1
            print("    · %s/  （%d 个文件）⏭️ 非完整日志（未触发总结/中间路径，正常跳过）"
                  % (os.path.basename(f), len(files)))
            for fn in files:
                print("        - %s" % fn)

    print("-" * 66)
    print("  统计：完整日志 %d 个，非完整(正常跳过) %d 个，空文件 %d 个" %
          (complete_count, skip_count, empty_file_count))

    # 判定：至少 1 个完整日志 + 无空文件 = 通过
    # Pass: at least 1 complete log + no empty files
    ok = (complete_count >= 1) and (empty_file_count == 0)
    if ok:
        print("  ✅ 日志检查通过：存在完整思考日志且内容非空")
    else:
        if complete_count == 0:
            print("  ❌ 未找到完整日志（需要至少 1 个含 AI思考与决策 + 99_最终结果 的文件夹）")
        if empty_file_count > 0:
            print("  ❌ 存在空文件，日志写入可能不完整")
    return ok


def main():
    print("=" * 66)
    print("  MCP 全量总测试（功能测试 + 隔离补搜测试 + 日志检查）")
    print("  目录：%s" % BASE_DIR)
    print("=" * 66)

    # 1. 功能测试 / Functional tests
    r1 = run_script("text_client.py（7项功能测试）", ["text_client.py", "test_client.py"])

    # 2. 隔离补搜测试 / Isolated refinement test
    r2 = run_script("text_isolated.py（隔离补搜测试）", ["text_isolated.py", "test_isolated.py"])

    # 3. 检查日志 / Check logs
    log_ok = check_logs()

    # 4. 汇总 / Summary
    print("\n" + "=" * 66)
    print("  汇总结果")
    print("=" * 66)
    print("  功能测试 (text_client)  : %s" % ("✅ 通过" if r1 == 0 else "❌ 失败（退出码 %s）" % r1))
    print("  隔离测试 (text_isolated): %s" % ("✅ 通过" if r2 == 0 else "❌ 失败（退出码 %s）" % r2))
    print("  logs 目录检查           : %s" % ("✅ 通过" if log_ok else "❌ 失败"))
    print("-" * 66)
    all_pass = (r1 == 0) and (r2 == 0) and log_ok
    if all_pass:
        print("  🎉 总体结果：全部通过！")
    else:
        print("  ⚠️ 总体结果：存在失败项，请根据上方详情排查。")
    print("=" * 66)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
