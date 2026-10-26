"""因子就是给股票打分：本项目分数为过去一段时间的涨跌幅。"""


def rank_momentum(rows, index, lookback, top_n, symbols):
    """只用截至 index 当天的数据；返回完整排名和等权目标仓位。"""
    scores = {
        symbol: rows[index]["prices"][symbol] / rows[index-lookback]["prices"][symbol] - 1
        for symbol in symbols
    }
    # 分数高的排前面；同分时按代码字母排序，使结果可重复。
    ordered = sorted(symbols, key=lambda symbol: (-scores[symbol], symbol))
    selected = set(ordered[:top_n])
    weights = {symbol: (1/top_n if symbol in selected else 0.0) for symbol in symbols}
    ranking = [{"symbol": symbol, "momentum": scores[symbol], "rank": number,
                "selected": int(symbol in selected), "target_weight": weights[symbol]}
               for number, symbol in enumerate(ordered, 1)]
    return ranking, weights
