# TickFlow Python SDK

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg?style=flat)](https://pypi.org/project/tickflow/)
[![PyPI Package](https://img.shields.io/pypi/v/tickflow.svg?maxAge=60)](https://pypi.org/project/tickflow/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/tickflow.svg?maxAge=2592000&label=downloads&color=%2327B1FF)](https://pypi.org/project/tickflow/)
[![Docs](https://img.shields.io/badge/docs-docs.tickflow.org-blue)](https://docs.tickflow.org)
[![GitHub Stars](https://img.shields.io/github/stars/tickflow-org/tickflow.svg?style=social&label=Star&maxAge=60)](https://github.com/tickflow-org/tickflow)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

TickFlow Python SDK 是 TickFlow 行情数据 API 的官方 Python 客户端，支持 A 股、ETF、美股、港股、国内期货等。

> **完整文档**：<https://docs.tickflow.org>

---

## 安装

使用 pip 安装 TickFlow Python SDK：

```bash
pip install "tickflow[all]" --upgrade
```

如不需要 DataFrame 支持和进度条功能，可安装基本版：

```bash
pip install tickflow
```

SDK 支持 Python 3.9+，推荐使用 Python 3.10 或更高版本。

---

## 初始化客户端

### 免费服务（无需注册）

如果你只需要日K线数据和标的信息（不需要实时行情和分钟K线），可以直接使用免费服务：

```python
from tickflow import TickFlow

# 使用免费服务（无需 API key）
tf = TickFlow.free()

# 查询日K线数据
df = tf.klines.get("600000.SH", period="1d", count=100, as_dataframe=True)
print(df.tail())

# 查询标的信息
instruments = tf.instruments.batch(symbols=["600000.SH", "000001.SZ"])
print(instruments)
```

**免费服务特点：**
- ✅ 无需注册，直接使用
- ✅ 提供历史日K线数据（1d、1w、1M、1Q、1Y）
- ✅ 提供标的信息、交易所、标的池查询
- ❌ 不提供实时行情
- ❌ 不提供分钟级K线（1m、5m、15m、30m、60m）
- ⚠️ 日K数据为历史数据，盘中不会实时更新

如果你需要实时行情、盘中实时更新的K线或更高频率访问，请使用完整服务。

---

### 完整服务（需注册）

### 1. 获取 API Key

访问 [tickflow.org](https://tickflow.org) 登录后，在控制台一键生成你的 API Key。

### 2. 配置认证

**方式一：直接传入**

```python
from tickflow import TickFlow

tf = TickFlow(api_key="your-api-key")
```

**方式二：Windows 环境变量(PowerShell)**

```powershell
$env:TICKFLOW_API_KEY="your-api-key"
```

**方式二：Windows 环境变量(CMD)**

```cmd
set TICKFLOW_API_KEY=your-api-key
```

```python
from tickflow import TickFlow

tf = TickFlow()  # 自动读取环境变量
```

**方式三：Linux/Mac 环境变量**

```bash
export TICKFLOW_API_KEY="your-api-key"
```

```python
from tickflow import TickFlow

tf = TickFlow()  # 自动读取 TICKFLOW_API_KEY 环境变量
```

### 3. 发起第一个请求

```python
from tickflow import TickFlow

# 使用完整服务（需要 API key）
tf = TickFlow(api_key="your-api-key")

# 获取沪深 A 股实时行情
quotes = tf.quotes.get(symbols=["600000.SH", "000001.SZ"])

for q in quotes:
    print(f"{q['symbol']}: {q['last_price']}")
```

如果看到股票价格输出，说明 SDK 已配置成功！

**完整服务优势：**
- ✅ 实时行情数据
- ✅ 分钟级K线（5m、15m、30m、60m）
- ✅ 日内分时数据
- ✅ 更高的调用频率

---

## 标的代码格式与支持市场

所有按标的查询的接口（行情、K 线等）均使用**统一标的代码**，格式为：**`代码.市场后缀`**（中间为英文点号）。

### 标的代码格式

- 格式：`代码.市场后缀`
- 示例：
  - 股票：`600000.SH`（浦发银行）、`000001.SZ`（平安银行）、`920662.BJ`（方盛股份）
  - ETF：`510300.SH`（沪深 300 ETF）、`159915.SZ`（创业板 ETF）
  - 指数：`000001.SH`（上证指数）、`399006.SZ`（创业板指数）
  - 期货：`au2604.SHF`（上期所黄金主力合约）、`i2605.DCE`（大商所铁矿石主力合约）等

代码部分使用交易所官方代码（如 6 位 A 股代码、合约代码等），**市场后缀**见下表。

### 支持的市场（后缀）

| 后缀 | 市场 | 说明 |
|------|------|------|
| **SH** | 上海证券交易所 | 沪市 A 股、ETF、债券等 |
| **SZ** | 深圳证券交易所 | 深市 A 股、创业板、ETF 等 |
| **BJ** | 北京证券交易所 | 北交所股票 |
| **SHF** | 上海期货交易所 | 上期所期货 |
| **DCE** | 大连商品交易所 | 大商所期货 |
| **ZCE** | 郑州商品交易所 | 郑商所期货 |
| **CFX** | 中国金融期货交易所 | 中金所股指/国债期货 |
| **INE** | 上海国际能源交易中心 | 原油等期货 |
| **GFE** | 广州期货交易所 | 广期所期货 |
| **US** | 美股 | 美国证券市场 |
| **HK** | 港股 | 香港联交所 |

### 目前支持状态

- **A 股（SH / SZ / BJ）**：已支持。可查实时行情、日 K、分钟 K、日内分时、财务数据、标的池（如 `CN_Equity_A`）等。
- **国内期货（SHF / DCE / ZCE / CFX / INE / GFE）**：支持主力合约查询。按合约代码 + 后缀查询（如 `au2604.SHF`）。
- **美股（US）**：已支持。实时行情、全量历史日 K 线（支持前复权/后复权）、除权因子、标的池（`US_Equity`）。
- **港股（HK）**：已支持。实时行情、全量历史日 K 线（支持前复权/后复权）、除权因子、标的池（`HK_Equity`）。

按标的查询时传入上述格式的字符串或列表即可：

```python
from tickflow import TickFlow

tf = TickFlow(api_key="your-api-key")

symbols = [
    "600000.SH",   # 沪市
    "000001.SZ",   # 深市
    "AAPL.US",     # 美股
    "00700.HK",    # 港股
]
quotes = tf.quotes.get(symbols=symbols, as_dataframe=True)
print(quotes)
```

---

## 基础用法

### K 线获取

单次单标的最多获取 10000 根 K 线。

**非批量**：单只标的日 K、周 K 等，使用 `tf.klines.get(symbol, ...)`：

```python
from tickflow import TickFlow

tf = TickFlow(api_key="your-api-key")

# 获取日 K 线，返回原始数据
klines = tf.klines.get("600000.SH", period="1d", count=10000)
print(f"最新收盘价: {klines['close'][-1]}")

# 获取日 K 线，返回 DataFrame（需安装 pandas）
df = tf.klines.get("600000.SH", period="1d", count=10000, as_dataframe=True)
print(df.tail(5))
```

**批量**：多只标的一次性拉取，使用 `tf.klines.batch(symbols, ...)`，适合大量标的：

```python
from tickflow import TickFlow

tf = TickFlow(api_key="your-api-key")

symbols = ["600000.SH", "000001.SZ", "600519.SH"]
dfs = tf.klines.batch(symbols, period="1d", count=10000, as_dataframe=True, show_progress=True)
print(list(dfs.keys()))
print(dfs["600000.SH"].tail())
```

### 日内分时

当日分钟 K 线（1 分钟、5 分钟等），按单只或批量调用。

**非批量**：单只标的当日分钟线，使用 `tf.klines.intraday(symbol, ...)`：

```python
from tickflow import TickFlow

tf = TickFlow(api_key="your-api-key")

# 获取当日 1 分钟 K 线
df = tf.klines.intraday("600000.SH", as_dataframe=True)
print(f"今日已有 {len(df)} 根分钟 K 线")
print(df.tail())

# 指定 count 参数，获取当日最新 1 根分钟 K 线
df_last = tf.klines.intraday("600000.SH", as_dataframe=True, count=1)
print(df_last.tail())

# 获取当日 5 分钟 K 线
df_5m = tf.klines.intraday("600000.SH", period="5m", as_dataframe=True)
print(df_5m.tail())
```

**批量**：多只标的当日分钟线，使用 `tf.klines.intraday_batch(symbols, ...)`：

```python
from tickflow import TickFlow

tf = TickFlow(api_key="your-api-key")

symbols = ["600000.SH", "000001.SZ", "600519.SH"]
dfs = tf.klines.intraday_batch(symbols, as_dataframe=True, show_progress=True)
print(f"成功获取 {len(dfs)} 只股票的日内数据")
print(dfs["600000.SH"].tail())
```

### 获取实时行情

**按标的代码查询**

```python
quotes = tf.quotes.get(symbols=["600000.SH", "000001.SZ"], as_dataframe=True)
print(quotes)
```

**按标的池查询**

```python
# 获取全部 A 股行情
quotes_a = tf.quotes.get(universes=["CN_Equity_A"], as_dataframe=True)
print(quotes_a)

# 获取全部沪深 ETF 行情
quotes_etf = tf.quotes.get(universes=["CN_ETF"], as_dataframe=True)
print(quotes_etf)
```

---

## 异步使用

对于高并发场景，使用异步客户端：

**免费服务：**

```python
import asyncio
from tickflow import AsyncTickFlow

async def main():
    # 使用免费服务（无需 API key）
    async with AsyncTickFlow.free() as tf:
        df = await tf.klines.get("600000.SH", period="1d", as_dataframe=True)
        print(df.tail())

asyncio.run(main())
```

**完整服务：**

```python
import asyncio
from tickflow import AsyncTickFlow

async def main():
    async with AsyncTickFlow(api_key="your-api-key") as tf:
        df = await tf.klines.get("600000.SH", as_dataframe=True)
        print(df.tail())
        
        # 并发获取多只股票（如需大量获取 K 线数据，请使用 tf.klines.batch）
        tasks = [
            tf.klines.get(s, as_dataframe=True)
            for s in ["600000.SH", "000001.SZ"]
        ]
        results = await asyncio.gather(*tasks)

asyncio.run(main())
```

---

## 更多文档

- [完整示例](https://docs.tickflow.org/zh-Hans/sdk/python-examples) — 查看更多使用场景和代码示例
- [最佳实践](https://docs.tickflow.org/zh-Hans/sdk/python-best-practices) — 了解生产环境的最佳实践
- [API 参考](https://docs.tickflow.org/zh-Hans/api-reference/introduction) — HTTP API 接口说明

---

## License

MIT
