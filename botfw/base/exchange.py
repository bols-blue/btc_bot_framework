import logging

from .order_simulator import OrderManagerSimulator, OrderGroupManagerSimulator


def none(*args):
    assert False
    return args[0]


class ExchangeBase:  # Abstract Factory
    Api = none
    Websocket = none
    Trade = none
    Orderbook = none
    OrderManager = none
    OrderGroupManager = none

    def __init__(self, simulate=False):
        self.log = logging.getLogger(self.__class__.__name__)
        self.trades = {}
        self.orderbooks = {}
        self.api = None
        self.websocket = None
        self.order_manager = None
        self.order_group_manager = None
        self.simulate = simulate

    def create_basics(self, ccxt_config):
        self.api = self.Api(ccxt_config)
        self.websocket = self.Websocket(
            ccxt_config['apiKey'], ccxt_config['secret'])
        if not self.simulate:
            self.order_manager = self.OrderManager(
                self.api, self.websocket)
            self.order_group_manager = self.OrderGroupManager(
                self.order_manager)
        else:
            self.order_manager = OrderManagerSimulator(
                self.api, self.websocket)
            self.order_manager.exchange = self
            if self.__class__.__name__ == 'Bitmex':
                self.order_manager.quote_prec = 0

            self.order_group_manager = OrderGroupManagerSimulator(
                self.order_manager)
            self.order_group_manager.order_group_class = getattr(
                self.OrderGroupManager, 'OrderGroup')
        return {
            'api': self.api,
            'websocket': self.websocket,
            'order_manager': self.order_manager,
            'order_group_manager': self.order_group_manager,
        }

    def create_trade(self, symbol, ws=None):
        if symbol in self.trades:
            self.log.warning(f'trade({symbol}) already exists')

        trade = self.Trade(symbol, ws)
        self.trades[symbol] = trade
        if self.order_group_manager:
            self.order_group_manager.trades[symbol] = trade
        return trade

    def create_orderbook(self, symbol, ws=None):
        if symbol in self.orderbooks:
            self.log.warning(f'trade({symbol}) already exists')

        orderbook = self.Orderbook(symbol, ws)
        self.orderbooks[symbol] = orderbook
        return orderbook

    def create_order_group(self, symbol, name=None):
        return self.order_group_manager.create_order_group(symbol, name)
