"""
MODULE: scripts.run_document_processing
RESPONSIBILITY: Running automated document processing (downloading, extracting, matching).
ALLOWED: sys, argparse, pathlib, loguru, os, config.settings, core.database, core.tender_database, core.exceptions, services.archive_background_runner.
FORBIDDEN: None.
ERRORS: None.

Скрипт для запуска автоматической обработки документов торгов.

Выполняет полный цикл:
1. Получение торгов из БД по критериям пользователя или конкретных закупок
2. Скачивание документов (сметы + Excel)
3. Обработка архивов и поиск совпадений
4. Сохранение результатов в БД

Использование:
    python scripts/run_document_processing.py
    python scripts/run_document_processing.py --tenders "44fz:123,456 223fz:789"
"""

import sys
import argparse
from pathlib import Path

from loguru import logger

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import config
from core.database import DatabaseManager
from core.tender_database import TenderDatabaseManager
from core.exceptions import DatabaseConnectionError
from services.archive_background_runner import ArchiveBackgroundRunner


def parse_tender_ids(tenders_arg: str) -> list:
    """
    Парсит строку с ID закупок в формате "44fz:123,456 223fz:789"
    
    Returns:
        Список словарей: [{'id': 123, 'registry_type': '44fz'}, ...]
    """
    if not tenders_arg:
        return None
    
    result = []
    parts = tenders_arg.split()
    
    for part in parts:
        if ':' not in part:
            continue
        
        registry_type, ids_str = part.split(':', 1)
        registry_type = registry_type.strip().lower()
        
        if registry_type not in ['44fz', '223fz']:
            continue
        
        try:
            ids = [int(id_str.strip()) for id_str in ids_str.split(',') if id_str.strip()]
            for tender_id in ids:
                result.append({'id': tender_id, 'registry_type': registry_type})
        except ValueError:
            logger.warning(f"Неверный формат ID в '{part}', пропускаем")
    
    return result if result else None


