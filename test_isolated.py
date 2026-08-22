# -*- coding: utf-8 -*-
"""
================================================================
search_and_summarize 补搜功能 · 隔离网络集成测试（修复版 v2.0）
================================================================
设计：
  1. 本地启动 15 个模拟网站（2 个有用 + 13 个高干扰，内容写死）
  2. 将 BingSearchEngine.search 替换为「本地假搜索」（仅从 15 个网站匹配）
  3. ★ 进程级网络隔离：monkey-patch socket.create_connection
     只允许连接：本地网站(127.0.0.1) + AI API 域名
     其他一切外网连接直接拒绝 —— 只锁当前进程，不影响系统其他程序
  4. 调用 search_and_summarize(query=..., num_results=2, max_refine_rounds=2)
     验证：首次搜索返回干扰信息 → AI 判断数据不足 → 自动补搜 → 找到有用数据
  5. 无需管理员权限；进程退出隔离自动失效，零系统残留

v2.0 修复：
  ✓ fake_search 改为：第1次只返回干扰站（制造"信息不足"），补搜时有用站+100分必然命中
  ✓ 验证逻辑兼容 AI 输出的千分位逗号（1,349,084 → 1349084）
  ✓ 干扰站删减为 13 个（2有用+13干扰=15个站点）

用法：
  python test_isolated.py
"""
import sys, os, json, re, time, socket, atexit, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ========== 强制 UTF-8 输出 ==========
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# =================================================================
# 一、15 个模拟网站内容（写死，2 有用 + 13 高干扰）
# =================================================================
# 有用网站①：含真实官方精确数据（国家统计局 2024 年统计公报口径）
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

# 有用网站②：政府网口径，与网站①数据相互印证
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

