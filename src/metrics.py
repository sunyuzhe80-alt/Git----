"""绩效指标：固定按一年 252 个交易日、无风险利率为 0 计算。"""
from math import sqrt
from statistics import mean, stdev


def performance(records, prefix):
    """首行是共同初始净值 1；它不作为一个收益期参加年化计算。"""
    returns = [r[prefix+"_return"] for r in records[1:]]
    navs = [r[prefix+"_nav"] for r in records]
    vol = stdev(returns) if len(returns) > 1 else 0.0
    peak, max_dd = navs[0], 0.0
    for nav in navs:
        peak = max(peak, nav)
        max_dd = max(max_dd, 1-nav/peak)
    return {"total_return": navs[-1]/navs[0]-1,
            "annual_return": (navs[-1]/navs[0])**(252/len(returns))-1,
            "annual_volatility": vol*sqrt(252),
            "sharpe": mean(returns)/vol*sqrt(252) if vol else None,
            "max_drawdown": max_dd, "final_nav": navs[-1],
            "positive_day_ratio": sum(r > 0 for r in returns)/len(returns)}


def drawdowns(records, prefix):
    peak, result = records[0][prefix+"_nav"], []
    for row in records:
        nav = row[prefix+"_nav"]
        peak = max(peak, nav)
        result.append(nav/peak-1)  # 图中以负值展示回撤。
    return result


def yearly_returns(records):
    """按每日收益连乘，首尾年份可能不完整，报告中会注明。"""
    by_year = {}
    for row in records[1:]:
        year = row["date"].year
        current = by_year.setdefault(year, {"year": year, "periods": 0, "strategy_growth": 1., "benchmark_growth": 1.})
        current["periods"] += 1
        current["strategy_growth"] *= 1+row["strategy_return"]
        current["benchmark_growth"] *= 1+row["benchmark_return"]
    return [{"year": r["year"], "periods": r["periods"], "strategy_return": r["strategy_growth"]-1,
             "benchmark_return": r["benchmark_growth"]-1} for r in by_year.values()]