def main():
    """Основная функция запуска обработки документов."""
    
    # Настройка логирования
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:HH:mm:ss} | {level: <8} | {message}",
        colorize=True
    )
    
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description='Обработка документов торгов')
    parser.add_argument(
        '--tenders',
        type=str,
        help='Конкретные закупки для обработки в формате "44fz:123,456 223fz:789"'
    )
    parser.add_argument(
        '--user-id',
        type=int,
        default=1,
        help='ID пользователя (по умолчанию: 1)'
    )
    parser.add_argument(
        '--all-after-priority',
        action='store_true',
        help='Обработать все закупки после приоритетных (используется с --tenders)'
    )
    parser.add_argument(
        '--registry-type',
        type=str,
        choices=['44fz', '223fz'],
        help='Тип реестра для анализа (44fz или 223fz). Если не указан, анализируются оба реестра.'
    )
    parser.add_argument(
        '--tender-type',
        type=str,
        choices=['new', 'won'],
        default='new',
        help='Тип торгов для анализа (new для новых, won для разыгранных). По умолчанию new.'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=2,
        help='Максимальное количество параллельных потоков (по умолчанию: 2 для ноутбуков)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=5,
        help='Размер партии торгов для обработки перед паузой (по умолчанию: 5)'
    )
    parser.add_argument(
        '--batch-delay',
        type=float,
        default=10.0,
        help='Задержка между партиями торгов в секундах (по умолчанию: 10.0)'
    )
    args = parser.parse_args()
    
    # Парсим ID закупок, если указаны
    specific_tender_ids = None
    if args.tenders:
        specific_tender_ids = parse_tender_ids(args.tenders)
        if specific_tender_ids:
            logger.info(f"Обработка конкретных закупок: {len(specific_tender_ids)} закупок")
        else:
            logger.warning("Не удалось распарсить ID закупок, используем настройки пользователя")
    
    logger.info("🚀 Запуск автоматической обработки документов торгов")
    logger.info("="*80)
    logger.info(f"Параметры: user_id={args.user_id}, registry_type={args.registry_type}, tender_type={args.tender_type}, specific_tenders={specific_tender_ids is not None}")
    
    # Проверка конфигурации
    if not config.tender_database:
        logger.error("❌ Конфигурация БД tender_monitor не задана в .env файле!")
        sys.exit(1)

    if not config.database:
        logger.error("❌ Конфигурация БД product_catalog не задана в .env файле!")
        sys.exit(1)
    
    # Подключение к БД tender_monitor
    try:
        tender_db_manager = TenderDatabaseManager(config.tender_database)
        tender_db_manager.connect()
        logger.info("✅ Подключение к БД tender_monitor установлено")
    except DatabaseConnectionError as error:
        logger.error(f"❌ Ошибка подключения к БД tender_monitor: {error}")
        sys.exit(1)
    
    # Подключение к БД product_catalog
    try:
        product_db_manager = DatabaseManager(config.database)
        product_db_manager.connect()
        logger.info("✅ Подключение к БД product_catalog установлено")
    except DatabaseConnectionError as error:
        logger.error(f"❌ Ошибка подключения к БД product_catalog: {error}")
        tender_db_manager.disconnect()
        sys.exit(1)

    # Создание runner
    logger.info("Создание ArchiveBackgroundRunner...")
    runner = ArchiveBackgroundRunner(
        tender_db_manager=tender_db_manager,
        product_db_manager=product_db_manager,
        user_id=args.user_id,
        max_workers=args.max_workers,
        batch_size=args.batch_size,
        batch_delay=args.batch_delay,
    )
    logger.info("ArchiveBackgroundRunner создан успешно")
    # Если указан флаг --all-after-priority, сначала обрабатываем приоритетные, затем все остальные
    if args.all_after_priority and specific_tender_ids:
        logger.info("Режим 'все после приоритетных': сначала обрабатываем приоритетные закупки")
        logger.info(f"Вызов runner.run() для приоритетных закупок: {len(specific_tender_ids)} закупок")
        # Обрабатываем приоритетные
        priority_stats = runner.run(specific_tender_ids=specific_tender_ids, registry_type=args.registry_type, tender_type=args.tender_type)
        logger.info(f"Приоритетные закупки обработаны: {priority_stats.get('processed', 0)}/{priority_stats.get('total_tenders', 0)}")

        # Теперь обрабатываем все остальные (без конкретных ID)
        logger.info("Теперь обрабатываем все остальные закупки по настройкам пользователя")
        logger.info("Вызов runner.run() для всех остальных закупок")
        all_stats = runner.run(specific_tender_ids=None, registry_type=args.registry_type, tender_type=args.tender_type)

        # Объединяем статистику
        stats = {
            "priority_processed": priority_stats.get('processed', 0),
            "priority_total": priority_stats.get('total_tenders', 0),
            "all_processed": all_stats.get('processed', 0),
            "all_total": all_stats.get('total_tenders', 0),
            "processed": priority_stats.get('processed', 0) + all_stats.get('processed', 0),
            "total_tenders": priority_stats.get('total_tenders', 0) + all_stats.get('total_tenders', 0),
            "errors": priority_stats.get('errors', 0) + all_stats.get('errors', 0),
            "total_matches": priority_stats.get('total_matches', 0) + all_stats.get('total_matches', 0),
        }
    else:
        # Обычный режим: либо конкретные закупки, либо все по настройкам
        logger.info("Запуск обработки документов...")
        if specific_tender_ids:
            logger.info(f"Вызов runner.run() для конкретных закупок: {len(specific_tender_ids)} закупок")
        else:
            logger.info("Вызов runner.run() для всех закупок по настройкам пользователя")
        stats = runner.run(specific_tender_ids=specific_tender_ids, registry_type=args.registry_type, tender_type=args.tender_type)
        logger.info(f"runner.run() завершен. Статистика: {stats}")
        
    logger.info("\n✅ Обработка завершена успешно")
    if args.all_after_priority and specific_tender_ids:
        logger.info(f"Приоритетных торгов: {stats.get('priority_processed', 0)}/{stats.get('priority_total', 0)}")
        logger.info(f"Остальных торгов: {stats.get('all_processed', 0)}/{stats.get('all_total', 0)}")
        logger.info(f"Всего обработано: {stats.get('processed', 0)}/{stats.get('total_tenders', 0)}")
    else:
        logger.info(f"Обработано торгов: {stats.get('processed', 0)}/{stats.get('total_tenders', 0)}")


    # Закрываем соединения с защитой от Access Violation
    try:
        if product_db_manager:
            try:
                product_db_manager.close()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии соединения с product_catalog: {e}")
    except Exception as e:
        logger.warning(f"Ошибка при работе с product_db_manager: {e}")
    
    try:
        if tender_db_manager:
            try:
                tender_db_manager.disconnect()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии соединения с tender_monitor: {e}")
    except Exception as e:
        logger.warning(f"Ошибка при работе с tender_db_manager: {e}")


if __name__ == "__main__":
    main()