# 13 个高干扰网站：标题/正文大量使用 GDP、经济、增长等词，但无精确官方数据
SITES_NOISE = [
    {"title": "2024年中国GDP增长态势深度分析报告", "content": """
2024年中国GDP增长态势深度分析报告
在全球经济复杂多变的背景下，中国经济展现出强大韧性与活力。本报告基于公开信息与专家访谈，对全年GDP运行态势进行系统梳理。

从总量看，中国经济总量继续稳步攀升，稳居世界第二大经济体地位。从增速看，全年经济保持平稳增长，各季度增速总体处于合理区间，呈现前稳后升的运行特征。

从结构看，第三产业对经济增长的贡献持续提升，消费成为拉动经济增长的主要引擎。工业领域，高技术制造业与装备制造业保持较快增长，新旧动能转换加速推进。

从需求看，投资、消费、出口三驾马车协同发力，内需对经济增长的支撑作用进一步显现。房地产市场处于深度调整期，对经济增速形成一定拖累，但总体可控。

多位受访经济学家认为，中国经济长期向好的基本面没有改变，高质量发展扎实推进，全年经济增速在全球主要经济体中保持领先水平。

需要注意的是，上述分析基于趋势判断与专家观点，具体精确数值请以国家统计局官方发布为准。
""".strip()},
    {"title": "2024年全球GDP排名前瞻：中美差距与格局演变", "content": """
2024年全球GDP排名前瞻
本文综合多家国际机构预测，对2024年全球主要经济体GDP规模与排名进行分析。

分析指出，全球前两大经济体的位次保持稳定，中国经济总量稳居全球第二。在增速对比上，中国明显快于主要发达经济体，双方总量差距呈逐步收窄态势。

国际货币基金组织（IMF）、世界银行等机构在最新展望中，均对中国经济增速给出积极预测，认为中国经济对全球增长的贡献率继续保持在较高水平。

从人均GDP角度看，中国仍处于中等偏上收入国家行列，与发达经济体存在差距，但追赶步伐稳健。

值得关注的是，全球产业链重构与地缘政治因素对各国GDP增长格局产生深远影响。部分新兴市场国家凭借资源与人口优势，增速表现亮眼。

本文数据为机构预测与估算值，与官方最终核算数据可能存在差异，请谨慎引用。
""".strip()},
    {"title": "GDP增速与A股市场表现相关性研究", "content": """
GDP增速与A股市场表现相关性研究
长期以来，投资者普遍关注GDP增速与股市走势之间的关系。本文从历史数据出发，对这一相关性进行实证探讨。

研究显示，GDP增速与股市短期表现的相关性较弱，但从长期看，经济基本面仍是决定资本市场中枢的核心变量。当经济增速企稳回升时，企业盈利预期改善，估值中枢往往随之抬升。

分行业看，周期性行业与GDP增速相关性最强，消费、医药等行业则更多受自身景气周期影响。科技板块与宏观经济增速的相关性近年来有所增强。

需要指出的是，股市受流动性、风险偏好、政策预期等多重因素影响，GDP增速只是其中一个参考维度。投资者不应仅依据GDP数据做出投资决策。

本研究的统计区间与样本选择可能影响结论稳健性，相关观点仅供参考。
""".strip()},
    {"title": "中国经济高质量发展：告别唯GDP论", "content": """
中国经济高质量发展：告别唯GDP论
进入新发展阶段，中国经济从高速增长转向高质量发展。文章指出，评价经济发展不能只看GDP总量和增速，更要看发展质量、结构优化与民生改善。

近年来，研发经费投入强度持续提升，单位GDP能耗稳步下降，绿色发展成效显著。服务业占比上升，高技术产业投资保持两位数增长，经济结构不断优化。

同时，区域协调发展战略深入推进，城乡差距逐步缩小，共同富裕迈出坚实步伐。教育、医疗、养老等民生领域投入持续加大。

文章强调，高质量发展要求保持经济增速在合理区间，为结构调整和转型升级留出空间。宏观政策注重跨周期与逆周期调节相结合，保持经济运行在合理区间。

从全球经验看，当经济体量达到一定规模后，增速放缓是普遍规律，关键在于增长质量与可持续性。
""".strip()},
    {"title": "2024年经济形势十大预判与风险提示", "content": """
2024年经济形势十大预判与风险提示
岁末年初，多家研究机构发布年度展望报告，对来年经济形势作出预判。综合各方观点，梳理如下。

预判一：经济增速保持平稳，全年呈现前低后高走势。预判二：消费继续恢复，服务消费成为亮点。预判三：出口面临外部压力，但结构持续优化。预判四：基建投资托底作用明显，制造业投资保持韧性。预判五：房地产市场继续筑底，政策持续宽松。预判六：物价低位运行，通胀压力温和。预判七：货币政策保持宽松，流动性合理充裕。预判八：财政政策更加积极，专项债发行提速。预判九：人民币汇率双向波动，总体稳定。预判十：新旧动能转换加快，新兴产业贡献提升。

风险方面，外部环境不确定性、内需不足、地方债务化解等仍是主要挑战。机构普遍认为，宏观政策将加大逆周期调节力度，托底经济。

以上预判基于机构模型与专家观点，不代表官方立场。
""".strip()},
    {"title": "GDP核算方法改革：从总量导向到质量导向", "content": """
GDP核算方法改革：从总量导向到质量导向
随着经济进入高质量发展阶段，GDP核算方法也在不断改进完善。本文介绍我国国民经济核算体系改革的最新进展。

近年来，我国积极推动核算制度改革，将研发支出计入GDP、完善数字经济核算、推进地区生产总值统一核算改革等。这些改革使GDP数据更加真实、全面、准确地反映经济发展实际。

在核算实践中，坚持"凡出数必有据、凡数据必核查"原则，加强数据质量管控。统计执法检查力度加大，坚决防范和惩治统计造假。

专家指出，核算方法改革是国际通行做法，有利于国际比较。我国还积极参与国际统计标准制定，提升统计能力与数据公信力。

需要说明的是，核算方法调整会导致历史数据修订，这是正常现象，不影响经济基本面判断。
""".strip()},
    {"title": "2024年各省GDP竞赛：区域经济新版图", "content": """
2024年各省GDP竞赛：区域经济新版图
随着各地经济数据陆续披露，各省份GDP排名与区域格局引发关注。本文对区域经济发展态势进行梳理。

东部沿海省份经济体量继续领先，多个省份GDP站上新台阶。中西部地区增速表现亮眼，承接产业转移成效显著。东北地区经济逐步企稳，新旧动能转换初见成效。

从城市群看，长三角、珠三角、京津冀、成渝等城市群经济集聚效应增强，成为全国经济增长的重要引擎。县域经济活力提升，特色产业培育初见成效。

区域协调发展战略深入实施，东西部协作、对口支援等机制持续发力。一批国家级新区、自贸试验区发挥示范引领作用。

需要说明的是，各省GDP数据以省级统计局最终发布为准，本文仅作趋势性梳理，不构成精确排名依据。
""".strip()},
    {"title": "经济学家圆桌：2024年增长压力与转型机遇", "content": """
经济学家圆桌：2024年增长压力与转型机遇
本刊邀请多位知名经济学家，围绕当年经济形势展开圆桌讨论。以下为观点摘要。

关于增速，经济学家普遍认为，当年经济面临一定下行压力，但政策托底效应逐步显现，全年增速有望保持在目标区间附近。关键在于提振信心、激发活力。

关于内需，消费复苏呈现"服务强、商品弱"特征，建议通过提高居民收入、优化消费环境释放消费潜力。投资方面，基础设施与新基建仍是稳增长的重要抓手。

关于产业，新质生产力成为高频词，人工智能、新能源、高端制造等战略性新兴产业快速发展，为经济注入新动能。

关于政策，专家建议财政政策更加积极有为，货币政策精准有力，加强政策协调配合，形成合力。

以上为专家个人观点，不代表本刊立场。
""".strip()},
    {"title": "2024年消费市场回暖了吗？内需观察报告", "content": """
2024年消费市场回暖了吗？
消费是经济增长的重要引擎。本文基于高频数据与实地调研，观察当年消费市场运行情况。

从整体看，消费市场呈现稳步恢复态势，社会消费品零售总额保持增长。服务消费表现尤为亮眼，餐饮、旅游、文娱等领域需求旺盛。

从结构看，升级类消费增长较快，新能源汽车、智能家居、国货潮品成为消费新热点。线上消费占比持续提升，直播电商、即时零售等新业态蓬勃发展。

从区域看，一线城市消费韧性强，县域消费潜力加速释放。以旧换新等促消费政策效果逐步显现。

受访商户表示，客流与销售额较上年有所改善，但对消费持续回升的预期保持谨慎乐观。

本文为定性观察，具体数据请以官方统计为准。
""".strip()},
    {"title": "房地产与GDP：牵一发动全身的深度剖析", "content": """
房地产与GDP：牵一发动全身的深度剖析
房地产产业链条长、关联行业多，对GDP增长具有重要影响。本文剖析二者关系。

从直接贡献看，房地产开发投资、房地产服务等是GDP的组成部分。从间接影响看，房地产通过带动建材、家电、家具等上下游产业，对经济增长产生乘数效应。

近年来，房地产市场供求关系发生重大变化，进入深度调整期。房地产开发投资有所回落，土地出让收入下降，对地方财政与经济增速形成拖累。

为促进市场平稳健康发展，各地因城施策优化调控政策，取消限购、降低首付比例与贷款利率等。政策效果有待进一步显现。

专家认为，房地产市场有望逐步企稳，对经济的拖累作用趋于减弱，但恢复节奏取决于居民收入预期与信心修复。

本文为分析性内容，不构成投资建议。
""".strip()},
    {"title": "新质生产力如何重塑中国经济版图", "content": """
新质生产力如何重塑中国经济版图
新质生产力是当前经济领域的高频概念。本文探讨其内涵与对经济格局的影响。

新质生产力以科技创新为核心驱动，以高技术、高效能、高质量为特征，涵盖人工智能、量子科技、生物制造、商业航天、低空经济等前沿领域。

从对GDP的影响看，新质生产力通过提升全要素生产率，推动经济潜在增速上移。高技术产业增加值增速明显快于规上工业平均水平，战略性新兴产业占比稳步提升。

区域层面，创新资源向科创走廊、高新区集聚，形成若干创新增长极。传统产业通过技术改造与数字化转型，焕发新的生机。

专家表示，发展新质生产力不是忽视传统产业，而是推动传统产业高端化、智能化、绿色化发展。

本文为概念解读与趋势分析。
""".strip()},
    {"title": "2024年就业形势与经济增长的关系观察", "content": """
2024年就业形势与经济增长的关系观察
就业是最大的民生，经济增长与就业形势密切相关。本文对当年就业市场进行观察。

从总量看，全年城镇新增就业保持稳定，就业形势总体平稳。从结构看，青年就业压力仍然存在，但政策支持下逐步缓解。服务业吸纳就业能力增强，灵活就业规模扩大。

经济增长对就业的拉动作用持续显现。经济总量每增长一个百分点，带动城镇新增就业的能力保持稳定。服务业占比提升，增强了经济增长的就业弹性。

职业技能培训力度加大，重点群体就业帮扶持续强化。失业保险稳岗返还、吸纳就业补贴等政策落地见效。

专家指出，保持经济增速在合理区间，是稳定和扩大就业的基础。促进高质量充分就业仍需多方发力。

本文为观察性分析，具体数据请以官方发布为准。
""".strip()},
    {"title": "外贸出口对GDP贡献再审视：韧性与挑战", "content": """
外贸出口对GDP贡献再审视
外需是拉动经济增长的重要力量。本文审视外贸出口对GDP的贡献与挑战。

从规模看，我国货物贸易进出口总额保持增长，出口市场份额稳中有升，展现出强大韧性。机电产品、高新技术产品出口占比提升，出口结构持续优化。

从市场看，对东盟、共建"一带一路"国家出口增长较快，市场多元化成效显著。跨境电商、海外仓等新业态新模式快速发展。

从挑战看，全球贸易保护主义抬头、外需不确定性增加，对出口形成压力。汇率波动、物流成本等也是企业面临的实际问题。

专家建议，在稳住外贸基本盘的同时，着力扩大内需，形成以国内大循环为主体、国内国际双循环相互促进的新发展格局。

本文为分析性内容，具体数据请以海关总署公布为准。
""".strip()},
]

