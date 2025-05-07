import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import rcParams
import matplotlib.font_manager as fm
import time
import platform
    
# 查找系统可用字体
font_list = fm.findSystemFonts(fontpaths=None, fontext='ttf')
chinese_fonts = [f for f in font_list if any(c in f.lower() for c in ['simhei', 'msyh', 'arialuni', 'wqy'])]

if chinese_fonts:
    # 使用找到的第一个中文字体
    plt.rcParams['font.sans-serif'] = [fm.FontProperties(fname=chinese_fonts[0]).get_name()]
    print(f"使用字体: {chinese_fonts[0]}")
else:
    # 如果没有找到中文字体，使用英文显示
    plt.rcParams['font.sans-serif'] = ['Arial']
    print("未找到中文字体，将使用英文显示")

# 解决负号显示问题
plt.rcParams['axes.unicode_minus'] = False

# 设置图形显示方式
# 对于GUI环境（如Jupyter Notebook、IDE等）
plt.switch_backend('TkAgg')  # 或者 'Qt5Agg'

# 对于命令行环境
# plt.switch_backend('Agg')  # 使用这个如果只需要保存图片而不显示

# 对于macOS系统，使用以下后端
plt.switch_backend('MacOSX')

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

# 1. 定义要分析的科技股票列表
tech_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'INTC', 'AMD', 'CRM']

