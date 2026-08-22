[English](README_CN) | 中文

# mcp-websearch-ai

> **项目说明**：本项目由我（lamsam2026）提出并主导，代码由 AI 辅助编写，我负责编译、调试、功能验证与最终审查。本人对代码质量、安全性及合规性承担全部责任。

> **AI 辅助声明**：本项目的核心代码由 AI 生成，并经过人工审查与修改。使用前请仔细阅读本声明及许可证条款。

> **运行环境说明**：本工具及其测试脚本仅在 **Windows 11** 系统上完成测试与调试。其他操作系统（如 macOS、Linux）未经过充分验证，可能存在兼容性问题，请使用者自行评估。

一个集成了 **网页搜索 + AI 智能总结** 的 MCP (Model Context Protocol) 服务器，支持在 MCP 客户端中通过对话直接调用搜索与 AI 分析能力。

**中文编码已全面修复**，支持本地 API 与云端 API，开箱即用。

---

## ✨ 功能特性

| 功能                 | 说明                                                           |
| :------------------- | :------------------------------------------------------------- |
| 🔍 **web_search**    | 使用 Bing 搜索引擎搜索网页（国内可直接访问，无需代理）         |
| 📄 **fetch_webpage** | 抓取指定网页正文，用于深度阅读                                 |
| 🤖 **ai_summarize**  | 对已有内容调用 AI 进行结构化 JSON 摘要分析                     |
| ⚡ **search_and_summarize** | **一键完成「搜索 → 拼接 → AI 总结」全流程（推荐使用）**，支持**智能转总结**开关 |
| ⚙️ **set_ai_config** | 临时修改 AI 配置（仅本次会话有效）                             |
| 🔧 **test_api**      | 测试 AI API 连通性，快速排查密钥/网络问题                      |
| 📖 **get_tutorial**  | 获取服务器完整使用教程                                         |

### 智能转总结

- 开启后，**搜索内容超过字数阈值才自动调用 AI 总结**；未超过则只返回搜索结果，省 token、速度快
- 阈值与开关可通过参数临时指定，也可用代码开头的默认常量控制

---

## 📦 环境要求

| 项目           | 要求                                                           |
| :------------- | :------------------------------------------------------------- |
| Python         | 3.9 及以上                                                     |
| 依赖库         | `requests`（仅此一个）                                         |
| AI 后端（二选一） | ① 云端 API（OpenAI 兼容格式）；② 本地 API（如 LM Studio 等） |

### 安装依赖

```bash
pip install requests
```

---

## ⚙️ 配置方法

打开 `mcp_websearch_server.py`，在文件开头找到配置区，按需填写：

**方式一：云端 API（以 DeepSeek 为例）**

```python
YOUR_API_KEY = "sk-你的真实密钥"
YOUR_API_URL = "https://api.deepseek.com/v1/chat/completions"
YOUR_MODEL   = "deepseek-chat"
```

**方式二：本地 API（以 LM Studio 为例，完全离线，无需真实密钥）**

```python
YOUR_API_KEY = "lm-studio"                                            # 占位符即可，本地服务不校验
YOUR_API_URL = "http://localhost:1234/v1/chat/completions"            # 本地地址
YOUR_MODEL   = "你的模型名"                                           # 如 qwen2.5-7b-instruct
```

**本地 API 通用启动步骤：**

1. 启动你的本地 API 服务（如 LM Studio 的「Start Server」）
2. 在浏览器中访问服务提供的模型列表地址，获取准确的模型名称
3. 将模型名称填入 `YOUR_MODEL`
4. 保存代码 → 重启 MCP 客户端 → 运行 `test_api` 验证

> 💡 云端与本地切换：修改代码开头的三个值 → 重启客户端即可。

---

> 🔐 **安全提醒**：请勿将包含真实 API 密钥的代码提交至公开仓库。建议使用环境变量或 `.env` 文件管理密钥，并将 `.env` 加入 `.gitignore`。若您坚持硬编码，请确保仅限本地使用，且每次提交前检查文件内容。

---

## ⏱️ 超时与智能转总结常量（文件开头）

