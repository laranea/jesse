import jesse.helpers as jh
import jesse.services.selectors as selectors
from jesse.config import config
from jesse.enums import order_statuses, order_flags
from jesse.services.notifier import notify
import jesse.services.logger as logger


class Order():
    def __init__(self, attributes=None):
        # id generated by Jesse for database usage
        self.id = ''
        # id generated by market
        self.exchange_id = ''
        self.symbol = ''
        self.exchange = ''
        self.side = ''
        self.type = ''
        self.flag = ''
        self.qty = 0
        self.price = 0
        self.status = order_statuses.ACTIVE
        self.created_at = None
        self.executed_at = None
        self.canceled_at = None
        self.role = None

        if attributes is None:
            attributes = {}

        for a in attributes:
            setattr(self, a, attributes[a])

        if self.created_at is None:
            self.created_at = jh.now()

        p = selectors.get_position(self.exchange, self.symbol)
        if p:
            p._on_opened_order(self)

        if jh.is_live() and config['env']['notifications']['events']['submitted_orders']:
            self.notify_submission()

        if jh.is_debuggable('order_submission'):
            logger.info(
                '{} order: {}, {}, {}, {}, ${}'.format(
                    'QUEUED' if self.is_queued else 'SUBMITTED',
                    self.symbol, self.type, self.side, self.qty,
                    round(self.price, 2)
                )
            )

    def notify_submission(self):
        notify(
            '{} order: {}, {}, {}, {}, ${}'.format(
                'QUEUED' if self.is_queued else 'SUBMITTED',
                self.symbol, self.type, self.side, self.qty,
                round(self.price, 2)
            )
        )

    @property
    def is_canceled(self) -> bool:
        return self.status == order_statuses.CANCELED

    @property
    def is_active(self) -> bool:
        return self.status == order_statuses.ACTIVE

    @property
    def is_queued(self) -> bool:
        """
        Used in live mode only: it means the strategy has considered the order as submitted,
        but the exchange does not accept it because of the distance between the current
        price and price of the order. Hence it's been queued for later submission.

        :return: bool
        """
        return self.status == order_statuses.QUEUED

    @property
    def is_new(self) -> bool:
        return self.is_active

    @property
    def is_executed(self) -> bool:
        return self.status == order_statuses.EXECUTED

    @property
    def is_filled(self) -> bool:
        return self.is_executed

    @property
    def is_reduce_only(self) -> bool:
        return self.flag == order_flags.REDUCE_ONLY

    @property
    def is_close(self) -> bool:
        return self.flag == order_flags.CLOSE

    def cancel(self):
        if self.is_canceled or self.is_executed:
            return

        self.canceled_at = jh.now()
        self.status = order_statuses.CANCELED

        if jh.is_debuggable('order_cancellation'):
            logger.info(
                'CANCELED order: {}, {}, {}, {}, ${}'.format(
                    self.symbol, self.type, self.side, self.qty, round(self.price, 2)
                )
            )

        # notify
        if jh.is_live() and config['env']['notifications']['events']['cancelled_orders']:
            notify(
                'CANCELED order: {}, {}, {}, {}, {}'.format(
                    self.symbol, self.type, self.side, self.qty, round(self.price, 2)
                )
            )

        p = selectors.get_position(self.exchange, self.symbol)
        if p:
            p._on_canceled_order(self)

    def execute(self):
        if self.is_canceled or self.is_executed:
            return

        self.executed_at = jh.now()
        self.status = order_statuses.EXECUTED

        # log
        if jh.is_debuggable('order_execution'):
            logger.info(
                'EXECUTED order: {}, {}, {}, {}, ${}'.format(
                    self.symbol, self.type, self.side, self.qty, round(self.price, 2)
                )
            )

        # notify
        if jh.is_live() and config['env']['notifications']['events']['executed_orders']:
            notify(
                'EXECUTED order: {}, {}, {}, {}, {}'.format(
                    self.symbol, self.type, self.side, self.qty, round(self.price, 2)
                )
            )

        p = selectors.get_position(self.exchange, self.symbol)

        if p:
            p._on_executed_order(self)