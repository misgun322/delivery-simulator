import os
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ConsoleTests(unittest.TestCase):
    def run_console(self, commands: list[str]) -> str:
        result = subprocess.run(
            [sys.executable, "-B", "main.py"],
            cwd=PROJECT_ROOT,
            input="\n".join(commands) + "\n" if commands else "",
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def test_all_six_menu_actions_for_standard_delivery(self) -> None:
        output = self.run_console([
            "2",
            "1", "Анна", "123", "ул. Мира, 10",
            "Книга", "2", "120,50", "1", "Блокнот", "1", "75", "0",
            "3", "1", "1",
            "4", "1", "2",
            "5", "1", "2", "5", "1", "3", "5", "1", "5",
            "2", "6",
        ])
        self.assertIn("Заказов пока нет.", output)
        self.assertIn("Книга: 2 × 120.50 руб. = 241.00 руб.", output)
        self.assertIn("Блокнот: 1 × 75.00 руб. = 75.00 руб.", output)
        self.assertIn("Стоимость доставки: 300.00 руб.", output)
        self.assertIn("Ориентировочный срок: 48 ч.", output)
        self.assertIn("Итого: 616.00 руб.", output)
        self.assertIn("Курьер: №2 Мария", output)
        self.assertEqual(output.count("Заказ №1 — Выполнен"), 2)
        self.assertTrue(output.rstrip().endswith("Работа завершена."))

    def test_bad_input_is_recoverable(self) -> None:
        output = self.run_console([
            "нет", "3", "abc", "3", "99",
            "1", "Анна", "123", "ул. Мира, 10",
            "Альбом", "0", "Альбом", "1,5",
            "Альбом", "1", "-30", "Альбом", "1", "цена",
            "Альбом", "1", "100", "нет", "0",
            "3", "1", "7", "3", "1", "2",
            "4", "1", "77",
            "5", "1", "9", "5", "1", "5", "6",
        ])
        for message in (
            "Введите номер действия от 1 до 6.",
            "Введите целое число больше нуля.",
            "Заказ №99 не найден.",
            "Цена должна быть конечным неотрицательным числом.",
            "Введите цену числом с точностью до двух знаков после запятой.",
            "Введите 1 или 0.",
            "Выберите способ доставки из списка.",
            "Курьер №77 не найден.",
            "Выберите статус из списка.",
            "Недопустимый переход",
        ):
            with self.subTest(message=message):
                self.assertIn(message, output)
        self.assertIn("Стоимость доставки: 500.00 руб.", output)
        self.assertTrue(output.rstrip().endswith("Работа завершена."))

    def test_pickup_with_no_address_or_courier(self) -> None:
        output = self.run_console([
            "1", "Анна", "123", "", "Книга", "1", "100", "0",
            "3", "1", "1", "3", "1", "3",
            "4", "1", "5", "1", "2", "5", "1", "4", "5", "1", "5", "6",
        ])
        self.assertIn("Для курьерской доставки нужен адрес.", output)
        self.assertIn("Для самовывоза курьер не нужен.", output)
        self.assertIn("Стоимость доставки: 0.00 руб.", output)
        self.assertIn("Ориентировочный срок: 2 ч.", output)
        self.assertIn("Заказ №1 — Готов к самовывозу", output)
        self.assertIn("Заказ №1 — Выполнен", output)

    def test_end_of_input_exits_cleanly(self) -> None:
        output = self.run_console([])
        self.assertTrue(output.rstrip().endswith("Работа завершена."))
