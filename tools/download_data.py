"""可选取数工具，正常回测不调用。下载失败不使用随机数据替代。

用法：在项目目录运行 python tools/download_data.py，需要联网。
源文件若变化，SHA256 不一致则停止，不覆盖随项目固定的样本。
"""
import hashlib
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://raw.githubusercontent.com/plotly/datasets/master/stockdata.csv'
EXPECTED = '60bf505fec160ce05ba959382adee32ea6e53ce14fe22886db27c58fe1b0d26b'


def main():
    try:
        with urlopen(URL, timeout=30) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != EXPECTED:
            raise ValueError('远端数据已变化，未覆盖固定样本；请先人工核对来源和版本')
        (ROOT/'references'/'stockdata.csv').write_bytes(content)
        (ROOT/'data'/'prices.csv').write_bytes(content)
    except (URLError, OSError, ValueError) as error:
        raise SystemExit(f'下载失败：{error}。可直接使用项目附带的数据运行 main.py。')
    print('数据下载成功，与项目固定样本一致。')


if __name__ == '__main__':
    main()
