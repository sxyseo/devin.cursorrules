from freqtrade.strategy import IStrategy
from pandas import DataFrame
import numpy as np

class MartingaleStrategy(IStrategy):
    # 定义策略的时间框架
    timeframe = '1h'
    
    # 定义买入和卖出条件
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 使用简单移动平均线作为趋势指标
        dataframe['sma'] = dataframe['close'].rolling(window=20).mean()
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 当价格高于移动平均线时买入
        dataframe.loc[
            (dataframe['close'] > dataframe['sma']),
            'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 当价格低于移动平均线时卖出
        dataframe.loc[
            (dataframe['close'] < dataframe['sma']),
            'sell'] = 1
        return dataframe

    def custom_stake_amount(self, **kwargs):
        # 实现马丁格尔资金管理策略
        last_trade = kwargs.get('last_trade')
        if last_trade and last_trade.is_losing:
            # 如果上次交易亏损，则加倍下注
            return last_trade.stake_amount * 2
        else:
            # 否则使用默认下注金额
            return self.wallets.get_total_stake_amount() * 0.01
