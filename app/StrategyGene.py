class StrategyGene:
    def __init__(self, buy_condition, sell_condition, weight):
        self.buy_condition = buy_condition  # 例如："cross(ema12, ema26)"
        self.sell_condition = sell_condition 
        self.weight = weight  # 在组合中的表达权重

    def apply(self, dataframe):
        # 将基因表达式转化为实际交易信号
        dataframe.loc[eval(self.buy_condition), 'buy'] += self.weight