# 汇总所有站点：2 有用 + 13 干扰 = 15 个
SITES = [{"id": i, "port": 8001 + i, "good": True, **SITE_GOOD_1} for i in [0]] + \
        [{"id": i, "port": 8001 + i, "good": True, **SITE_GOOD_2} for i in [1]] + \
        [{"id": i + 2, "port": 8003 + i, "good": False, **s} for i, s in enumerate(SITES_NOISE)]

GOOD_SITES = [s for s in SITES if s["good"]]
NOISE_SITES = [s for s in SITES if not s["good"]]

# =================================================================
# 二、本地网站服务器（15 个端口）
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
    for srv in servers:
        try:
            srv.shutdown(); srv.server_close()
        except Exception:
            pass

# =================================================================
# 三、★ 进程级网络隔离（只锁当前程序，不影响系统其他程序） ★
# =================================================================
_API_DOMAIN = None
_API_IPS = set()
_ALLOWED_EXTRA = set()   # 可额外放行的域名/IP（如代理）

_orig_create_connection = socket.create_connection

def _is_allowed(host):
    """判断目标地址是否在白名单内"""
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
    host = address[0] if isinstance(address, tuple) else address
    if not _is_allowed(host):
        raise socket.error(
            f"[进程级隔离] 已阻止访问非白名单地址: {host}（仅允许本地网站127.0.0.1与AI API）"
        )
    return _orig_create_connection(address, *args, **kwargs)

