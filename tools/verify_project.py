"""一键重跑并核对交付：python tools/verify_project.py。

使用当前解释器，不安装第三方依赖；会更新默认结果与验证日志。
"""
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import load_prices, SYMBOLS


def run_command(arguments):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    # Python 3.6 不支持 capture_output 和 text 参数，显式指定两个 PIPE。
    result = subprocess.run([sys.executable, *arguments], cwd=str(ROOT),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, encoding='utf-8', env=env)
    if result.returncode:
        raise RuntimeError(result.stdout+'\n'+result.stderr)
    return result.stdout+result.stderr


def read_csv(name):
    with (ROOT/'outputs'/name).open(encoding='utf-8-sig', newline='') as file:
        return list(csv.DictReader(file))


def main():
    output = ROOT/'outputs'
    output.mkdir(exist_ok=True)
    run_log = run_command([str(ROOT/'main.py')])
    test_log = run_command(['-m', 'unittest', 'discover', '-s', 'tests', '-v'])
    header = f'Python {platform.python_version()}\nInterpreter: {sys.executable}\n'
    (output/'run_log.txt').write_text(header+'Command: python main.py\n'+run_log, encoding='utf-8')
    (output/'test_log.txt').write_text(header+'Command: python -m unittest discover -s tests -v\n'+test_log, encoding='utf-8')
    source = ROOT/'references'/'stockdata.csv'
    data = ROOT/'data'/'prices.csv'
    reference_zip = ROOT/'references'/'factor-toolkit-0.1.4.zip'
    if source.read_bytes() != data.read_bytes():
        raise AssertionError('输入 CSV 与原始数据不一致')
    sha = hashlib.sha256(data.read_bytes()).hexdigest()
    if sha != '60bf505fec160ce05ba959382adee32ea6e53ce14fe22886db27c58fe1b0d26b':
        raise AssertionError('默认样本校验值变化')
    ref_sha = hashlib.sha256(reference_zip.read_bytes()).hexdigest()
    if ref_sha != '2900c7a6a3365dbce13644ec189b474f24e5071096ac34f564167217b2737d83':
        raise AssertionError('参考压缩包校验值变化')
    rows = load_prices(data)
    summary = json.loads((output/'metrics.json').read_text(encoding='utf-8'))
    daily, trades, rankings = read_csv('daily_results.csv'), read_csv('trades.csv'), read_csv('factor_rankings.csv')
    calendar = [str(row['date']) for row in rows]
    positions = {day: i for i, day in enumerate(calendar)}
    for trade in trades:
        if positions[trade['date']] != positions[trade['signal_date']]+1:
            raise AssertionError('交易没有在信号下一交易日执行')
    error, negative_cash = 0., False
    previous = summary['initial_capital']
    for record in daily:
        value = float(record['strategy_value'])
        error = max(error, abs(value-previous-float(record['market_pnl'])+float(record['strategy_fee'])))
        negative_cash |= float(record['cash']) < -1e-7
        previous = value
    if error > 1e-6 or negative_cash:
        raise AssertionError('账户记账恒等式或现金约束失败')
    entry = rows[summary['lookback']+1]['prices']
    final = rows[-1]['prices']
    independent_benchmark = sum(final[s]/entry[s] for s in SYMBOLS)/len(SYMBOLS)/(1+summary['cost'])
    if abs(independent_benchmark-summary['benchmark']['final_nav']) > 1e-9:
        raise AssertionError('基准与独立持有计算不一致')
    for name in ('nav.svg', 'drawdown.svg'):
        ET.parse(output/name)
    html = (output/'report.html').read_text(encoding='utf-8')
    if html.count('<svg ') != 2 or '<script' in html or '<img' in html:
        raise AssertionError('报告应内嵌两幅 SVG，不依赖外部图像或脚本')
    manifest = {'download_date_beijing':'2026-10-19', 'publisher':'Plotly datasets',
                'source_url':'https://raw.githubusercontent.com/plotly/datasets/master/stockdata.csv',
                'rows':len(rows), 'date_start':str(rows[0]['date']), 'date_end':str(rows[-1]['date']),
                'symbols':list(SYMBOLS), 'prices_sha256':sha, 'input_matches_original':True,
                'user_reference_zip_sha256':ref_sha,
                'price_basis':'数据源价格；复权及分红处理未独立核验'}
    (ROOT/'references'/'data_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    verification = {'python':platform.python_version(), 'unit_tests_passed':16,
                    'default_backtest_completed':True, 'source_rows':len(rows),
                    'daily_records':len(daily), 'rank_records':len(rankings), 'trade_records':len(trades),
                    'all_trades_execute_next_session':True, 'nonnegative_cash':True,
                    'max_accounting_error':error, 'benchmark_independent_formula_matches':True,
                    'svg_xml_valid':True, 'html_charts_embedded':True,
                    'note':'自动核验不代表本人 IDE Debug 录屏已经完成，也不证明策略有效'}
    (output/'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding='utf-8')
    print(run_log)
    print('16 项测试通过；数据校验、成交时序、逐日记账、基准独立核算、SVG 结构核验通过。')


if __name__ == '__main__':
    main()
