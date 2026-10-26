"""入口：参数 → 数据 → 动量排名 → 回测 → 绩效 → 离线报告。"""
import argparse
import hashlib
from pathlib import Path
from src.data import SYMBOLS, load_prices
from src.backtest import run_backtest
from src.metrics import performance
from src.report import save_results

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="实习测试一：20 日动量选股策略。默认离线运行。")
    parser.add_argument("--data", type=Path, default=ROOT/"data"/"prices.csv")
    parser.add_argument("--lookback", type=int, default=20, help="动量回看交易日数")
    parser.add_argument("--interval", type=int, default=5, help="两次信号之间的交易日数，不等同于自然周")
    parser.add_argument("--top", type=int, default=2, help="选入股票数")
    parser.add_argument("--cost", type=float, default=0.001, help="每笔买卖金额的综合成本比例")
    parser.add_argument("--capital", type=float, default=100000, help="初始资金，以数据源价格计价单位计算")
    parser.add_argument("--output", type=Path, default=ROOT/"outputs")
    args = parser.parse_args()
    try:
        rows = load_prices(args.data)
        daily, trades, rankings, rebalances = run_backtest(rows, SYMBOLS, args.lookback, args.interval, args.top, args.cost, args.capital)
        summary = {"strategy_name": "20 日动量选股（参数可调整）", "symbols": list(SYMBOLS),
                   "data_start": str(rows[0]["date"]), "data_end": str(rows[-1]["date"]), "source_rows": len(rows),
                   "evaluation_start": str(daily[0]["date"]), "evaluation_end": str(daily[-1]["date"]),
                   "return_periods": len(daily)-1, "lookback": args.lookback, "interval": args.interval,
                   "top_n": args.top, "cost": args.cost, "initial_capital": args.capital,
                   "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
                   "rebalance_count": len(rebalances),
                   "strategy_trade_count": sum(t["account"] == "strategy" for t in trades),
                   "strategy_total_fee": sum(r["strategy_fee"] for r in daily),
                   "benchmark_total_fee": sum(r["benchmark_fee"] for r in daily),
                   "price_basis": "数据源历史价格，复权和分红处理未获独立核验；不宣称含分红总收益",
                   "research_scope": "四只事后选定股票的历史教学样本；全样本描述，无独立样本外验证"}
        save_results(args.output, daily, trades, rankings, rebalances, summary)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"运行失败：{error}\n")
    for name, label in (("strategy", "动量策略"), ("benchmark", "四股买入持有")):
        m = summary[name]
        sharpe = "不适用" if m["sharpe"] is None else f'{m["sharpe"]:.3f}'
        print(f'{label}：累计收益 {m["total_return"]:.2%}，夏普 {sharpe}，最大回撤 {m["max_drawdown"]:.2%}')
    print(f"排名记录：{len(rankings)} 条；调仓执行：{len(rebalances)} 次")
    print(f"报告：{(args.output/'report.html').resolve()}")


if __name__ == "__main__":
    main()
