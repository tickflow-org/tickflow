---
name: tickflow-stock
version: 1.0.0
description: A股/美股/港股/期货实时行情与K线数据，基于TickFlow Python SDK，支持同步和异步调用。用于获取实时报价、历史K线、日内分时、标的池行情等。
---

# TickFlow 行情数据 Skill

基于 [TickFlow Python SDK](https://github.com/tickflow-org/tickflow) 的行情数据查询工具。

## 快速安装

```bash
pip install "tickflow[all]" --upgrade
免费服务无需 API Key，直接使用：

历史日K线数据（1d、1w、1M、1Q、1Y）
标的信息查询
完整服务需要注册获得 API Key（tickflow.org），额外提供：

实时行情数据
分钟级K线（5m、15m、30m、60m）
日内分时数据
更高调用频率
标的代码格式
所有标的代码格式为 代码.市场后缀：

后缀	市场
SH	上交所（A股、ETF）
SZ	深交所（A股、创业板、ETF）
BJ	北交所
US	美股
HK	港股
SHF	上期所期货
DCE	大商所期货
ZCE	郑商所期货
CFX	中金所期货
INE	上海国际能源交易中心
GFE	广期所期货
示例：600000.SH（浦发银行）、AAPL.US（苹果）、00700.HK（腾讯）

使用方式
1. 免费服务 - 日K线 & 标的信息
python

from tickflow import TickFlow

tf = TickFlow.free()

# 获取日K线（返回DataFrame）
df = tf.klines.get("600000.SH", period="1d", count=100, as_dataframe=True)
print(df.tail())

# 批量获取多只股票K线
symbols = ["600000.SH", "000001.SZ", "600519.SH"]
dfs = tf.klines.batch(symbols, period="1d", count=10000, as_dataframe=True, show_progress=True)

# 查询标的信息
instruments = tf.instruments.batch(symbols=["600000.SH", "000001.SZ"])
print(instruments)
2. 完整服务 - 实时行情 & 分钟K线
python

from tickflow import TickFlow

tf = TickFlow(api_key="your-api-key")

# 按标的查询实时行情
quotes = tf.quotes.get(symbols=["600000.SH", "000001.SZ"], as_dataframe=True)
print(quotes)

# 按标的池查询（全部A股）
quotes_a = tf.quotes.get(universes=["CN_Equity_A"], as_dataframe=True)

# 获取日内1分钟K线
df = tf.klines.intraday("600000.SH", as_dataframe=True)

# 获取日内5分钟K线
df_5m = tf.klines.intraday("600000.SH", period="5m", as_dataframe=True)

# 批量获取多只股票日内K线
symbols = ["600000.SH", "000001.SZ", "600519.SH"]
dfs = tf.klines.intraday_batch(symbols, as_dataframe=True, show_progress=True)
3. 一次运行脚本（命令行方式）
bash

# 免费获取日K线
python3 -c "
from tickflow import TickFlow
tf = TickFlow.free()
df = tf.klines.get('600000.SH', period='1d', count=10, as_dataframe=True)
print(df.to_string())
"
4. 异步使用
python

import asyncio
from tickflow import AsyncTickFlow

async def main():
    async with AsyncTickFlow(api_key="your-api-key") as tf:
        df = await tf.klines.get("600000.SH", as_dataframe=True)
        print(df.tail())

asyncio.run(main())
5. 获取A股股本信息
python

from tickflow import TickFlow

tf = TickFlow(api_key="your-api-key")
shares = tf.financials.shares(symbol="600000.SH")
print(shares)
Shell 快速查询
bash

python3 -c "
from tickflow import TickFlow
tf = TickFlow.free()
symbol = '${SYMBOL:-600000.SH}'
df = tf.klines.get(symbol, period='1d', count=100, as_dataframe=True)
print(df.tail(10))
"
支持的标的池
CN_Equity_A — 全部A股
CN_ETF — 全部沪深ETF
US_Equity — 美股
HK_Equity — 港股
注意事项
单次单标的最多获取 10000 根K线
API Key 可通过环境变量 TICKFLOW_API_KEY 设置
需要 pandas 支持时安装 tickflow[all]
完整文档：https://docs.tickflow.org
