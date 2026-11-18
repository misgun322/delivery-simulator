from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from delivery import DeliveryMethod


@dataclass(frozen=True)
class Customer:
    name: str
    phone: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.phone.strip():
            raise ValueError("Укажите имя и телефон клиента.")

    def __str__(self) -> str:
        return f"{self.name} ({self.phone})"


@dataclass(frozen=True)
class Courier:
    number: int
    name: str

    def __post_init__(self) -> None:
        if self.number < 1 or not self.name.strip():
            raise ValueError("Укажите положительный номер и имя курьера.")

    def __str__(self) -> str:
        return f"№{self.number} {self.name}"


@dataclass(frozen=True)
class OrderItem:
    name: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Укажите название товара.")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise ValueError("Количество должно быть целым числом больше нуля.")
        if not self.unit_price.is_finite() or self.unit_price < 0:
            raise ValueError("Цена должна быть конечным неотрицательным числом.")

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


class OrderStatus(Enum):
    NEW = "Новый"
    CONFIRMED = "Подтверждён"
    IN_DELIVERY = "В доставке"
    READY_FOR_PICKUP = "Готов к самовывозу"
    DELIVERED = "Выполнен"
    CANCELLED = "Отменён"


class Order:
    _TRANSITIONS = {
        OrderStatus.NEW: (OrderStatus.CONFIRMED, OrderStatus.CANCELLED),
        OrderStatus.CONFIRMED: (
            OrderStatus.IN_DELIVERY,
            OrderStatus.READY_FOR_PICKUP,
            OrderStatus.CANCELLED,
        ),
        OrderStatus.IN_DELIVERY: (OrderStatus.DELIVERED,),
        OrderStatus.READY_FOR_PICKUP: (OrderStatus.DELIVERED,),
        OrderStatus.DELIVERED: (),
        OrderStatus.CANCELLED: (),
    }

    def __init__(self, number: int, customer: Customer, address: str) -> None:
        self._number = number
        self._customer = customer
        self._address = address.strip()
        self._items: list[OrderItem] = []
        self._delivery_method: DeliveryMethod | None = None
        self._courier: Courier | None = None
        self._status = OrderStatus.NEW

    @property
    def number(self) -> int:
        return self._number

    @property
    def customer(self) -> Customer:
        return self._customer

    @property
    def address(self) -> str:
        return self._address

    @property
    def items(self) -> tuple[OrderItem, ...]:
        return tuple(self._items)

    @property
    def items_total(self) -> Decimal:
        return sum((item.subtotal for item in self._items), Decimal("0.00"))

    @property
    def delivery_method(self) -> DeliveryMethod | None:
        return self._delivery_method

    @property
    def courier(self) -> Courier | None:
        return self._courier

    @property
    def status(self) -> OrderStatus:
        return self._status

    @property
    def delivery_cost(self) -> Decimal | None:
        if self._delivery_method is None:
            return None
        return self._delivery_method.calculate_cost(self)

    @property
    def delivery_hours(self) -> int | None:
        if self._delivery_method is None:
            return None
        return self._delivery_method.estimate_hours()

    @property
    def total_cost(self) -> Decimal:
        delivery_cost = self.delivery_cost
        return self.items_total if delivery_cost is None else self.items_total + delivery_cost

    def add_item(self, item: OrderItem) -> None:
        if self._status is not OrderStatus.NEW:
            raise ValueError("Добавлять позиции можно только в новый заказ.")
        if not isinstance(item, OrderItem):
            raise ValueError("В заказ можно добавить только позицию заказа.")
        self._items.append(item)

    def set_delivery_method(self, method: DeliveryMethod) -> None:
        if self._status is not OrderStatus.NEW:
            raise ValueError("Выбрать способ доставки можно только для нового заказа.")
        if not isinstance(method, DeliveryMethod):
            raise ValueError("Выберите один из способов доставки.")
        if method.requires_courier and not self._address:
            raise ValueError("Для курьерской доставки нужен адрес.")
        if not method.requires_courier:
            self._courier = None
        self._delivery_method = method

    def assign_courier(self, courier: Courier) -> None:
        if not isinstance(courier, Courier):
            raise ValueError("Назначить можно только курьера.")
        if self._status not in (OrderStatus.NEW, OrderStatus.CONFIRMED):
            raise ValueError("Курьера можно назначить до начала доставки.")
        if self._delivery_method is None:
            raise ValueError("Сначала выберите способ доставки.")
        if not self._delivery_method.requires_courier:
            raise ValueError("Для самовывоза курьер не нужен.")
        self._courier = courier

    def change_status(self, target: OrderStatus) -> None:
        if not isinstance(target, OrderStatus):
            raise ValueError("Выберите один из статусов заказа.")
        if target not in self._TRANSITIONS[self._status]:
            raise ValueError(
                f"Недопустимый переход: «{self._status.value}» → «{target.value}»."
            )
        method = self._delivery_method
        if target is OrderStatus.CONFIRMED:
            if not self._items:
                raise ValueError("В заказе должна быть хотя бы одна позиция.")
            if method is None:
                raise ValueError("Перед подтверждением выберите способ доставки.")
        if target is OrderStatus.IN_DELIVERY:
            if method is None or not method.requires_courier:
                raise ValueError("Для самовывоза выберите статус «Готов к самовывозу».")
            if self._courier is None:
                raise ValueError("Перед отправкой назначьте курьера.")
        if target is OrderStatus.READY_FOR_PICKUP:
            if method is None or method.requires_courier:
                raise ValueError("Этот статус доступен только для самовывоза.")
        self._status = target