```python
MCP_SERVER_NAME = "mcp-websearch-ai"
MCP_SERVER_VERSION = "1.0.0"
SEARCH_TIMEOUT = 15       # Bing搜索/网页抓取 超时（秒）
AI_TIMEOUT = 300          # AI 模型返回 超时（秒）——本地模型建议 300+

# 【智能转总结】配置
AUTO_SUMMARIZE_DEFAULT = True      # 默认开关：True=开启，False=关闭
AUTO_SUMMARIZE_THRESHOLD = 2000    # 触发自动总结的字数阈值
```

> ⚠️ **本地模型注意**：`AI_TIMEOUT` 默认 60 秒大概率超时，建议改为 300。若 `test_api` 也超时，把函数里写死的 `timeout=15` 改为 `timeout=AI_TIMEOUT`。

---

## 🚀 快速开始

**1. 注册 MCP 服务器（以 Claude Desktop 为例）**

编辑 `%APPDATA%\Claude\claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "websearch-ai": {
      "command": "python",
      "args": ["C:\\你的完整路径\\mcp_websearch_server.py"]
    }
  }
}
```

其他 MCP 客户端在各自设置界面填写启动命令与脚本路径即可。

**2. 重启客户端** → 完全退出并重新打开。

**3. 验证连通性** → 对话中输入 `test_api`，返回 `"status": "ok"` 即配置正确。

**4. 开始使用**

```
search_and_summarize(query="2024年中国GDP", purpose="了解中国经济形势", num_results=5)
```

---

## 📋 作者已测试兼容的客户端软件

以下 MCP 客户端经作者测试可正常调用本工具：

- Claude Desktop
- DeepSeek Harness
- LM Studio
- AnythingLLM
- Cursor

> **关于兼容性说明**：本工具严格遵循 **MCP (Model Context Protocol) 标准调用格式**，理论上兼容所有支持 MCP 协议的客户端软件。上述列表仅为作者实际测试通过的环境，**不代表仅限上述软件可用**。用户可自行尝试在其他 MCP 客户端中配置使用。

> **免责声明**：上述软件名称仅用于说明本工具的测试环境，**不含任何商业宣传目的**。软件列表仅供参考，不代表作者与上述软件方有任何合作关系，亦不构成对上述软件的任何推荐或背书。用户应自行评估并遵守各软件的使用条款。

---

## 🛠️ 工具详细说明

### 1️⃣ search_and_summarize（✅ 首选）

一键完成搜索 + AI 总结，返回完整 JSON 分析报告。

| 参数                   | 必填 | 说明                                                           |
| :--------------------- | :--- | :------------------------------------------------------------- |
| `query`                | ✅   | 搜索关键词                                                     |
| `purpose`              | ✅   | 总结目的                                                       |
| `num_results`          | ❌   | 搜索结果数量（默认 5）                                         |
| `smart_summarize`      | ❌   | 智能转总结开关：`True`=开启（超阈值才总结）；`False`=关闭（总是总结）；不填=用默认常量 |
| `summarize_threshold`  | ❌   | 触发总结的字数阈值；不填=用默认常量 `AUTO_SUMARIZE_THRESHOLD`  |

**智能转总结行为对照：**

| `SMART_SUMMARIZE`      | 内容 < 阈值       | 内容 ≥ 阈值       | 效果                |
| :--------------------- | :---------------- | :---------------- | :------------------ |
| `True`（或默认）       | 只返回搜索结果，不调 AI | 自动转 AI 总结   | 省 token、快        |
| `False`                | 总是总结          | 总是总结          | 恢复"必总结"行为    |
| 不填                   | 看默认常量（默认 `True`） | 同上              | 由代码开头控制      |

**示例：**

```python
# 不传阈值，用默认 2000
search_and_summarize(query="2025年人工智能趋势", purpose="了解AI产业动向")

# 自定义阈值 5000
search_and_summarize(query="人工智能趋势", purpose="深度调研", smart_summarize=True, summarize_threshold=5000)

# 关闭智能转总结（总是总结）
search_and_summarize(query="今天的新闻", purpose="了解热点", smart_summarize=False)
```

**返回格式：**

