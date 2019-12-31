import datetime
import threading
import time

import alpaca_trade_api as tradeapi

API_KEY = "PK4AJ8TN25KTZBTVLH6R"
API_SECRET = "mCtlDH2Euk3kiOVf67gBjNYSA3FdKwroVV6nbU9F"
PAPER_ACCOUNT_TRADING_URL = "https://paper-api.alpaca.markets"
SP100 = ['AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'AGN', 'AIG', 'ALL', 'AMGN', 'AMZN', 'AXP', 'BA', 'BAC', 'BIIB', 'BK',
         'BKNG', 'BLK', 'BMY', 'BRK.B', 'C', 'CAT', 'CHTR', 'CL', 'CMCSA', 'COF', 'COP', 'COST', 'CSCO', 'CVS', 'CVX',
         'DD', 'DHR', 'DIS', 'DOW', 'DUK', 'EMR', 'EXC', 'F', 'FB', 'FDX', 'GD', 'GE', 'GILD', 'GM', 'GOOG', 'GOOGL',
         'GS', 'HD', 'HON', 'IBM', 'INTC', 'JNJ', 'JPM', 'KHC', 'KMI', 'KO', 'LLY', 'LMT', 'LOW', 'MA', 'MCD', 'MDLZ',
         'MDT', 'MET', 'MMM', 'MO', 'MRK', 'MS', 'MSFT', 'NEE', 'NFLX', 'NKE', 'NVDA', 'ORCL', 'OXY', 'PEP', 'PFE',
         'PG', 'PM', 'PYPL', 'QCOM', 'RTN', 'SBUX', 'SLB', 'SO', 'SPG', 'T', 'TGT', 'TMO', 'TXN', 'UNH', 'UNP', 'UPS',
         'USB', 'UTX', 'V', 'VZ', 'WBA', 'WFC', 'WMT', 'XOM']


