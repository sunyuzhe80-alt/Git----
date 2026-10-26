# 实习生测试一：简单动量因子选股与回测（Python 3.6 版）

本项目已迁移到 Python 3.6，另存于 momentum_strategy_py36，原项目保留。最快运行方式：双击 `run_python36.bat`；完整检查：双击 `test_python36.bat`。两个启动文件优先使用本机 Anaconda 的 myEnvironment（Python 3.6.13），必要时回退到独立安装的 Python 3.6.8，均检查版本。

PyCharm 请打开此新文件夹，并将项目解释器设为 `C:\Users\86198\anaconda3\envs\myEnvironment\python.exe`。具体设置和版本改动见 `docs/05_Python36迁移与打开说明.md`。

**一句话：给四只股票按过去 20 个交易日的涨跌幅排名，每隔 5 个交易日选前两只，下一交易日收盘等权买入。**

本项目参考用户提供的 factor-toolkit-0.1.4 的“因子打分—排名—评价”研究流程，独立实现易读的动量选股和交易回测。原工具包示例是合成数据上的短期反转，本项目是公开历史样本上的动量策略。两者的区别、来源原件和 AI 辅助说明均已附上。

## 先看什么

1. 双击 `outputs/report.html` 看净值、回撤、指标和年度结果，不用启动服务器。
2. 阅读 `docs/01_策略与研究说明.md`，理解买卖规则和结论。
3. 阅读 `docs/02_代码与字段讲解.md`，对照带中文注释的代码学习。
4. 按 `docs/03_PyCharm调试与录屏.md` 实际调试并录制，最后核对提交清单。

## Anaconda 创建环境并运行

在 Anaconda Prompt 中进入项目文件夹，依次执行：

```text
conda env create -f environment.yml
conda activate momentum_py36
python main.py
python -m unittest discover -s tests -v
```

项目仅使用 Python 标准库，无须安装 pandas、Polars、NumPy 或绘图库。`requirements.txt` 说明第三方依赖为空，不需要安装参考工具包。

当前电脑也可以直接使用已验证的 Anaconda 环境：

```text
conda activate "C:\Users\86198\anaconda3\envs\myEnvironment"
cd /d "C:\Users\86198\Desktop\量化\momentum_strategy_py36"
python main.py
```

上面 `cd /d` 适用于 Windows Anaconda Prompt；如果使用 PowerShell，请改用 `Set-Location`。首次创建环境可能需要联网，项目本身运行完全离线。换电脑时重建环境，不复制本机环境文件夹。

## 输入、参数和输出

默认输入：`data/prices.csv`。必要列为 `Date,AAPL,IBM,MSFT,SBUX`；数据按日期升序，价格为有限正数，不能缺失。原始文件中还有 GSPC 指数列，本策略不使用。只支持本项目四只股票的列定义，不声称是任意股票通用取数接口。

默认参数：20 日回看、每 5 个交易日调仓、选前 2 只、单边成本 0.1%、初始资金 100000 个模型计价单位。价格口径未独立核验，因此不宣称含分红总收益，也不将这些单位解释为人民币。

```text
python main.py --lookback 20 --interval 5 --top 2 --cost 0.001 --capital 100000
python main.py --cost 0.002 --output outputs/experiment_cost_002
```

默认再次运行会覆盖默认结果。修改参数时使用新的输出目录，并如实说明实验；不要只保留表现最好的参数作为研究结论。

| 输出 | 作用 |
|---|---|
| report.html | 内嵌图表的离线报告，单独打开即可查看 |
| nav.svg / drawdown.svg | 可单独引用的净值、回撤矢量图 |
| daily_results.csv | 每日收益、资金、费用、持仓单位数与权重 |
| factor_rankings.csv | 每个信号日四股的分数、排名与目标权重 |
| trades.csv | 策略和基准的逐股交易；account 字段区分账户 |
| rebalances.csv | 每次策略调仓的时间、名单、金额和费用 |
| yearly_returns.csv | 分年度收益；首尾年份不完整 |
| metrics.json | 完整精度的指标、参数、数据校验值 |
| 结果摘要.md | 简短结果解读 |
| cost_sensitivity.csv / 成本敏感性说明.md | 固定规则下 0%、0.1%、0.2% 成本对照 |
| run_log.txt / test_log.txt / verification.json | 本次运行、测试、数据与记账核验记录 |

CSV 收益按小数存储，0.02 代表 2%；Excel 可将单元格格式设为百分比。

可选复核：`python tools/verify_project.py` 重跑默认回测和全部测试；`python tools/cost_sensitivity.py` 重建三个固定成本情景。默认运行 main.py 不自动重建这些辅助核验文件，改变参数后请勿把旧核验记录当作新实验的证明。

## 代码结构与执行顺序

```text
momentum_strategy_py36/
├─ main.py                 参数与主流程
├─ environment.yml         Anaconda 环境定义
├─ requirements.txt        依赖说明
├─ src/
│  ├─ data.py              读取、检查数据
│  ├─ factor.py            计算分数、排序、选股
│  ├─ backtest.py          账户估值、调仓和成本记账
│  ├─ metrics.py           收益、夏普、回撤、年度统计
│  └─ report.py            保存表格和离线报告
├─ data/                   默认输入行情
├─ references/             原始行情、参考压缩包、来源说明与校验值
├─ docs/                   策略、代码、调试录屏和提交清单
├─ tests/                  小样本逻辑测试
├─ tools/                  可选的重新下载及核验工具
└─ outputs/                本次完整结果
```

调用顺序：`main → load_prices → run_backtest（调用 rank_momentum / rebalance）→ performance → save_results`。

## 真实结果与完成边界

默认评价区间为 2007-02-01 至 2016-03-01。策略累计收益 **161.84%**，基准 **314.54%**；策略夏普 **0.546**，最大回撤 **62.89%**。本样本中策略跑输基准，且回撤更大。这是研究结果，不应隐藏或包装为有效策略。

代码和文档由 Codex AI 辅助编写，提交者需要亲自理解和调试。完整代码、数据、结果及参考原件已准备。原目录已有的 EVdebug录频.mp4 已完整复制到新目录，内容未核验；如展示旧版解释器，应补录 Python 3.6 环境及相关操作。本人简历、真实招聘渠道和视频分享链接需本人补充。交付 ZIP 不包含大视频，符合视频另传网盘的要求，也未代发邮件。
