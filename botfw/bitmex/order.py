import time

from ..base import order as od
from .api import ccxt_bitmex
from ..etc.util import unix_time_from_ISO8601Z


class BitmexOrder(od.OrderBase):
    pass


class BitmexOrderManager(od.OrderManagerBase):
    Order = BitmexOrder

    def _after_auth(self):
        self.ws.subscribe('execution', self.__on_events)

    def _get_order_id(self, e):
        return e.orderID

    def _update_order(self, o, e):
        ts = unix_time_from_ISO8601Z(e.timestamp)
        now = time.time()

        status = e.ordStatus
        if status == 'New' and o.state != od.OPEN:
            o.open_ts = ts
            o.state, o.state_ts = od.OPEN, now
        elif status == 'Filled' and o.state != od.CLOSED:
            o.close_ts = ts
            o.state, o.state_ts = od.CLOSED, now
        elif status == 'Canceled' and o.state != od.CANCELED:
            o.close_ts = ts
            o.state, o.state_ts = od.CANCELED, now
        else:
            self.log.error(f'Unknown order status: {status}')

        filled = e.cumQty
        if filled != o.filled:
            o.trade_ts = ts
            o.filled = filled

    def _generate_order_object(self, e):
        symbol = ccxt_bitmex.markets_by_id[e.symbol]['symbol']
        return self.Order(
            symbol, e.ordType.lower(), e.side.lower(), e.orderQty, e.price)

    def __on_events(self, msg):
        if msg['action'] != 'insert':
            return

        for event in msg['data']:
            e = BitmexOrderEvent()
            e.__dict__ = event
            self._handle_order_event(e)


class BitmexPositionGroup(od.PositionGroupBase):
    SIZE_IN_FIAT = True

    def __init__(self):
        super().__init__()
        self.commission = 0  # total commissions in USD

    def update(self, price, size, commission):
        super().update(price, size)
        self.commission += commission
        self.pnl -= commission


class BitmexOrderGroup(od.OrderGroupBase):
    PositionGroup = BitmexPositionGroup

    def _handle_event(self, e):
        p, s, c = e.lastPx, e.lastQty, e.commission
        if not s:
            return

        s = s if e.side.lower() == od.BUY else -s
        self.position_group.update(p, s, c)


class BitmexOrderGroupManager(od.OrderGroupManagerBase):
    OrderGroup = BitmexOrderGroup


class BitmexOrderEvent:
    pass
    # https://www.bitmex.com/app/wsAPI
