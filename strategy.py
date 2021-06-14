import backtrader as bt
import math

class PrintClose(bt.Strategy):

	def __init__(self):
		#Keep a reference to the "close" line in the data[0] dataseries
		self.dataclose = self.datas[0].close

	def log(self, txt, dt=None):
		dt = dt or self.datas[0].datetime.date(0)
		print(f'{dt.isoformat()} {txt}') #Print date and close

	def next(self):
		self.log('Close: ', self.dataclose[0])

class MAcrossover(bt.Strategy): 
	# Moving average parameters
	params = (('pfast',20),('pslow',50),)

	def log(self, txt, dt=None):
		dt = dt or self.datas[0].datetime.date(0)
		print(f'{dt.isoformat()} {txt}') # Comment this line when running optimization

	def __init__(self):
		self.dataclose = self.datas[0].close
		
		# Order variable will contain ongoing order details/status
		self.order = None

		# Instantiate moving averages
		self.fast_sma = bt.indicators.MovingAverageSimple(self.datas[0], period=self.params.pfast)
		self.slow_sma = bt.indicators.MovingAverageSimple(self.datas[0], period=self.params.pslow)
		
		''' Using the built-in crossover indicator
		self.crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)'''


	def notify_order(self, order):
		if order.status in [order.Submitted, order.Accepted]:
			# An active Buy/Sell order has been submitted/accepted - Nothing to do
			return

		# Check if an order has been completed
		# Attention: broker could reject order if not enough cash
		if order.status in [order.Completed]:
			if order.isbuy():
				self.log(f'BUY EXECUTED, {order.executed.price:.2f}')
			elif order.issell():
				self.log(f'SELL EXECUTED, {order.executed.price:.2f}')
			self.bar_executed = len(self)

		elif order.status in [order.Canceled, order.Margin, order.Rejected]:
			self.log('Order Canceled/Margin/Rejected')

		# Reset orders
		self.order = None

	def next(self):
		''' Logic for using the built-in crossover indicator
		
		if self.crossover > 0: # Fast ma crosses above slow ma
			pass # Signal for buy order
		elif self.crossover < 0: # Fast ma crosses below slow ma
			pass # Signal for sell order
		'''

		# Check for open orders
		if self.order:
			return

		# Check if we are in the market
		if not self.position:
			# We are not in the market, look for a signal to OPEN trades
				
			#If the 20 SMA is above the 50 SMA
			if self.fast_sma[0] > self.slow_sma[0] and self.fast_sma[-1] < self.slow_sma[-1]:
				self.log(f'BUY CREATE {self.dataclose[0]:2f}')
				# Keep track of the created order to avoid a 2nd order
				self.order = self.buy()
			#Otherwise if the 20 SMA is below the 50 SMA   
			elif self.fast_sma[0] < self.slow_sma[0] and self.fast_sma[-1] > self.slow_sma[-1]:
				self.log(f'SELL CREATE {self.dataclose[0]:2f}')
				# Keep track of the created order to avoid a 2nd order
				self.order = self.sell()
		else:
			# We are already in the market, look for a signal to CLOSE trades
			if len(self) >= (self.bar_executed + 5):
				self.log(f'CLOSE CREATE {self.dataclose[0]:2f}')
				self.order = self.close()


#Create golden cross strategy:
class GoldCross(bt.Strategy):

    # set parameters to define fast and slow
    params = (
        ("fast", 40),
        ("slow", 150),
        ("order_percentage", 0.99),
        ("ticker", "stock"),
    )

    def __init__(self):
        print("position size:", self.position.size)

        self.fast_moving_average = bt.indicators.EMA(
            self.data.close, period=self.params.fast, plotname="40 day moving average"
        )

        self.slow_moving_average = bt.indicators.EMA(
            self.data.close, period=self.params.slow, plotname="150 day moving average"
        )

        self.crossover = bt.indicators.CrossOver(
            self.fast_moving_average, self.slow_moving_average
        )

    def log(self, txt, dt=None):
        dt = dt or self.data.datetime[0]
        if isinstance(dt, float):
            dt = bt.num2date(dt)
        print("%s, %s" % (dt.date(), txt))

    def notify_order(self, order):
        """ Triggered upon changes to orders. """

        # Suppress notification if it is just a submitted order.
        if order.status == order.Submitted:
            return

        # Print out the date, security name, order number and status.
        dt, dn = self.datetime.date(), order.data._name
        type = "Buy" if order.isbuy() else "Sell"
        self.log(
            f"{order.data._name:<6} Order: {order.ref:3d}\tType: {type:<5}\tStatus"
            f" {order.getstatusname():<8} \t"
            f"Size: {order.created.size:9.4f} Price: {order.created.price:9.4f} "
            f"Position: {self.getposition(order.data).size}"
        )
        if order.status == order.Margin:
            return

        # Check if an order has been completed
        if order.status in [order.Completed]:
            self.log(
                f"{order.data._name:<6} {('BUY' if order.isbuy() else 'SELL'):<5} "
                # f"EXECUTED for: {dn} "
                f"Price: {order.executed.price:6.2f} "
                f"Cost: {order.executed.value:6.2f} "
                f"Comm: {order.executed.comm:4.2f} "
                f"Size: {order.created.size:9.4f} "
            )

    def notify_trade(self, trade):
        """Provides notification of closed trades."""
        if trade.isclosed:
            self.log(
                "{} Closed: PnL Gross {}, Net {},".format(
                    trade.data._name,
                    round(trade.pnl, 2),
                    round(trade.pnlcomm, 1),
                )
            )

    def next(self):
        if self.position.size == 0:
            if self.crossover > 0:
                amount_to_invest = self.params.order_percentage * self.broker.cash
                self.size = math.floor(amount_to_invest / self.data.close)

                self.log(
                    "Buy {} shares of {} at {}".format(
                        self.size,
                        self.params.ticker,
                        self.data.close[0],
                    )
                )
                self.buy(size=self.size)

        if self.position.size > 0:
            if self.crossover < 0:
                self.log(
                    "Sell {} shares of {} at {}".format(
                        self.size, self.params.ticker, self.data.close[0],
                    )
                )
                self.sell(size=self.size)