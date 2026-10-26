"""生成 CSV、JSON、Markdown 和离线 HTML；绘图使用 SVG，无需第三方库。"""
import csv
import json
from html import escape
from .metrics import drawdowns, yearly_returns

METRICS = [("total_return", "累计收益"), ("annual_return", "年化收益"),
           ("annual_volatility", "年化波动率"), ("sharpe", "夏普比率"),
           ("max_drawdown", "最大回撤"), ("final_nav", "期末净值")]


def csv_save(path, rows, fields=None):
    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def formatted(key, value):
    if value is None:
        return "不适用"
    return f"{value:.3f}" if key in ("sharpe", "final_nav") else f"{value:.2%}"


def line_chart(dates, series, title, percent=False):
    """series 为 (标签, 颜色, 数值列表) 的列表，生成可直接嵌入网页的矢量图。"""
    bottom, top = min(min(s[2]) for s in series), max(max(s[2]) for s in series)
    pad = max((top-bottom)*0.08, 0.005 if percent else 0.02)
    bottom, top = bottom-pad, top+pad
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 420" role="img" aria-label="'+escape(title)+'">',
           '<rect width="1040" height="420" rx="14" fill="#f8fafc"/>',
           '<g font-family="Arial, Microsoft YaHei, sans-serif" font-size="13" fill="#475569">',
           f'<text x="88" y="30" font-size="18" fill="#172033">{escape(title)}</text>']
    for i, (label, color, _) in enumerate(series):
        x = 88+i*300
        svg += [f'<path d="M{x} 55h22" stroke="{color}" stroke-width="3"/>',
                f'<text x="{x+30}" y="59">{escape(label)}</text>']
    for k in range(6):
        value, y = bottom+(top-bottom)*k/5, 345-260*k/5
        label = f"{value:.0%}" if percent else f"{value:.2f}"
        svg += [f'<path d="M88 {y}H1000" stroke="#dce3ee"/>', f'<text x="12" y="{y+5}">{label}</text>']
    for _, color, values in series:
        points = ' '.join(f'{88+912*i/(len(values)-1):.2f},{345-260*(v-bottom)/(top-bottom):.2f}' for i, v in enumerate(values))
        svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.8"/>')
    for i in sorted({0, (len(dates)-1)//2, len(dates)-1}):
        x = 88+912*i/(len(dates)-1)
        anchor = "start" if i == 0 else ("end" if i == len(dates)-1 else "middle")
        svg.append(f'<text x="{x}" y="380" text-anchor="{anchor}">{dates[i]}</text>')
    svg.append('</g></svg>')
    return '\n'.join(svg)


def save_results(folder, daily, trades, rankings, rebalances, summary):
    folder.mkdir(parents=True, exist_ok=True)
    csv_save(folder/'daily_results.csv', daily)
    csv_save(folder/'trades.csv', trades, ['account', 'signal_date', 'date', 'symbol', 'action', 'price', 'units', 'amount', 'fee'])
    csv_save(folder/'factor_rankings.csv', rankings)
    csv_save(folder/'rebalances.csv', rebalances)
    years = yearly_returns(daily)
    csv_save(folder/'yearly_returns.csv', years)
    (folder/'metrics.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    dates = [r['date'] for r in daily]
    nav_svg = line_chart(dates, [('动量策略（扣费后）', '#2563eb', [r['strategy_nav'] for r in daily]),
                                ('四股买入持有（扣费后）', '#d97706', [r['benchmark_nav'] for r in daily])], '累计净值 · 起点为 1')
    dd_svg = line_chart(dates, [('动量策略', '#2563eb', drawdowns(daily, 'strategy')),
                               ('四股买入持有', '#d97706', drawdowns(daily, 'benchmark'))], '历史回撤 · 越接近 0 越好', True)
    (folder/'nav.svg').write_text(nav_svg, encoding='utf-8')
    (folder/'drawdown.svg').write_text(dd_svg, encoding='utf-8')
    table, markdown = [], ['| 指标 | 动量策略 | 四股买入持有 |', '|---|---:|---:|']
    for key, label in METRICS:
        a, b = [formatted(key, summary[name][key]) for name in ('strategy', 'benchmark')]
        table.append(f'<tr><td>{label}</td><td>{a}</td><td>{b}</td></tr>')
        markdown.append(f'| {label} | {a} | {b} |')
    difference = summary['strategy']['total_return']-summary['benchmark']['total_return']
    conclusion = f'本样本中策略累计收益比基准{"高" if difference >= 0 else "低"} {abs(difference)*100:.2f} 个百分点。'
    conclusion += '这是两者累计收益之差，不是相对净值收益率，也不证明未来有效。'
    limitations = '四只事后选定股票存在选择及幸存者偏差，不能代表全市场；价格复权与分红处理未独立核验，不宣称含分红总收益；只做历史全样本描述，没有独立样本外验证。允许碎股、不借贷、不做空，未模拟真实成交限制、税务或汇率。'
    s = summary
    year_table = ''.join(f'<tr><td>{r["year"]}</td><td>{r["periods"]}</td><td>{r["strategy_return"]:.2%}</td><td>{r["benchmark_return"]:.2%}</td></tr>' for r in years)
    first_rank = ''.join(f'<tr><td>{r["symbol"]}</td><td>{r["momentum"]:.2%}</td><td>{r["rank"]}</td><td>{"是" if r["selected"] else "否"}</td></tr>' for r in rankings[:len(s['symbols'])])
    style = '''body{margin:0;background:#eef2f7;color:#172033;font-family:"Microsoft YaHei",Arial,sans-serif;line-height:1.7}main{max-width:1120px;margin:auto;padding:32px 20px}header{background:#14243e;color:white;padding:30px;border-radius:18px}header p{color:#d6e2f4}h1{font-size:30px;margin:0}h2{font-size:21px;margin-top:0}.badge{display:inline-block;background:#dceafe;color:#1d4ed8;padding:4px 12px;border-radius:16px;font-size:13px}.section{background:white;border-radius:16px;padding:24px;margin-top:20px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:11px 10px;border-bottom:1px solid #e2e8f0;text-align:left}th{background:#f8fafc}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:20px 0}.card{background:white;border-radius:14px;padding:20px}.value{font-size:28px;font-weight:bold;color:#1d4ed8}.muted{color:#64748b;font-size:13px}svg{display:block;width:100%;height:auto}.note{border-left:4px solid #d97706;padding:12px 18px;background:#fff8eb}code{background:#eef2f7;padding:2px 5px}a{color:#1d4ed8}@media(max-width:650px){.cards{grid-template-columns:1fr}h1{font-size:24px}.section{padding:16px}td,th{padding:8px 5px}}'''
    html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>动量选股回测报告</title><style>{style}</style></head>
<body><main><header><span class="badge">实习生测试一 · 因子选股教学项目</span><h1>近期表现较强的股票，之后还能继续走强吗？</h1>
<p>{s['lookback']} 日动量排名 · 每 {s['interval']} 个交易日选前 {s['top_n']} 只 · 下一交易日收盘调仓</p>
<p>{s['evaluation_start']} — {s['evaluation_end']} ｜ AAPL / IBM / MSFT / SBUX</p></header>
<div class="cards"><div class="card">策略累计收益<div class="value">{s['strategy']['total_return']:.2%}</div><span class="muted">扣除模拟交易成本</span></div>
<div class="card">策略夏普比率<div class="value">{formatted('sharpe',s['strategy']['sharpe'])}</div><span class="muted">无风险利率设为 0</span></div>
<div class="card">策略最大回撤<div class="value">{s['strategy']['max_drawdown']:.2%}</div><span class="muted">历史峰值至后续低点的最大跌幅</span></div></div>
<section class="section"><h2>01 / 收益和风险</h2>{nav_svg}<br>{dd_svg}<table><tr><th>指标</th><th>动量策略</th><th>四股买入持有</th></tr>{''.join(table)}</table><p class="note">{conclusion}</p></section>
<section class="section"><h2>02 / 策略规则与公平比较</h2><p>分数 = 当天价格 ÷ {s['lookback']} 个交易日前价格 − 1。按分数从高到低排名，同分按股票代码排序；即使全部下跌，仍选前 {s['top_n']} 只。调仓后按扣费后账户价值等权分配，期间保持持有单位数，权重自然漂移。</p>
<p>初始资金 {s['initial_capital']:,.2f}（模型计价单位）；单边综合成本 {s['cost']:.2%}，按实际买卖金额扣除，包含换入和换出两侧。基准在首次策略成交日各买入四股的 25%，之后不再调仓。两者期末按市值计价，不强制卖出。</p>
<p>信号截止于当天收盘，下一交易日收盘才成交；成交前涨跌由原有持仓承担。每 {s['interval']} 个交易日不等同于每个自然周。</p>
<p>执行调仓 {s['rebalance_count']} 次；策略逐股成交 {s['strategy_trade_count']} 笔；策略累计费用 {s['strategy_total_fee']:,.2f}，基准费用 {s['benchmark_total_fee']:,.2f}（模型计价单位，未做现金流折现）。</p></section>
<section class="section"><h2>03 / 第一次选股，如何得到名单？</h2><p>信号日期：{rankings[0]['signal_date']}；计划成交：{rankings[0]['planned_execution_date']}。</p><table><tr><th>股票</th><th>动量分数</th><th>排名</th><th>选中</th></tr>{first_rank}</table></section>
<section class="section"><h2>04 / 分年度表现</h2><table><tr><th>年份</th><th>收益期数</th><th>策略收益</th><th>基准收益</th></tr>{year_table}</table><p class="muted">按日收益连乘；首尾年份不完整，不能直接与完整年度比较。不是训练集/测试集划分。</p></section>
<section class="section"><h2>05 / 数据、参考与研究限制</h2><p>原始样本：{s['data_start']} 至 {s['data_end']}，共 {s['source_rows']} 行；价格来自 <a href="https://github.com/plotly/datasets/blob/master/stockdata.csv">Plotly datasets / stockdata.csv</a>，原始文件和校验值随项目附带。{escape(s['price_basis'])}。</p>
<p>参考用户提供的 factor-toolkit-0.1.4，借鉴“因子打分—排名—评价”流程。参考示例是合成数据上的 5 日反转；本项目是历史真实样本上的动量选股，并独立实现持仓回测，没有自动翻转方向或用全样本挑最优参数。</p>
<p class="note">{limitations}</p><p class="muted">本报告仅展示固定规则的历史表现。核心代码由 Codex AI 辅助编写，提交者应如实说明，并自行理解、调试和录制讲解。</p></section>
<section class="section"><h2>06 / 核对结果</h2><p>同目录：<a href="daily_results.csv">每日账户</a> · <a href="factor_rankings.csv">每期排名</a> · <a href="trades.csv">逐股交易</a> · <a href="rebalances.csv">调仓汇总</a> · <a href="metrics.json">完整指标</a></p><p class="muted">图表已内嵌，本 HTML 可单独离线查看；明细链接需保留同目录文件。</p></section>
</main></body></html>'''
    (folder/'report.html').write_text(html, encoding='utf-8')
    result_text = '\n'.join(['# 默认回测结果', '', f"评价区间：{s['evaluation_start']} 至 {s['evaluation_end']}。", '', *markdown, '', conclusion, '', '## 研究限制', '', limitations, '', '数据、模型和比较口径详见离线 HTML 报告及项目文档。'])
    (folder/'结果摘要.md').write_text(result_text, encoding='utf-8')
