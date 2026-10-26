"""补充研究：固定选股规则，只比较预先列出的成本情景，不挑最优参数。

运行：python tools/cost_sensitivity.py。输出 cost_sensitivity.csv。
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import SYMBOLS, load_prices
from src.backtest import run_backtest
from src.metrics import performance


def main():
    rows = load_prices(ROOT/'data'/'prices.csv')
    result = []
    for cost in (0.0, 0.001, 0.002):
        daily, _, _, _ = run_backtest(rows, SYMBOLS, cost=cost)
        a, b = performance(daily, 'strategy'), performance(daily, 'benchmark')
        result.append({'one_way_cost':cost, 'strategy_total_return':a['total_return'],
                       'benchmark_total_return':b['total_return'], 'strategy_sharpe':a['sharpe'],
                       'strategy_max_drawdown':a['max_drawdown'],
                       'strategy_total_fee':sum(r['strategy_fee'] for r in daily)})
    output = ROOT/'outputs'
    output.mkdir(exist_ok=True)
    with (output/'cost_sensitivity.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    lines = ['# 固定规则下的成本敏感性检查', '',
             '保持 20 日动量、每 5 个交易日选前 2 只、初始资金 100000 不变；仅比较预先给定的三个单边成本情景。不是参数择优，也不修改默认结果。', '',
             '| 单边成本 | 策略累计收益 | 基准累计收益 | 策略夏普 | 策略最大回撤 |',
             '|---|---:|---:|---:|---:|']
    for r in result:
        lines.append(f"| {r['one_way_cost']:.2%} | {r['strategy_total_return']:.2%} | {r['benchmark_total_return']:.2%} | {r['strategy_sharpe']:.3f} | {r['strategy_max_drawdown']:.2%} |")
    lines.extend(['', '这三个情景中，即使不计交易成本，策略也未超过同口径基准；成本上升会进一步拖累本样本中的策略表现。不能把全部跑输都归咎于手续费。', '',
                  '累计费用是各日费用的名义金额之和，不等于“零成本期末资产减含成本期末资产”，因为费用还会改变后续持仓和复利路径。', '',
                  '此工具固定使用附带数据和默认选股规则，不沿用 main.py 的自定义参数。报告采用同样的数据口径及研究限制。'])
    (output/'成本敏感性说明.md').write_text('\n'.join(lines), encoding='utf-8')
    print('三个固定成本情景已保存；默认策略和默认报告没有改变。')


if __name__ == '__main__':
    main()
