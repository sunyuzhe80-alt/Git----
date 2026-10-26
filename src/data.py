"""读取公开历史价格。只选取四只股票，不把 GSPC 指数当成股票买入。"""
import csv
import math
from datetime import datetime

SYMBOLS = ("AAPL", "IBM", "MSFT", "SBUX")


def load_prices(path, symbols=SYMBOLS):
    """输入 CSV 路径，返回按日期排列的记录；有脏数据时立即提示。"""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"Date", *symbols}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("CSV 缺少列：" + ", ".join(sorted(required-set(reader.fieldnames or []))))
        for line, raw in enumerate(reader, 2):
            try:
                # Python 3.6 没有 date.fromisoformat，使用 strptime 解析日期。
                day = datetime.strptime(raw["Date"], "%Y-%m-%d").date()
                prices = {symbol: float(raw[symbol]) for symbol in symbols}
            except (ValueError, TypeError) as error:
                raise ValueError(f"第 {line} 行日期或价格无法转换：{error}") from error
            if any(not math.isfinite(p) or p <= 0 for p in prices.values()):
                raise ValueError(f"第 {line} 行价格必须为有限正数")
            if rows and day <= rows[-1]["date"]:
                raise ValueError(f"第 {line} 行日期重复或未按升序排列")
            rows.append({"date": day, "prices": prices})
    if not rows:
        raise ValueError("CSV 没有数据")
    return rows
