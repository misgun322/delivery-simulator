from console import run_menu
from models import Courier
from order_service import OrderService


def main() -> None:
    couriers = (Courier(1, "Алексей"), Courier(2, "Мария"), Courier(3, "Иван"))
    run_menu(OrderService(couriers))


if __name__ == "__main__":
    main()