```json
{
  "summary": "整体摘要",
  "key_points": [{"point": "要点", "detail": "详情"}],
  "analysis": "深度分析",
  "sources": ["来源链接"],
  "limitations": "局限性说明",
  "follow_up_queries": ["追问问题"]
}
```

未触发总结时返回：`auto_summarized: false` + 完整搜索结果列表 + 说明信息。

---

### 2️⃣ web_search

仅执行搜索，返回原始结果列表（标题/链接/摘要）。

| 参数           | 必填 | 说明                     |
| :------------- | :--- | :----------------------- |
| `query`        | ✅   | 搜索关键词               |
| `num_results`  | ❌   | 结果数量（默认 8）       |

---

### 3️⃣ fetch_webpage

抓取指定网页正文。

| 参数           | 必填 | 说明                         |
| :------------- | :--- | :--------------------------- |
| `url`          | ✅   | 网页链接                     |
| `max_chars`    | ❌   | 最大字符数（默认 5000）      |

---

### 4️⃣ ai_summarize

对已有文本内容进行 AI 结构化摘要。

| 参数             | 必填 | 说明         |
| :--------------- | :--- | :----------- |
| `search_context` | ✅   | 已有内容     |
| `purpose`        | ✅   | 总结目的     |

---

### 5️⃣ set_ai_config

临时修改 AI 配置（重启后恢复为代码开头的值）。

| 参数       | 说明                 |
| :--------- | :------------------- |
| `api_key`  | API 密钥（可选）     |
| `api_url`  | API 地址（可选）     |
| `model`    | 模型名称（可选）     |

---

### 6️⃣ test_api

测试 API 连通性，无参数。返回密钥、地址、网络是否正常。

---

### 7️⃣ get_tutorial

获取服务器内置教程，无参数。

---

## 🧪 调试与自检脚本

本工具附带三个测试脚本，用于不同场景下的功能验证与调试。

> **测试环境说明**：本工具及其测试脚本仅在 **Windows 11** 系统上完成测试与调试。其他操作系统（如 macOS、Linux）未经过充分验证，可能存在兼容性问题，请使用者自行评估。

---

### 📁 脚本概览

| 脚本 | 用途 | 适用场景 |
| :--- | :--- | :--- |
| `text_client.py` | 功能完整性测试 | 验证所有工具是否正常工作 |
| `text_isolated.py` | 补搜功能隔离测试 | 验证 AI 自动补搜逻辑是否正确 |
| `text_all.py` | 一键全量测试 | 同时运行上述两个脚本并检查日志 |

---

### 1️⃣ text_client.py —— 功能完整性测试

**工作原理**：通过模拟 MCP 协议的工具调用请求，依次调用服务器提供的 7 项核心工具，并根据返回值判断各项功能是否正常。

**测试覆盖**：

| 序号 | 测试项 | 验证目标 |
| :--- | :--- | :--- |
| ① | `test_api` | API 连通性、密钥有效性 |
| ② | `web_search`（中文搜索） | UTF-8 编码是否正常、搜索是否可用 |
| ③ | `ai_summarize`（深度思考模式） | AI 能否返回结构化 JSON 摘要 |
| ④ | `search_and_summarize`（大阈值） | 智能转总结在内容不足时是否正确跳过 |
| ⑤ | `search_and_summarize`（小阈值） | 智能转总结在内容充足时是否正确触发 |
| ⑥ | `search_and_summarize`（新参数兼容） | `thinking_level`、`fidelity`、`max_refine_rounds` 参数是否正常生效 |
| ⑦ | `get_tutorial` | 教程内容是否包含新参数说明 |

**运行方式**：
```bash
python text_client.py
```

**输出说明**：
- 每项测试显示“通过 ✅ / 失败 ❌”
- 失败项会标注**缺少的关键字**与**实际返回内容**
- 最终汇总：`共 X 项，通过 Y 项，失败 Z 项`

---

### 2️⃣ text_isolated.py —— 补搜功能隔离测试

**工作原理**：通过**进程级网络隔离** + **本地模拟网站**，在完全可控的环境中验证 AI 的自动补搜逻辑是否正确。