try:
    # 2. 分别获取每个股票的数据
    data_dict = {}
    for stock in tech_stocks:
        print(f"正在获取 {stock} 的数据...")
        stock_data = yf.download(stock, period='5y', progress=False)
        if not stock_data.empty:
            data_dict[stock] = stock_data
            print(f"{stock}: 获取成功，{len(stock_data)} 条数据")
        else:
            print(f"{stock}: 获取失败")
    
    if not data_dict:
        raise ValueError("未能获取任何股票数据")
    
    # 检查数据列名
    for stock, stock_data in data_dict.items():
        print(f"{stock} 数据列名: {stock_data.columns}")

    # 3. 计算每日收益率
    returns = pd.DataFrame()
    for stock, stock_data in data_dict.items():
        # 使用 'Close' 列而不是 'Adj Close'
        returns[stock] = stock_data['Close'].pct_change()
    
    # 4. 计算累计收益率
    cumulative_returns = (1 + returns).cumprod()
    
    # 5. 添加技术指标计算
    def calculate_technical_indicators(stock_data):
        result = pd.DataFrame()
        # 使用 'Close' 列而不是 'Adj Close'
        result['Close'] = stock_data['Close']
        result['Volume'] = stock_data['Volume']
        result['MA20'] = stock_data['Close'].rolling(window=20).mean()
        result['MA50'] = stock_data['Close'].rolling(window=50).mean()
        
        # 计算RSI
        delta = stock_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        result['RSI'] = 100 - (100 / (1 + rs))
        
        # 添加MACD指标
        exp1 = stock_data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = stock_data['Close'].ewm(span=26, adjust=False).mean()
        result['MACD'] = exp1 - exp2
        result['Signal Line'] = result['MACD'].ewm(span=9, adjust=False).mean()
        
        return result

    # 计算技术指标
    technical_data = {stock: calculate_technical_indicators(data) 
                     for stock, data in data_dict.items()}

    # 计算投资组合分析
    weights = np.array([1/len(tech_stocks)] * len(tech_stocks))
    portfolio_returns = returns.mean(axis=1)
    portfolio_cumulative = (1 + portfolio_returns).cumprod()
    
    # 计算投资组合风险指标
    portfolio_volatility = returns.std().mean() * np.sqrt(252) * 100
    risk_free_rate = 0.02  # 假设无风险利率为2%
    portfolio_sharpe = (portfolio_returns.mean() * 252 - risk_free_rate) / (portfolio_returns.std() * np.sqrt(252))

    # 添加新的可视化：技术指标展示
    plt.figure(figsize=(15, 10))
    plt.subplot(2, 1, 1)
    for stock in tech_stocks[:3]:  # 展示前三只股票的技术指标
        plt.plot(technical_data[stock].index, technical_data[stock]['Close'], label=f'{stock} 价格')  # 修改为 'Close'
        plt.plot(technical_data[stock].index, technical_data[stock]['MA20'], label=f'{stock} MA20')
        plt.plot(technical_data[stock].index, technical_data[stock]['MA50'], label=f'{stock} MA50')
    plt.title('主要科技股票价格和移动平均线')
    plt.legend()
    plt.grid(True)

    plt.subplot(2, 1, 2)
    for stock in tech_stocks[:3]:
        plt.plot(technical_data[stock].index, technical_data[stock]['RSI'], label=f'{stock} RSI')
    plt.axhline(y=70, color='r', linestyle='--')
    plt.axhline(y=30, color='g', linestyle='--')
    plt.title('RSI指标')
    plt.legend()
    plt.grid(True)
    plt.savefig('output_technical_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 输出增强版统计信息
    print("\n=== 投资组合分析 ===")
    print(f"投资组合年化收益率: {(portfolio_cumulative.iloc[-1]**(252/len(portfolio_cumulative))-1)*100:.2f}%")
    print(f"投资组合波动率: {portfolio_volatility:.2f}%")
    print(f"投资组合夏普比率: {portfolio_sharpe:.2f}")

    # ... 保持原有的其他分析和可视化 ...

except Exception as e:
    print(f"错误：{str(e)}")
    print("建议：")
    print("1. 检查网络连接是否正常")
    print("2. 尝试使用VPN连接")
    print("3. 稍后再试，可能是Yahoo Finance服务器问题")
    exit(1)

# 5. 可视化分析
plt.figure(figsize=(14, 8))
for stock in tech_stocks:
    plt.plot(cumulative_returns[stock], label=stock)

plt.title('过去5年热门科技股票累计收益率')
plt.xlabel('日期')
plt.ylabel('累计收益率')
plt.legend()
plt.grid(True)
plt.savefig(f'output_cumulative_returns.png', dpi=300, bbox_inches='tight')
plt.show()

# 6. 输出统计信息
print("过去5年各股票总收益率：")
print((cumulative_returns.iloc[-1] - 1) * 100)

# 7. 计算年化收益率
days = len(cumulative_returns)
annualized_returns = (cumulative_returns.iloc[-1] ** (252/days) - 1) * 100
print("\n年化收益率：")
print(annualized_returns)

# 8. 计算波动率（风险）
volatility = returns.std() * np.sqrt(252) * 100
print("\n年化波动率：")
print(volatility)

# 9. 计算夏普比率（风险调整后收益）
risk_free_rate = 0.02  # 假设无风险利率为2%
sharpe_ratios = (annualized_returns - risk_free_rate) / volatility
print("\n夏普比率：")
print(sharpe_ratios)

# 10. 相关性分析
correlation_matrix = returns.corr()
print("\n股票收益率相关性矩阵：")
print(correlation_matrix)

# 11. 绘制相关性热力图
plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm')
plt.title('股票收益率相关性热力图')
plt.savefig(f'output_correlation_matrix.png', dpi=300, bbox_inches='tight')
plt.show()

# 12. 绘制风险收益散点图
plt.figure(figsize=(10, 8))
plt.scatter(volatility, annualized_returns, s=100)

# 添加标注
for i, txt in enumerate(tech_stocks):
    plt.annotate(txt, (volatility[i], annualized_returns[i]), 
                 xytext=(10,0), textcoords='offset points')

plt.title('风险-收益分析')
plt.xlabel('年化波动率 (%)')
plt.ylabel('年化收益率 (%)')
plt.grid(True)
plt.savefig(f'output_risk_return_analysis.png', dpi=300, bbox_inches='tight')
plt.show()

# 13. 最大回撤分析
max_drawdown = pd.DataFrame()
for stock, stock_data in data_dict.items():
    rolling_max = stock_data['Close'].cummax()  # 修改为 'Close'
    daily_drawdown = stock_data['Close']/rolling_max - 1.0  # 修改为 'Close'
    max_drawdown[stock] = daily_drawdown.cummin()

plt.figure(figsize=(14, 8))
for stock in tech_stocks:
    plt.plot(max_drawdown[stock], label=stock)

plt.title('最大回撤分析')
plt.xlabel('日期')
plt.ylabel('回撤幅度')
plt.legend()
plt.grid(True)
plt.savefig(f'output_max_drawdown.png', dpi=300, bbox_inches='tight')
plt.show()

# 删除重复的代码和测试代码
data = yf.download('AAPL', period='5y')
print(data.head())