def apply_socket_isolation(api_url):
    """启用进程内 socket 隔离。返回白名单描述文本。"""
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
# =================================================================
search_call_log = []   # 记录每次搜索的 query 与命中 URL（用于验证补搜）

def fake_search(query, num_results=8):
    """模拟 Bing 搜索：第1次只返回干扰站（触发补搜），补搜时有用站+100分必然命中"""
    query = query or ""
    search_call_log.append({"query": query, "time": time.strftime("%H:%M:%S")})
    is_refine = len(search_call_log) > 1   # 第2次及以后 = 补搜

    # 细粒度分词：拆出中文段 + 英文/数字段
    words = re.findall(r'[\u4e00-\u9fff]+|[A-Za-z0-9.]+', query)

    scored = []
    for site in SITES:
        score = 0
        if site["good"]:
            score += 100          # 有用站基础分：保证补搜时必然优先返回
        for w in words:
            if w and w in site["title"]:
                score += 10
            if w and w in site["content"]:
                score += 3
        scored.append((score, site))
    scored.sort(key=lambda x: -x[0])

    if not is_refine:
        # 第1次搜索：只返回干扰站 → AI 找不到精确数据 → 申请补搜
        top = [item for item in scored if not item[1]["good"]][:num_results]
    else:
        # 补搜：有用站有 +100 基础分，必然排最前
        top = scored[:num_results]

    results = []
    for _, site in top:
        snippet = site["content"].replace("\n", " ").strip()[:150]
        results.append({"title": site["title"], "url": site["url"], "snippet": snippet})
        search_call_log[-1].setdefault("hits", []).append(site["title"])
    return results