**具体实现**：

1. **启动 15 个本地虚拟网站**（端口 8001～8015）：
   - **2 个有用网站**：包含国家统计局公布的 2024 年中国 GDP 精确数据（134.9084 万亿元、增速 5.0% 等）
   - **13 个干扰网站**：标题和正文大量提及“GDP”“经济”“增长”等关键词，但**不包含任何精确官方数据**

2. **进程级网络隔离**：
   - 使用 `monkey-patch` 技术拦截 `socket.create_connection`
   - 仅允许连接：**本地虚拟网站（127.0.0.1）** 和 **用户配置的 AI API 域名**
   - **其他所有外网连接被直接拒绝**，确保测试过程不依赖真实互联网
   - 该隔离仅影响当前进程，系统其他程序不受影响；进程退出后隔离自动失效

3. **替换搜索引擎**：
   - 将 `BingSearchEngine.search` 临时替换为“本地假搜索”
   - 假搜索仅在 15 个本地虚拟网站中匹配关键词，根据匹配度返回结果

4. **测试逻辑**：
   - **第 1 次搜索**：假搜索只返回 13 个干扰网站，不包含有用网站 → AI 找不到精确数据 → 自动申请补搜
   - **第 2 次搜索（补搜）**：AI 根据已获取内容，自动生成“GDP 134.9万亿 2024 国家统计局”等追问词 → 假搜索重新匹配 → 有用网站因匹配度极高被优先返回 → AI 获取到精确数据 → 生成最终摘要

5. **验证通过标准**：
   - 搜索调用次数 ≥ 2 次（证明触发了补搜）
   - 最终返回结果包含“134.9”或“1349084”（GDP 总量）
   - 最终返回结果包含“5.0”（GDP 增速）
   - 来源链接指向本地有用站点（端口 8001 或 8002）
   - 返回完整的 JSON 结构（含 `summary` 和 `key_points`）

**运行方式**：
```bash
python text_isolated.py
```

**输出说明**：
- 显示 15 个本地网站的启动状态
- 显示进程级隔离已生效（仅允许本地 + API 域名）
- 显示每次搜索的调用记录与命中情况
- 列出 5 项验证标准及其通过/失败状态
- 最终显示测试结论：全部通过 / 存在失败项

---

### 3️⃣ text_all.py —— 一键全量测试

**工作原理**：依次调用 `text_client.py` 和 `text_isolated.py`，并自动检查 `logs/` 目录中是否生成了完整的补搜日志。

**执行流程**：

1. 运行 `text_client.py`（7 项功能测试）
2. 运行 `text_isolated.py`（隔离补搜测试）
3. 检查 `logs/` 目录下的日志文件夹：
   - 若存在至少一个包含 `AI思考与决策` + `99_最终结果` 且内容非空的文件夹 → 日志检查通过
   - 若仅有“未触发总结”的文件夹（如 `00_调用参数.json` + `99_结果_未触发总结.json`），视为正常跳过，不判为失败

**运行方式**：
```bash
python text_all.py
```

**输出说明**：
- 显示两个子脚本的运行输出
- 显示日志检查结果（完整日志数量 / 非完整数量 / 空文件数）
- 最终汇总：功能测试、隔离测试、日志检查三项是否全部通过

---

### 📊 三个脚本的关系

```
┌─────────────────────────────────────────────┐
│              text_all.py                    │
│         （一键全量测试）                     │
│    ┌────────────────────────────────┐       │
│    │      text_client.py           │       │
│    │   （7 项功能测试，模拟调用）   │       │
│    └────────────────────────────────┘       │
│    ┌────────────────────────────────┐       │
│    │      text_isolated.py         │       │
│    │ （隔离补搜测试，本地虚拟网站）  │       │
│    └────────────────────────────────┘       │
│    ┌────────────────────────────────┐       │
│    │      检查 logs/ 目录           │       │
│    │  （验证完整补搜日志是否生成）   │       │
│    └────────────────────────────────┘       │
└─────────────────────────────────────────────┘
```
### 运行方式

```bash
python test_client.py
```

### 输出说明

