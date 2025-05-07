import yfinance as yf
# ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META']
data = yf.download('AAPL', period='5y')
data1 = yf.download('MSFT', period='5y')
data2 = yf.download('GOOGL', period='5y')
data3 = yf.download('AMZN', period='5y')
data4 = yf.download('TSLA', period='5y')
data5 = yf.download('NVDA', period='5y')
data6 = yf.download('META', period='5y')

print(data.head())
print(data1.head())
print(data2.head())
print(data3.head())
print(data4.head())
print(data5.head())
print(data6.head())
