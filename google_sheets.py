import gspread
import os
from loguru import logger


class GoogleSheets:

    def __init__(self):
        try:
            logger.info("Инициализация GoogleSheets")
            gc = gspread.service_account(filename="credentials.json")
            sh = gc.open_by_key("1KWsRADiDlfxA5Z_DD6Play_2AnAwpYZ-8ceEpdzOv7U")
            self.worksheet = sh.worksheet("Лист1")
            logger.info("Успешное подключение к таблице")
        except Exception as e:
            logger.error(f"Ошибка при инициализации GoogleSheets: {e}")
            raise

    def insert_row(self, row_data, index: int):
        """Вставляет строку данных на указанный индекс."""
        try:
            row_data[5], row_data[11], row_data[12] = int(row_data[11]), int(row_data[11]), int(row_data[12])
            logger.info(f"Вставка строки на позицию {index}: {row_data}")
            self.worksheet.insert_row(row_data, index)
            logger.info("Строка успешно вставлена")
        except Exception as e:
            logger.error(f"Ошибка при вставке строки: {e}")
            raise
            
    def get_row_count(self):
        """Возвращает количество строк, включая пустые."""
        try:
            logger.info("Получение общего количества строк")
            row_count = self.worksheet.row_count
            logger.info(f"Количество строк в таблице: {row_count}")
            return row_count
        except Exception as e:
            logger.error(f"Ошибка при получении количества строк: {e}")
            raise

    def get_filled_row_count(self):
        """Возвращает количество заполненных строк (игнорируя пустые строки)."""
        try:
            logger.info("Получение количества заполненных строк")
            filled_rows = len(self.worksheet.get_all_values())
            logger.info(f"Количество заполненных строк: {filled_rows}")
            return filled_rows
        except Exception as e:
            logger.error(f"Ошибка при получении количества заполненных строк: {e}")
            raise
