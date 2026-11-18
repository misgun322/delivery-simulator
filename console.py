import re
from decimal import Decimal

from delivery import ExpressDelivery, PickupDelivery, StandardDelivery
from models import Customer, Order, OrderItem, OrderStatus
from order_service import OrderService


MENU = """\
1. Создать заказ и добавить позиции
2. Показать список заказов
3. Выбрать способ доставки
4. Назначить курьера
5. Изменить статус заказа
6. Завершить работу"""

DELIVERY_METHODS = (StandardDelivery(), ExpressDelivery(), PickupDelivery())


def _read_positive_int(prompt: str) -> int:
    try:
        number = int(input(prompt))
    except ValueError:
        raise ValueError("Введите целое число больше нуля.") from None
    if number <= 0:
        raise ValueError("Введите целое число больше нуля.")
    return number


def _read_price() -> Decimal:
    text = input("Цена за единицу, руб.: ").strip()
    if not re.fullmatch(r"-?[0-9]+(?:[.,][0-9]{1,2})?", text):
        raise ValueError("Введите цену числом с точностью до двух знаков после запятой.")
    return Decimal(text.replace(",", "."))


def _read_order(service: OrderService) -> Order:
    return service.get_order(_read_positive_int("Номер заказа: "))


def _read_items() -> list[OrderItem]:
    items = []
    while True:
        try:
            name = input("Название товара: ").strip()
            quantity = _read_positive_int("Количество: ")
            items.append(OrderItem(name, quantity, _read_price()))
        except ValueError as error:
            print(f"Ошибка: {error} Введите позицию заново.")
            continue

        while True:
            answer = input("Добавить ещё позицию? (1 — да, 0 — нет): ").strip()
            if answer == "0":
                return items
            if answer == "1":
                break
            print("Введите 1 или 0.")


def _money(amount: Decimal) -> str:
    return f"{amount:.2f} руб."


def _show_order(order: Order) -> None:
    print(f"Заказ №{order.number} — {order.status.value}")
    print(f"Клиент: {order.customer}")
    print(f"Адрес: {order.address or 'не указан'}")
    for item in order.items:
        print(
            f"  {item.name}: {item.quantity} × {_money(item.unit_price)}"
            f" = {_money(item.subtotal)}"
        )
    print(f"Товары: {_money(order.items_total)}")
    if order.delivery_method is not None:
        print(f"Способ доставки: {order.delivery_method.name}")
        print(f"Стоимость доставки: {_money(order.delivery_cost)}")
        print(f"Ориентировочный срок: {order.delivery_hours} ч.")
    else:
        print("Способ доставки: не выбран")
    if order.delivery_method is not None and not order.delivery_method.requires_courier:
        print("Курьер: не требуется")
    else:
        print(f"Курьер: {order.courier or 'не назначен'}")
    print(f"Итого: {_money(order.total_cost)}")


def _create_order(service: OrderService) -> None:
    customer = Customer(input("Имя клиента: ").strip(), input("Телефон клиента: ").strip())
    address = input("Адрес доставки (можно оставить пустым для самовывоза): ").strip()
    order = service.create_order(customer, address, _read_items())
    _show_order(order)


def _list_orders(service: OrderService) -> None:
    orders = service.list_orders()
    if not orders:
        print("Заказов пока нет.")
        return
    for index, order in enumerate(orders):
        if index:
            print()
        _show_order(order)


def _select_delivery(service: OrderService) -> None:
    order = _read_order(service)
    for number, method in enumerate(DELIVERY_METHODS, start=1):
        print(f"{number}. {method.name}")
    choice = _read_positive_int("Способ доставки: ")
    if choice > len(DELIVERY_METHODS):
        raise ValueError("Выберите способ доставки из списка.")
    _show_order(service.set_delivery_method(order.number, DELIVERY_METHODS[choice - 1]))


def _assign_courier(service: OrderService) -> None:
    order = _read_order(service)
    if order.delivery_method is None:
        raise ValueError("Сначала выберите способ доставки.")
    if not order.delivery_method.requires_courier:
        print("Для самовывоза курьер не нужен.")
        return
    for courier in service.list_couriers():
        print(courier)
    courier_number = _read_positive_int("Номер курьера: ")
    _show_order(service.assign_courier(order.number, courier_number))


def _change_status(service: OrderService) -> None:
    order = _read_order(service)
    print(f"Текущий статус: {order.status.value}")
    statuses = tuple(OrderStatus)
    for number, status in enumerate(statuses, start=1):
        print(f"{number}. {status.value}")
    choice = _read_positive_int("Новый статус: ")
    if choice > len(statuses):
        raise ValueError("Выберите статус из списка.")
    _show_order(service.change_status(order.number, statuses[choice - 1]))


def run_menu(service: OrderService) -> None:
    actions = {
        "1": _create_order,
        "2": _list_orders,
        "3": _select_delivery,
        "4": _assign_courier,
        "5": _change_status,
    }
    print("Консольный симулятор службы доставки")
    try:
        while True:
            print(f"\n{MENU}")
            choice = input("Выберите действие: ").strip()
            if choice == "6":
                print("Работа завершена.")
                return
            action = actions.get(choice)
            if action is None:
                print("Введите номер действия от 1 до 6.")
                continue
            try:
                action(service)
            except ValueError as error:
                print(f"Ошибка: {error}")
    except (EOFError, KeyboardInterrupt):
        print("\nРабота завершена.")