class LongShort(object):
    def __init__(self, split=5, retrospect=20):
        self.split = split
        self.retrospect = retrospect
        self.alpaca = tradeapi.REST(API_KEY, API_SECRET, PAPER_ACCOUNT_TRADING_URL, 'v2')

        stockUniverse = SP100  # Format the allStocks variable for use in the class.
        self.allStocks = []
        for stock in stockUniverse:
            self.allStocks.append([stock, 0])

        self.long = []
        self.short = []
        self.blocklist = list()
        self.longAmount = 0
        self.shortAmount = 0

    def run(self):
        # First, cancel any existing orders so they don't impact our buying power.
        orders = self.alpaca.list_orders(status="open")
        for order in orders:
            self.alpaca.cancel_order(order.id)

        # Wait for market to open.
        print("Waiting for market to open...")
        tAMO = threading.Thread(target=self.await_market_open)
        tAMO.start()
        tAMO.join()
        print("Market opened.")

        tRebalance = threading.Thread(target=self.rebalance)
        tRebalance.start()
        tRebalance.join()

    def rebalance(self):
        tRerank = threading.Thread(target=self.get_amount())
        tRerank.start()
        tRerank.join()

        print("We are going to take a long position in: " + str(self.long))
        print("We are going to take a short position in: " + str(self.short))

        # Clear existing orders again.
        orders = self.alpaca.list_orders(status="open")
        for order in orders:
            self.alpaca.cancel_order(order.id)

        executed = [[], []]
        positions = self.alpaca.list_positions()

        # Remove positions that are no longer in the short or long list,
        # and make a list of positions that do not need to change.
        # Adjust position quantities if needed.
        for position in positions:
            if position.symbol not in self.long:
                # Position is not in long list.
                if position.symbol not in self.short:
                    # Position not in short list either.  Clear position.
                    if position.side == "long":
                        side = "sell"
                    else:
                        side = "buy"
                    respSO = []
                    tSO = threading.Thread(target=self.submit_order,
                                           args=[abs(int(float(position.qty))), position.symbol, side, respSO])
                    tSO.start()
                    tSO.join()
                else:
                    # Position in short list.
                    if position.side == "long":
                        # Position changed from long to short.  Clear long position to prepare for short position.
                        side = "sell"
                        respSO = []
                        tSO = threading.Thread(target=self.submit_order,
                                               args=[int(float(position.qty)), position.symbol, side, respSO])
                        tSO.start()
                        tSO.join()
                    else:
                        if abs(int(float(position.qty))) == self.qShort:
                            # Position is where we want it.  Pass for now.
                            pass
                        else:
                            # Need to adjust position amount
                            diff = abs(int(float(position.qty))) - self.qShort
                            if diff > 0:
                                # Too many short positions.  Buy some back to rebalance.
                                side = "buy"
                            else:
                                # Too little short positions.  Sell some more.
                                side = "sell"
                            respSO = []
                            tSO = threading.Thread(target=self.submit_order,
                                                   args=[abs(diff), position.symbol, side, respSO])
                            tSO.start()
                            tSO.join()
                        executed[1].append(position.symbol)
                        self.blocklist.add(position.symbol)
            else:
                # Position in long list.
                if position.side == "short":
                    # Position changed from short to long.  Clear short position to prepare for long position.
                    respSO = []
                    tSO = threading.Thread(target=self.submit_order,
                                           args=[abs(int(float(position.qty))), position.symbol, "buy", respSO])
                    tSO.start()
                    tSO.join()
                else:
                    if int(float(position.qty)) == self.qLong:
                        # Position is where we want it.  Pass for now.
                        pass
                    else:
                        # Need to adjust position amount.
                        diff = abs(int(float(position.qty))) - self.qLong
                        if diff > 0:
                            # Too many long positions.  Sell some to rebalance.
                            side = "sell"
                        else:
                            # Too little long positions.  Buy some more.
                            side = "buy"
                        respSO = []
                        tSO = threading.Thread(target=self.submit_order,
                                               args=[abs(diff), position.symbol, side, respSO])
                        tSO.start()
                        tSO.join()
                    executed[0].append(position.symbol)
                    self.blocklist.add(position.symbol)

        # Send orders to all remaining stocks in the long and short list.
        respSendBOLong = []
        tSendBOLong = threading.Thread(target=self.send_batch_order, args=[self.long, "buy", respSendBOLong])
        tSendBOLong.start()
        tSendBOLong.join()
        respSendBOLong[0][0] += executed[0]

        respSendBOShort = []
        tSendBOShort = threading.Thread(target=self.send_batch_order, args=[self.short, "sell", respSendBOShort])
        tSendBOShort.start()
        tSendBOShort.join()
        respSendBOShort[0][0] += executed[1]

        # Handle rejected/incomplete orders and determine new quantities to purchase.
        # Reorder stocks that didn't throw an error so that the equity quota is reached.
        if len(respSendBOLong[0][0]) > 0:
            respResendBOLong = []
            tResendBOLong = threading.Thread(target=self.send_batch_order, args=[self.long, "buy", respResendBOLong])
            tResendBOLong.start()
            tResendBOLong.join()

        if len(respSendBOShort[0][0]) > 0:
            respResendBOShort = []
            tResendBOShort = threading.Thread(target=self.send_batch_order, args=[self.long, "buy", respResendBOShort])
            tResendBOShort.start()
            tResendBOShort.join()

    # Determine amount to long/short based on total stock price of each bucket.
    def get_amount(self):
        tRank = threading.Thread(target=self.rank)
        tRank.start()
        tRank.join()

        # Grabs the top and bottom quarter of the sorted stock list to get the long and short lists.
        longShortNumber = len(self.allStocks) // self.split
        self.long = []
        self.short = []
        for i, stockField in enumerate(self.allStocks):
            if i < longShortNumber:
                self.short.append(stockField[0])
            elif i > (len(self.allStocks) - 1 - longShortNumber):
                self.long.append(stockField[0])
            else:
                continue

        equity = int(float(self.alpaca.get_account().equity))

        # TODO: I don't know if this is the right way to short a stock
        self.shortAmount = equity * 0.30 / longShortNumber  # the amount for every stock
        self.longAmount = equity + self.shortAmount / longShortNumber  # the amount for every stock

    # Submit a batch order that returns completed and uncompleted orders.
    def send_batch_order(self, stocks, side, resp):
        executed = []
        incomplete = []
        for stock in stocks:
            if stock not in self.blocklist:
                respSO = []
                qty = self.longAmount // self.get_present_price(stock)
                tsubmit_order = threading.Thread(target=self.submit_order, args=[qty, stock, side, respSO])
                tsubmit_order.start()
                tsubmit_order.join()
                if not respSO[0]:
                    # Stock order did not go through, add it to incomplete.
                    incomplete.append(stock)
                else:
                    executed.append(stock)
                respSO.clear()
        resp.append([executed, incomplete])

    # Submit an order if quantity is above 0.
    def submit_order(self, qty, stock, side, resp):
        if qty > 0:
            try:
                self.alpaca.submit_order(stock, qty, side, "market", "day")
                print("Market order of | " + str(qty) + " " + stock + " " + side + " | completed.")
                resp.append(True)
            except:
                print("Order of | " + str(qty) + " " + stock + " " + side + " | did not go through.")
                resp.append(False)
        else:
            print("Quantity is 0, order of | " + str(qty) + " " + stock + " " + side + " | not completed.")
            resp.append(True)

    # Wait for market to open.
    def await_market_open(self):
        isOpen = self.alpaca.get_clock().is_open
        while not isOpen:
            clock = self.alpaca.get_clock()
            openingTime = clock.next_open.replace(tzinfo=datetime.timezone.utc).timestamp()
            currTime = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
            timeToOpen = int((openingTime - currTime) / 60)
            print(str(timeToOpen) + " minutes til market open.")
            time.sleep(60)
            isOpen = self.alpaca.get_clock().is_open

    # Get the total price of the array of input stocks.
    def get_present_price(self, stock):
        bars = self.alpaca.get_barset(stock, "minute", 1)
        return bars[stock][0].c

    # Get percent changes of the stock prices over the past 10 days.
    def get_percent_changes(self):
        for i, stock in enumerate(self.allStocks):
            bars = self.alpaca.get_barset(stock[0], 'day', self.retrospect)
            self.allStocks[i][1] = (bars[stock[0]][- 1].c - bars[stock[0]][0].o) / bars[stock[0]][0].o

    # Mechanism used to rank the stocks, the basis of the Long-Short Equity Strategy.
    def rank(self):
        # Ranks all stocks by percent change over the past 10 days (higher is better).
        tGetPC = threading.Thread(target=self.get_percent_changes)
        tGetPC.start()
        tGetPC.join()

        # Sort the stocks in place by the percent change field (marked by pc).
        self.allStocks.sort(key=lambda x: -x[1])


if __name__ == "__main__":
    ls = LongShort()
    ls.run()
    # ls.rebalance()