- 每项测试结束后会记录通过/失败状态
- 失败项会单独标注，显示**缺失的关键字**与**实际返回内容**（便于定位问题）
- 全部测试完成后显示汇总：`共 X 项，通过 Y 项，失败 Z 项`
- 全部通过时退出码为 `0`，否则为 `1`

### 超时调整

脚本开头设有 `TIMEOUT = 300`（秒）：

- 本地模型（如 LM Studio）：建议保持 300，给足推理时间
- 云端 API：可酌情调整为 120

### 使用场景

| 场景                       | 建议                                                         |
| :------------------------- | :----------------------------------------------------------- |
| 首次配置 API               | 运行脚本快速验证密钥、地址、模型是否全部正确                 |
| 更换 API 服务商（云端↔本地） | 运行脚本确认新配置下各项功能仍正常                           |
| 环境迁移（换电脑/换系统）  | 运行脚本排查路径、编码、依赖等环境问题                       |
| 功能回归测试               | 修改代码后运行脚本，确保未破坏核心功能                       |

### 脚本与主程序的关系

`test_client.py` 独立于主程序运行，通过标准输入/输出与 MCP 服务器通信，不依赖任何外部测试框架，开箱即用。

---

## 📋 推荐工作流程

```
★ 日常查询（推荐）：
   search_and_summarize(query="搜索词", purpose="总结目的")

★ 深度调研：
   ① web_search(query="搜索词", num_results=8)
   ② fetch_webpage(url="权威链接")
   ③ ai_summarize(search_context=已获取内容, purpose="深度分析")

★ 故障排查：
   ① test_api → 确认 API 正常
   ② set_ai_config → 修正配置（如需要）
   ③ 重新执行
```

---

## 🤖 推荐系统提示词

在 MCP 客户端中可将以下提示词配置给 AI 助手，以规范其使用本工具的方式：

```
你是一个专业的联网信息检索与分析助手，通过 MCP 服务器「mcp-websearch-ai」接入实时互联网搜索和 AI 摘要能力。

【可用工具】
1. search_and_summarize（首选）：一键搜索 + AI总结。参数：query（必填）、purpose（必填）、num_results（可选默认5）、smart_summarize（可选）、summarize_threshold（可选）
2. web_search：仅搜索。参数：query（必填）、num_results（可选默认8）
3. fetch_webpage：抓取网页正文。参数：url（必填）、max_chars（可选默认5000）
4. ai_summarize：对已有文本做结构化JSON摘要。参数：search_context（必填）、purpose（必填）
5. set_ai_config：临时修改AI配置（api_key/api_url/model均可选）
6. test_api：测试API连通性，报错时先调用
7. get_tutorial：获取完整教程

【推荐工作流程】
- 首选：search_and_summarize(query="搜索词", purpose="总结目的") → 一步出分析报告
- 深度调研：web_search → fetch_webpage(权威链接) → ai_summarize
- 故障排查：test_api → set_ai_config → 重试

【输出规范】
1. 关键数据必须附来源（URL或权威媒体名称），优先用表格对比
2. 将JSON分析报告转为易读格式，保留summary/key_points/analysis/sources/follow_up_queries
3. 数据真实性优先：政府官网 > 主流媒体/学术数据库 > 知名行业报告 > 普通资讯网站
4. 涉及政策法规、统计数据、医疗健康等敏感信息，标注"以官方发布为准"

【注意事项】
- 中英文搜索均支持（Bing 全球版），但内部提示词为中文，请确保所使用的 API 模型具备较强的中文理解能力
- 搜索引擎为Bing（国内可访问，无需代理）
- AI后端需用户自行配置，失败先运行test_api诊断
- num_results建议3~8个，过多会稀释摘要质量
- 搜索结果为空或相关性低时，更换关键词重试
- 用户未明确要求时，优先用search_and_summarize

【工具调用格式】
search_and_summarize(query="2024年中国GDP", purpose="了解经济形势", num_results=5)
web_search(query="人工智能 2025 趋势", num_results=8)
fetch_webpage(url="https://www.stats.gov.cn/sj/zxfb/202502/t20250228_1958817.html")
ai_summarize(search_context="已获取的文本内容...", purpose="深度分析")
test_api
get_tutorial
```