# =================================================================
# 五、主测试流程
# =================================================================
def main():
    print("=" * 66)
    print("  search_and_summarize 补搜功能 · 进程级隔离测试")
    print("=" * 66)
    print()

    # ---- 导入主程序 ----
    print("▶ 导入主程序 mcp_websearch_server ...")
    import importlib.util
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(base_dir, "mcp_websearch_server.py")
    spec = importlib.util.spec_from_file_location("mcp_websearch_server", server_path)
    server_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_mod)
    # 恢复测试程序自身 stdio 编码（主程序会包一层 TextIOWrapper）
    if hasattr(sys.stdout, "reconfigure"):
        try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass

    api_url = server_mod._ai_config.get("api_url", "")
    api_key = server_mod._ai_config.get("api_key", "")
    print(f"  API 地址: {api_url}")
    print(f"  API 密钥: {'已配置 (' + api_key[:6] + '...)' if api_key else '未配置'}")

    # ---- 启动 15 个本地网站 ----
    print("\n▶ 启动 15 个本地模拟网站 ...")
    servers = start_site_servers()
    time.sleep(0.5)
    print(f"  已启动 {len(servers)} 个站点（端口 8001~8015）")
    print(f"  其中有用站点 {len(GOOD_SITES)} 个，干扰站点 {len(NOISE_SITES)} 个")

    # ---- 进程级网络隔离（只锁当前进程） ----
    print("\n▶ 应用进程级网络隔离 ...")
    apply_socket_isolation(api_url)

    # 注册恢复（站点服务器关闭；socket patch 随进程结束自动失效）
    atexit.register(stop_site_servers, servers)

    try:
        # ---- 替换搜索为本地假搜索 ----
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

        # ---- 输出搜索调用日志 ----
        print("\n" + "-" * 66)
        print("📡 假搜索调用记录（验证是否触发补搜）")
        print("-" * 66)
        for i, log in enumerate(search_call_log, 1):
            hits = "、".join(log.get("hits", [])) or "(无命中)"
            print(f"  第{i}次搜索: {log['query']}")
            print(f"    命中: {hits[:100]}")

        # ---- 验证 ----
        print("\n" + "-" * 66)
        print("🔍 测试验证")
        print("-" * 66)
        all_text = json.dumps(result, ensure_ascii=False)
        flat = all_text.replace(",", "")   # 兼容 AI 输出的千分位逗号 1,349,084
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

        # ---- 输出最终结果摘要 ----
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
