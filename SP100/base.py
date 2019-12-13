import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime

from SP100.src.prepare_data import sp100


class backtest(object):
    def __init__(self, test_mode=1, turnover=5, split=3, cf=5e-4):
        """
        :param turnover: 调仓时间，单位：交易日
        :param split: 将 SP100 股票池均分为若干组，交易首尾两组
        :param cf: 手续费
        """
        self.test_mode = test_mode
        self.turnover = turnover
        self.split = split
        self.cf = cf
        self.data = pd.read_csv('/Users/bob/PycharmData/sp100/stock.csv', index_col=0)
        self.ret, self.alpha = self._get_alpha()
        self.sp100 = sp100()

    def backtest(self):
        daily_ret = pd.DataFrame(columns=['long', 'short'])
        daily_ret.loc['2018-01-01'] = [0, 0]

        for i, date in enumerate(self.alpha.index):
            if i % self.turnover == 0:
                stock_list = self._get_list(date)
                alpha_list = self.alpha[stock_list].loc[date].sort_values()

                split_len = round(len(alpha_list) / self.split)
                long_list = alpha_list.index[:split_len]
                short_list = alpha_list.index[-split_len:]

            long_ret = self.ret[long_list].loc[date].mean()
            short_ret = self.ret[short_list].loc[date].mean()

            if i % self.turnover == 0:
                long_ret = (1 + long_ret) * (1 - self.cf) - 1
                short_ret = (1 + short_ret) * (1 - self.cf) - 1
            daily_ret.loc[date] = [long_ret, short_ret]

        daily_ret['hedging'] = (daily_ret.long - daily_ret.short) / 2
        portfolio = (daily_ret + 1).cumprod()

        summary = pd.DataFrame(columns=['return', 'sharpe_ratio', 'max_drawdown_ratio', 'max_drawdown_days'])
        summary.loc['long'] = self.get_summary_statistic(portfolio.long)
        summary.loc['short'] = self.get_summary_statistic(portfolio.short)
        summary.loc['hedging'] = self.get_summary_statistic(portfolio.hedging)

        return portfolio.iloc[1:], summary

    def _get_list(self, date):
        list_ = set(self.sp100.get_list(date)).intersection(set(self.data.columns))
        return list(list_)

    def _get_alpha(self):
        ret = self.data / self.data.shift(1) - 1
        if self.test_mode == 1:
            alpha = ret.shift(1)  # test1
        elif self.test_mode == 2:
            alpha = ret.rolling(21).apply(self._f, raw=True)  # test2
        else:
            raise ValueError
        alpha.dropna(inplace=True, how='all')
        return ret, alpha

    @staticmethod
    def _f(series):
        return (series[:-1] * np.arange(1, 21)).sum()

    @staticmethod
    def get_summary_statistic(df_value):
        """
        求日夏普比率、最大回撤率以及最大回撤持续时间
        :param df_value: pd.DataFrame
        :return: 最大回撤率、最大回撤持续时间
        """
        # 计算夏普比率
        ret = (df_value / df_value.shift(1) - 1).fillna(0)
        sharpe_ratio = ret.mean() / ret.std() * np.sqrt(250)
        # 计算回撤值
        value = df_value.values
        down_rate = 1 - value / np.maximum.accumulate(value)
        # 回撤期结束
        end_idx = np.argmax(down_rate)
        max_drawdown_ratio = down_rate[end_idx]
        # 回撤期开始
        begin_idx = np.argmax(value[:end_idx])
        # 计算最大回撤持续时间
        end = datetime.strptime(df_value.index[end_idx], '%Y-%m-%d')
        begin = datetime.strptime(df_value.index[begin_idx], '%Y-%m-%d')
        max_drawdown_days = (end - begin).days

        return df_value[-1] / df_value[0], sharpe_ratio, max_drawdown_ratio, max_drawdown_days


def summary(test_mode=1, index='hedging', column='sharpe_ratio'):
    """
    get the statistic summary
    :param test_mode: choose test1 / test2
    :param index: choose long / short / hedging
    :param column: choose return / sharpe_ratio / max_drawdown_ratio / max_drawdown_days
    :return: a DataFrame that contains all the results of chosen index & column
    """
    res = pd.DataFrame(columns=[1, 2, 3, 5, 7, 10, 15, 20], index=[2, 3, 4, 5])
    for turnover in [1, 2, 3, 5, 7, 10, 15, 20]:
        for split in [2, 3, 4, 5]:
            df = pd.read_csv(f'/Users/bob/PycharmData/sp100/test{test_mode}/turnover{turnover}_split{split}.csv',
                             index_col=0)
            res.loc[split, turnover] = df.loc[index, column]
    # res.to_csv('/Users/bob/PycharmData/sp100/res.csv')
    return res


if __name__ == '__main__':
    test_mode = 1

    for turnover in [1, 2, 3, 5, 7, 10, 15, 20]:
        for split in [2, 3, 4, 5]:
            bt = backtest(turnover, split)
            portfolio, summary = bt.backtest()
            portfolio.plot(figsize=(16, 8))
            plt.savefig(f'/Users/bob/PycharmData/sp100/test{test_mode}/turnover{bt.turnover}_split{bt.split}.png')
            plt.close()
            summary.to_csv(f'/Users/bob/PycharmData/sp100/test{test_mode}/turnover{bt.turnover}_split{bt.split}.csv')
