# Python 3.6 迁移与打开说明

## 新项目位置

`C:\Users\86198\Desktop\量化\momentum_strategy_py36`

原来的 momentum_strategy 不变。新目录已包含兼容 Python 3.6 的代码、数据、测试、结果、说明和原始参考包。

## 本机两套 Python 3.6

| 用途 | 实际版本 | 解释器路径 |
|---|---|---|
| 首选，满足 Anaconda 环境要求 | Python 3.6.13 | C:\Users\86198\anaconda3\envs\myEnvironment\python.exe |
| 备用，本机独立安装版 | Python 3.6.8 | C:\Users\86198\AppData\Local\Programs\Python\Python36\python.exe |

两个版本均已实际运行回测与 16 项逻辑测试。正式运行日志使用 Anaconda 的 3.6.13；双版本核验见 outputs/python36_compatibility.json。

## 最简单的打开和运行方法

双击项目根目录的 run_python36.bat。它会优先选择上表的 Anaconda 解释器，检查版本确实为 3.6，然后运行 main.py；找不到主解释器时，尝试本机独立 3.6.8。不会使用 PATH 中不确定的 python，也不会静默切到新版 Python。

双击 test_python36.bat 可重跑默认回测、16 项测试和三个成本情景。双击 outputs/report.html 查看报告。启动文件只适用于当前电脑已知路径；换电脑需修改启动文件中的 PYTHON36 路径，或在新电脑的 Anaconda 环境中直接运行 main.py。

## 在中文版 PyCharm 中打开

1. 文件 → 打开，选择 momentum_strategy_py36 文件夹。
2. 文件 → 设置，搜索“Python 解释器”。
3. 添加解释器 → 添加本地解释器 → 使用现有环境；按界面选择 Conda 或已有解释器。
4. 选择 `C:\Users\86198\anaconda3\envs\myEnvironment\python.exe`，不要选择原项目的 .conda_env，也不要新建一个默认新版环境。
5. 如果要求 Conda 路径，选择 `C:\Users\86198\anaconda3\Scripts\conda.exe`。它是环境管理程序，不是解释器。若该 exe 在本机报启动错误，可直接通过已有本地解释器选择上面的 python.exe，不需要重新创建环境。
6. 应用并确定，右键 main.py → 运行或调试。运行配置的解释器也应是项目的 Python 3.6。

PyCharm 的解释器选择属于 IDE 项目设置，本次没有改写你现有 PyCharm 全局配置。仅打开 .py 文件不会自动更改 IDE 的解释器，必须核对上面的选择。

## 兼容性改动

| 原调用 | Python 3.6 写法 | 原因 |
|---|---|---|
| date.fromisoformat | datetime.strptime(..., "%Y-%m-%d").date() | fromisoformat 在 3.6 不可用 |
| math.prod | functools.reduce 配合 operator.mul | 3.6 没有 math.prod |
| subprocess 的 capture_output / text | stdout/stderr=PIPE，universal_newlines=True | 兼容 3.6 的子进程接口 |
| PYTHONUTF8 | PYTHONIOENCODING=utf-8 | 用 3.6 支持的方式指定子进程输出编码 |
| python=3.9 环境 | python=3.6.13 | 环境定义与实际运行版本一致 |

f-string 在 Python 3.6 已经支持，保留不变。动量公式、调仓规则、交易成本和基准没有修改。

## 录屏与参考原件

新目录保留从原项目复制的 EVdebug录频.mp4。本次没有核验或改写视频内容；如它展示旧版 Python 解释器，应补录新环境及修改部分，不能把旧画面作为 Python 3.6 调试证明。

招聘要求视频通过网盘分享，因此交付 ZIP 只打包项目、数据、文档和结果，不放入该大视频。视频仍完整保存在新项目本地目录中。

references/factor-toolkit-0.1.4.zip 是第三方参考原件，要求 Python 3.10+，本次保持字节不变，不安装、不调用。新项目自有的全部可执行 Python 文件兼容 3.6；保持参考原件完整不等于将第三方工具包改成 3.6。
