import json
import os

import pandas as pd
import yfinance as yf
from datetime import datetime


class sp100(object):
    def __init__(self):
        load_f = open('/Users/bob/PycharmData/sp100/sp100-historical-components.json', 'r')
        load_dict = json.load(load_f)
        load_dict.sort(key=lambda k: k.get('Date'))
        self.load_dict = load_dict
        self.dates = [datetime.strptime(k.get('Date'), '%Y/%m/%d').strftime('%Y-%m-%d') for k in load_dict]
        load_f.close()

    def get_list(self, date):
        for i in range(1, len(self.dates)):
            if self.dates[i] > date:
                return self.load_dict[i - 1].get('Symbols')

        return self.load_dict[-1].get('Symbols')

    @property
    def full_list(self):
        res = set(self.load_dict[0].get('Symbols'))
        for i in range(1, len(self.dates)):
            res = set(self.load_dict[i].get('Symbols')).union(res)
        return list(res)


class data(object):
    def __init__(self):
        self.sp100 = sp100()
        self.merge()

    @staticmethod
    def download(ticker):
        stock = yf.Ticker(ticker)
        hist_daily = stock.history(start='2008-01-01', end='2018-12-31', actions=False, interval='1d', auto_adjust=True)
        if len(hist_daily) > 10:
            hist_daily.dropna(inplace=True, how='all')
            close = hist_daily['Close'].fillna(method='ffill')
            close_return = (close / close.shift(1)).dropna()
            close_return.clip(0.8, 1.2, inplace=True)
            close = close_return.cumprod()
            hist_daily = pd.DataFrame(close / close[0])
            hist_daily.columns = [ticker]
            hist_daily.to_csv(f'/Users/bob/PycharmData/sp100/yahoo/{ticker}.csv')

    @staticmethod
    def merge():
        file_list = [f for f in os.listdir('/Users/bob/PycharmData/sp100/yahoo') if f.endswith('csv')]
        file_list.sort()

        df = pd.DataFrame()
        for file in file_list:
            tmp = pd.read_csv(f'/Users/bob/PycharmData/sp100/yahoo/{file}', parse_dates=[0]).set_index('Date')
            if len(df) == 0:
                df = tmp
            else:
                df = df.join(tmp)

        df.fillna(method='bfill', inplace=True)
        df.fillna(method='ffill', inplace=True)
        return df


if __name__ == '__main__':
    tmp = data()
    for ticker in tmp.sp100.full_list:
        tmp.download(ticker)
    df = tmp.merge()
    df.to_csv('/Users/bob/PycharmData/sp100/stock.csv')
