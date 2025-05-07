import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import platform

# 根据操作系统选择字体
system = platform.system()
if system == 'Darwin':  # macOS
    plt.rcParams['font.sans-serif'] = ['Alibaba PuHuiTi 2.0']  # 使用苹果系统自带的中文字体
elif system == 'Windows':
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
elif system == 'Linux':
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']  # 使用文泉驿正黑

# 确保使用系统字体
plt.rcParams['font.family'] = 'sans-serif'

# 定义要分析的加密货币列表
cryptos = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT']

# 使用ccxt获取数据
exchange = ccxt.binance()
data_dict = {}
for crypto in cryptos:
    print(f"正在获取 {crypto} 的数据...")
    ohlcv = exchange.fetch_ohlcv(crypto, timeframe='1d', since=exchange.parse8601('2018-01-01T00:00:00Z'))
    data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    data.set_index('timestamp', inplace=True)
    data_dict[crypto] = data

# 计算每日收益率
returns = pd.DataFrame({crypto: data['close'].pct_change() for crypto, data in data_dict.items()})

# 计算累计收益率
cumulative_returns = (1 + returns).cumprod()

# 绘制累计收益率曲线
plt.figure(figsize=(14, 8))
for crypto in cryptos:
    plt.plot(cumulative_returns[crypto], label=crypto)

plt.title('过去5年热门加密货币累计收益率')
plt.xlabel('日期')
plt.ylabel('累计收益率')
plt.legend()
plt.grid(True)
plt.show()

# 计算相关性矩阵
correlation_matrix = returns.corr()

# 绘制相关性热力图
plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm')
plt.title('加密货币收益率相关性热力图')
plt.show()