---

## ⚠️ 法律合规提醒

- **Bing 搜索**：本工具通过模拟浏览器请求访问 Bing 公开网页，仅供**个人学习与研究**使用。若用于商业项目或大规模部署，建议改用 [Bing Web Search API](https://www.microsoft.com/en-us/bing/apis/bing-web-search-api) 等官方服务，以遵守其服务条款。
- **AI 生成内容**：本工具代码由 AI 辅助生成，作者已进行人工审查。使用者应自行评估代码的适用性与安全性。
- **许可证**：本工具采用 MIT 许可证，详见下方 [许可证](#-许可证) 章节。

---

## 📦 文件迁移 / 部署（新电脑）

核心文件：`mcp_websearch_server.py`（单文件运行，配置写在代码内）。

1. 拷贝 `mcp_websearch_server.py` 到新电脑
2. 新电脑安装 Python 3.9+ → `pip install requests`
3. 配置 MCP 客户端指向新路径
4. 完全重启客户端 → `test_api` 验证

> 💡 路径建议不含中文和空格（如 `C:\mcp\`），避免客户端解析问题。
> 💡 API 密钥是账户级，换电脑依然有效。
> ⚠️ 密钥明文在文件里，勿外传、勿传公开仓库。

---

## ❓ 常见问题（FAQ）

**Q1：中文乱码怎么办？**

服务器已强制 stdin/stdout/stderr 全部 UTF-8 编码。cmd 中看到乱码是终端默认 GBK 显示所致，MCP 客户端（按 UTF-8 解析）显示正常。

**Q2：test_api 超时/连接失败？**

- 云端：检查 `YOUR_API_URL` 是否正确
- 本地：确认本地 API 服务已启动，端口未被占用
- 超时太短：把 `AI_TIMEOUT` 调大（本地模型建议 300），`test_api` 里的 `timeout=15` 也改为 `timeout=AI_TIMEOUT`

**Q3：test_api 返回 401 密钥无效？**

- 检查 `YOUR_API_KEY` 是否完整；检查密钥是否过期（云端）
- 本地 API 服务通常不校验密钥，填任意占位符即可，但不能留空

**Q4：提示模型不存在？**

- 本地：用服务提供的模型列表接口查询准确模型名，填进 `YOUR_MODEL`
- 云端：确认 model 名称与所用服务商一致

**Q5：search_and_summarize 没触发总结？**

智能转总结默认开启，内容未达阈值时只返回搜索结果（这是正常行为）。想强制总结：设 `smart_summarize=False` 或调小 `summarize_threshold`。

**Q6：模型返回内容质量不佳？**

本工具内部提示词使用中文编写，请确保所使用的 API 模型具备较强的中文理解能力。若模型中文能力较弱，可能导致摘要质量下降。

---

## 📄 版本与更新说明

本工具按当前需求编写，**不承诺定期更新或版本迭代**。请勿对后续更新抱有过高期待。如无重大问题，将保持当前版本长期可用。

当前版本：**v1.0.0**

---

## 📄 许可证

本项目采用 **MIT 许可证**。

MIT 许可证是一种宽松的开源许可证，允许任何人：

- ✅ 免费使用、复制、修改、合并、出版、分发、再许可和/或出售本软件的副本
- ✅ 将本软件用于任何目的，包括商业用途
- ✅ 修改源代码并闭源使用

**唯一要求**：在所有副本或重要部分中，必须保留原始的版权声明和本许可声明。

**免责声明**：本软件按“现状”提供，不提供任何形式的明示或暗示担保，包括但不限于适销性、特定用途适用性和非侵权性的担保。在任何情况下，作者或版权持有人均不对任何索赔、损害或其他责任负责，无论是在合同、侵权或其他方面，因使用本软件或与本软件有关的行为产生的责任。

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

---

<!-- 
=====================================================================
【开发者注释】本 README 由 AI 辅助编写，经人工审查与修订。
若您发现任何问题，欢迎提交 Issue 或 Pull Request。
=====================================================================
-->