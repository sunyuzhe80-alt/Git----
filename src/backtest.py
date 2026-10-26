"""逐日持仓回测。今天收盘生成名单，下一交易日收盘调仓。

教学模型：用数据源价格作为交易/估值单位，允许碎股；无借贷、无做空。
真实券商订单、分红现金流、税费、汇率、停牌与成交限制不在本模型中。
"""
import math
from .factor import rank_momentum


def account_value(shares, cash, prices):
    """账户价值 = 现金 + 各只股票的持有单位数 × 当日价格。"""
    return cash + sum(shares[s] * prices[s] for s in shares)


def rebalance(shares, cash, prices, weights, cost):
    """按扣费后的账户价值分配资金，确保不会买超或透支。

    设扣费前价值 E，扣费后价值 V，目标股票金额 w*V，原持仓金额 old。
    则 V + cost * sum(abs(w*V-old)) = E。用二分法求 V。
    sum(abs(...)) 是买入和卖出金额之和；全换仓时约为账户价值的两倍。
    """
    before = account_value(shares, cash, prices)
    old_amounts = {s: shares[s]*prices[s] for s in shares}
    low, high = 0.0, before
    for _ in range(80):
        value = (low+high)/2
        turnover = sum(abs(weights[s]*value-old_amounts[s]) for s in shares)
        if value + cost*turnover > before:
            high = value
        else:
            low = value
    after = (low+high)/2
    amounts = {s: weights[s]*after for s in shares}
    deltas = {s: amounts[s]-old_amounts[s] for s in shares}
    fee = cost*sum(abs(change) for change in deltas.values())
    new_shares = {s: amounts[s]/prices[s] for s in shares}
    new_cash = before-fee-sum(amounts.values())
    if abs(new_cash) < before*1e-12:
        new_cash = 0.0  # 消除浮点运算导致的极小尾差。
    return new_shares, new_cash, fee, deltas


def run_backtest(rows, symbols, lookback=20, interval=5, top_n=2, cost=0.001, capital=100000.0):
    """返回每日记录、股票交易、每期排名和调仓汇总；不自动改变因子方向。"""
    if not isinstance(lookback, int) or isinstance(lookback, bool) or lookback < 1:
        raise ValueError("lookback 必须为正整数")
    if not isinstance(interval, int) or isinstance(interval, bool) or interval < 1:
        raise ValueError("interval 必须为正整数")
    if not isinstance(top_n, int) or isinstance(top_n, bool) or not 1 <= top_n <= len(symbols):
        raise ValueError("top_n 必须为 1 到股票数量之间的整数")
    if not math.isfinite(cost) or not 0 <= cost < 1:
        raise ValueError("单边成本必须在 [0, 1) 内")
    if not math.isfinite(capital) or capital <= 0:
        raise ValueError("初始资金必须为有限正数")
    if len(rows) < lookback+3:
        raise ValueError("数据至少需要 lookback + 3 行，包含信号、成交和收益观察")
    shares = {s: 0.0 for s in symbols}
    bench_shares = shares.copy()
    cash = bench_cash = capital
    previous_value = previous_bench = capital
    pending = None  # 暂存今天收盘后才能执行的昨日名单。
    daily, trades, rankings, rebalances = [], [], [], []
    for i in range(lookback, len(rows)):
        day = rows[i]["date"]
        prices = rows[i]["prices"]
        before = account_value(shares, cash, prices)
        bench_before = account_value(bench_shares, bench_cash, prices)
        market_pnl = before-previous_value
        fee = bench_fee = 0.0
        turnover_ratio = 0.0
        executed = 0
        signal_date = ""
        # 先按旧持仓获得当天涨跌，再于收盘执行昨天已知的名单。
        if pending is not None:
            signal_date, weights = pending
            shares, cash, fee, deltas = rebalance(shares, cash, prices, weights, cost)
            traded_amount = sum(abs(change) for change in deltas.values())
            turnover_ratio = traded_amount/before
            executed = 1
            rebalances.append({"signal_date": signal_date, "execution_date": day,
                               "selected": ",".join(s for s in symbols if weights[s] > 0),
                               "value_before": before, "fee": fee,
                               "traded_amount": traded_amount, "turnover_ratio": turnover_ratio})
            for s, change in deltas.items():
                if abs(change) > 1e-8:
                    trades.append({"account": "strategy", "signal_date": signal_date,
                                   "date": day, "symbol": s, "action": "BUY" if change > 0 else "SELL",
                                   "price": prices[s], "units": abs(change)/prices[s],
                                   "amount": abs(change), "fee": abs(change)*cost})
            pending = None
        # 基准只在首次策略成交日买入四只股票，此后保持单位数不变。
        if i == lookback+1:
            weights = {s: 1/len(symbols) for s in symbols}
            bench_shares, bench_cash, bench_fee, deltas = rebalance(bench_shares, bench_cash, prices, weights, cost)
            for s, change in deltas.items():
                trades.append({"account": "benchmark", "signal_date": rows[i-1]["date"],
                               "date": day, "symbol": s, "action": "BUY", "price": prices[s],
                               "units": change/prices[s], "amount": change, "fee": change*cost})
        value = account_value(shares, cash, prices)
        bench_value = account_value(bench_shares, bench_cash, prices)
        record = {"date": day, "rebalance": executed, "executed_signal_date": signal_date,
                  "market_pnl": market_pnl, "strategy_fee": fee, "benchmark_fee": bench_fee,
                  "turnover_ratio": turnover_ratio, "cash": cash,
                  "strategy_value": value, "benchmark_value": bench_value,
                  "strategy_return": value/previous_value-1,
                  "benchmark_return": bench_value/previous_bench-1,
                  "strategy_nav": value/capital, "benchmark_nav": bench_value/capital}
        for s in symbols:
            record[s+"_price"] = prices[s]
            record[s+"_units"] = shares[s]
            record[s+"_weight"] = shares[s]*prices[s]/value
            record[s+"_benchmark_units"] = bench_shares[s]
        daily.append(record)
        previous_value, previous_bench = value, bench_value
        # 仅在预先固定的日期打分；不读取下一日价格来决定今天选什么。
        if (i-lookback) % interval == 0:
            ranked, targets = rank_momentum(rows, i, lookback, top_n, symbols)
            next_day = rows[i+1]["date"] if i+1 < len(rows) else ""
            rankings.extend({"signal_date": day, "planned_execution_date": next_day, **r} for r in ranked)
            if next_day:
                pending = (day, targets)
    return daily, trades, rankings, rebalances
