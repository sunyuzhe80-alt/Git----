"""可手算的测试，不把真实样本的回测收益硬编码成正确答案。"""
import csv
from functools import reduce
from operator import mul
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from src.backtest import run_backtest, rebalance, account_value
from src.data import load_prices
from src.factor import rank_momentum
from src.metrics import performance, yearly_returns

SYMS = ('A', 'B', 'C', 'D')


def sample(matrix):
    return [{"date": date(2020, 1, 1)+timedelta(days=i), "prices": dict(zip(SYMS, values))}
            for i, values in enumerate(matrix)]


class StrategyTests(unittest.TestCase):
    def test_factor_formula_and_ties(self):
        rows = sample([[10, 10, 10, 10], [12, 12, 11, 9]])
        ranking, weights = rank_momentum(rows, 1, 1, 2, SYMS)
        self.assertEqual([r['symbol'] for r in ranking], ['A', 'B', 'C', 'D'])
        self.assertAlmostEqual(ranking[0]['momentum'], .2)
        self.assertEqual(weights, {'A': .5, 'B': .5, 'C': 0, 'D': 0})

    def test_all_negative_still_selects_two(self):
        rows = sample([[10]*4, [9, 8, 7, 6]])
        ranking, _ = rank_momentum(rows, 1, 1, 2, SYMS)
        self.assertEqual([r['symbol'] for r in ranking if r['selected']], ['A', 'B'])

    def test_signal_delay_and_first_profit(self):
        rows = sample([[1,1,1,1], [2,1,1,1], [4,1,1,1], [8,1,1,1], [16,1,1,1]])
        daily, trades, _, _ = run_backtest(rows, SYMS, 1, 5, 1, 0, 100)
        self.assertEqual(daily[0]['strategy_nav'], 1)
        self.assertEqual(daily[1]['strategy_nav'], 1)
        self.assertEqual(daily[2]['strategy_nav'], 2)
        self.assertEqual(daily[3]['strategy_nav'], 4)
        t = next(t for t in trades if t['account'] == 'strategy')
        self.assertEqual(t['signal_date'], rows[1]['date'])
        self.assertEqual(t['date'], rows[2]['date'])

    def test_buy_cost_is_self_financing(self):
        prices = dict.fromkeys(SYMS, 10.)
        weights = {'A': .5, 'B': .5, 'C': 0., 'D': 0.}
        shares, cash, fee, deltas = rebalance(dict.fromkeys(SYMS, 0.), 100., prices, weights, .01)
        self.assertAlmostEqual(account_value(shares, cash, prices), 100/1.01)
        self.assertAlmostEqual(fee, 100-100/1.01)
        self.assertGreaterEqual(cash, 0)

    def test_full_switch_pays_both_sides(self):
        prices = dict.fromkeys(SYMS, 1.)
        old = {'A':100., 'B':0., 'C':0., 'D':0.}
        weights = {'A':0., 'B':1., 'C':0., 'D':0.}
        shares, cash, fee, deltas = rebalance(old, 0, prices, weights, .01)
        self.assertAlmostEqual(shares['B'], 100*.99/1.01)
        self.assertAlmostEqual(fee, (100+shares['B'])*.01)
        self.assertLess(deltas['A'], 0)
        self.assertGreater(deltas['B'], 0)

    def test_weights_drift_between_rebalances(self):
        rows = sample([[1]*4, [2,1,1,1], [2,1,1,1], [4,1,1,1], [4,1,1,1]])
        daily, _, _, _ = run_backtest(rows, SYMS, 1, 10, 2, 0, 100)
        self.assertAlmostEqual(daily[1]['A_weight'], .5)
        self.assertAlmostEqual(daily[2]['A_weight'], 2/3)
        self.assertEqual(daily[1]['A_units'], daily[2]['A_units'])
        self.assertEqual(daily[2]['rebalance'], 0)

    def test_fixed_rebalance_schedule(self):
        rows = sample([[1+i, 2, 3, 4] for i in range(12)])
        _, _, ranks, rebalances = run_backtest(rows, SYMS, 2, 3, 2, 0)
        self.assertEqual([r['execution_date'] for r in rebalances], [rows[i]['date'] for i in [3,6,9]])
        self.assertEqual(len(ranks), 16)  # 最后一天有信号，但没有下一日可成交。
        self.assertEqual(ranks[-1]['planned_execution_date'], '')

    def test_future_changes_do_not_change_past(self):
        a = sample([[1+i, 2, 3, 4] for i in range(12)])
        b = sample([[1+i, 2, 3, 4] if i < 8 else [100, 90, 80, 70] for i in range(12)])
        x = run_backtest(a, SYMS, 2, 3, 2, .001)
        y = run_backtest(b, SYMS, 2, 3, 2, .001)
        self.assertEqual(x[0][:6], y[0][:6])
        cutoff = a[7]['date']
        self.assertEqual([r for r in x[2] if r['signal_date'] <= cutoff], [r for r in y[2] if r['signal_date'] <= cutoff])

    def test_benchmark_matches_independent_formula(self):
        rows = sample([[1+i, 2+i, 3+i, 4+i] for i in range(10)])
        daily, trades, _, _ = run_backtest(rows, SYMS, 2, 3, 2, .001, 100)
        entry = rows[3]['prices']
        final = rows[-1]['prices']
        expected = sum(final[s]/entry[s] for s in SYMS)/4/1.001
        self.assertAlmostEqual(daily[-1]['benchmark_nav'], expected)
        self.assertEqual(sum(t['account'] == 'benchmark' for t in trades), 4)

    def test_accounting_identity_each_day(self):
        rows = sample([[1+i, 2+i*.1, 3+(i%3), 4+i*.2] for i in range(25)])
        daily, trades, _, rebalances = run_backtest(rows, SYMS, 2, 3, 2, .003, 100)
        previous = 100
        for r in daily:
            self.assertAlmostEqual(r['strategy_value'], previous+r['market_pnl']-r['strategy_fee'])
            self.assertAlmostEqual(sum(r[s+'_units']*r[s+'_price'] for s in SYMS)+r['cash'], r['strategy_value'])
            self.assertGreaterEqual(r['cash'], 0)
            previous = r['strategy_value']
        self.assertAlmostEqual(sum(r['strategy_fee'] for r in daily), sum(t['fee'] for t in trades if t['account']=='strategy'))
        self.assertAlmostEqual(sum(r['strategy_fee'] for r in daily), sum(r['fee'] for r in rebalances))

    def test_drawdown_includes_initial_nav(self):
        records = [{'strategy_nav':1., 'strategy_return':0.}, {'strategy_nav':.8, 'strategy_return':-.2}, {'strategy_nav':.9, 'strategy_return':.125}]
        self.assertAlmostEqual(performance(records, 'strategy')['max_drawdown'], .2)

    def test_flat_zero_cost_has_undefined_sharpe(self):
        daily, _, _, _ = run_backtest(sample([[1]*4]*10), SYMS, 2, 3, 2, 0)
        self.assertEqual(performance(daily, 'strategy')['total_return'], 0)
        self.assertIsNone(performance(daily, 'strategy')['sharpe'])

    def test_yearly_compounding_matches_final_nav(self):
        daily, _, _, _ = run_backtest(sample([[1+i, 2, 3, 4] for i in range(25)]), SYMS, 2, 3, 2, .001)
        years = yearly_returns(daily)
        self.assertAlmostEqual(reduce(mul, (1+r['strategy_return'] for r in years), 1.0), daily[-1]['strategy_nav'])

    def test_rejects_invalid_parameters(self):
        rows = sample([[1]*4]*10)
        for kwargs in [{'lookback':0}, {'interval':0}, {'top_n':5}, {'cost':float('nan')}, {'cost':-1}, {'capital':float('inf')}, {'lookback':2.5}]:
            with self.assertRaises(ValueError):
                run_backtest(rows, SYMS, **kwargs)

    def test_rejects_insufficient_data(self):
        with self.assertRaises(ValueError):
            run_backtest(sample([[1]*4]*5), SYMS, 3)

    def test_invalid_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bad.csv'
            cases = ['Date,AAPL\n2020-01-01,1\n',
                     'Date,AAPL,IBM,MSFT,SBUX\n2020-01-01,1,1,-1,1\n',
                     'Date,AAPL,IBM,MSFT,SBUX\n2020-01-01,1,1,1,1\n2020-01-01,1,1,1,1\n',
                     'Date,AAPL,IBM,MSFT,SBUX\n2020-01-01,1,,1,1\n',
                     'Date,AAPL,IBM,MSFT,SBUX\n2020-01-01,1,nan,1,1\n']
            for text in cases:
                path.write_text(text, encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_prices(path)


if __name__ == '__main__':
    unittest.main()
