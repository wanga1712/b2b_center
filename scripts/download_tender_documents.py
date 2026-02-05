"""
MODULE: scripts.download_tender_documents
RESPONSIBILITY: Downloading all documents for a tender specified by contract number.
ALLOWED: sys, pathlib, typing, loguru, psycopg2.extras, config.settings, core.database, core.tender_database, core.exceptions, services.document_search_service, services.document_search.document_downloader.
FORBIDDEN: None.
ERRORS: None.

Скрипт для скачивания всех документов по номеру закупки из базы данных.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

from loguru import logger
from psycopg2.extras import RealDictCursor

from config.settings import config
from core.database import DatabaseManager
from core.tender_database import TenderDatabaseManager
from core.exceptions import DatabaseConnectionError
from services.document_search_service import DocumentSearchService
from services.document_search.document_downloader import DocumentDownloader


def find_tender_by_number(
    db_manager: TenderDatabaseManager,
    contract_number: str,
) -> Optional[Dict[str, Any]]:
    """
    Находит торг по номеру в базе данных.
    
    Args:
        db_manager: Менеджер БД tender_monitor
        contract_number: Номер закупки
        
    Returns:
        Словарь с данными торга или None
    """
    # Ищем в 44ФЗ
    query_44fz = """
        SELECT 
            id,
            contract_number,
            tender_link,
            '44fz' as registry_type
        FROM reestr_contract_44_fz
        WHERE contract_number = %s
        LIMIT 1
    """
    try:
        results = db_manager.execute_query(query_44fz, (contract_number,), RealDictCursor)
        if results:
            return dict(results[0])
    except Exception as error:
        logger.debug(f"Ошибка при поиске в 44ФЗ: {error}")
    
    # Ищем в 223ФЗ
    query_223fz = """
        SELECT 
            id,
            contract_number,
            tender_link,
            '223fz' as registry_type
        FROM reestr_contract_223_fz
        WHERE contract_number = %s
        LIMIT 1
    """
    try:
        results = db_manager.execute_query(query_223fz, (contract_number,), RealDictCursor)
        if results:
            return dict(results[0])
    except Exception as error:
        logger.debug(f"Ошибка при поиске в 223ФЗ: {error}")
    
    return None


def get_tender_documents(
    db_manager: TenderDatabaseManager,
    tender_id: int,
    registry_type: str,
) -> List[Dict[str, Any]]:
    """
    Получает все документы для торга.
    
    Args:
        db_manager: Менеджер БД tender_monitor
        tender_id: ID торга
        registry_type: Тип реестра (44fz или 223fz)
        
    Returns:
        Список документов
    """
    table_name = (
        "links_documentation_44_fz" if registry_type.lower() == "44fz"
        else "links_documentation_223_fz"
    )
    
    query = f"""
        SELECT 
            id,
            contract_id,
            document_links,
            file_name
        FROM {table_name}
        WHERE contract_id = %s
        ORDER BY id
    """
    
    try:
        results = db_manager.execute_query(query, (tender_id,), RealDictCursor)
        return [dict(row) for row in results] if results else []
    except Exception as error:
        logger.error(f"Ошибка при получении документов: {error}")
        return []


def download_all_documents(
    documents: List[Dict[str, Any]],
    tender_id: int,
    registry_type: str,
    download_dir: Path,
    unrar_path: Optional[str] = None,
    winrar_path: Optional[str] = None,
) -> List[Path]:
    """
    Скачивает все документы для торга.
    
    Args:
        documents: Список документов из БД
        tender_id: ID торга
        registry_type: Тип реестра
        download_dir: Директория для скачивания
        unrar_path: Путь к UnRAR
        winrar_path: Путь к WinRAR
        
    Returns:
        Список путей к скачанным файлам
    """
    if not documents:
        logger.warning("Нет документов для скачивания")
        return []
    
    # Создаем папку для торга
    folder_name = f"{registry_type}_{tender_id}"
    tender_folder = download_dir / folder_name
    tender_folder.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📁 Папка для загрузки: {tender_folder}")
    logger.info(f"📄 Найдено документов: {len(documents)}")
    
    # Используем DocumentDownloader для скачивания
    downloader = DocumentDownloader(tender_folder)
    
    all_downloaded_paths: List[Path] = []
    
    # Скачиваем все документы
    for idx, doc in enumerate(documents, 1):
        file_name = doc.get("file_name") or f"document_{doc.get('id')}"
        link = doc.get("document_links")
        
        if not link:
            logger.warning(f"⚠️  Пропущен документ {file_name}: нет ссылки")
            continue
        
        logger.info(f"[{idx}/{len(documents)}] Скачивание: {file_name}")
        
        try:
            downloaded_path = downloader.download_document(doc, target_dir=tender_folder)
            if downloaded_path:
                all_downloaded_paths.append(downloaded_path)
                logger.info(f"✅ Скачан: {downloaded_path.name}")
            else:
                logger.warning(f"⚠️  Не удалось скачать: {file_name}")
        except Exception as error:
            logger.error(f"❌ Ошибка при скачивании {file_name}: {error}")
            continue
    
    logger.info(f"\n✅ Всего скачано файлов: {len(all_downloaded_paths)}")
    return all_downloaded_paths


def main():
    """Основная функция."""
    # Настройка логирования
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:HH:mm:ss} | {level: <8} | {message}",
        colorize=True
    )
    
    # Номер закупки из аргументов или по умолчанию
    if len(sys.argv) > 1:
        contract_number = sys.argv[1]
    else:
        contract_number = "0172200002525000618"
    
    logger.info(f"🔍 Поиск закупки: {contract_number}")
    logger.info("="*80)
    
    # Подключаемся к БД tender_monitor
    try:
        tender_db = TenderDatabaseManager(config.tender_database)
        tender_db.connect()
        logger.info("✅ Подключение к БД tender_monitor установлено")
    except DatabaseConnectionError as error:
        logger.error(f"❌ Ошибка подключения к БД: {error}")
        sys.exit(1)
    
    # Ищем торг
    tender = find_tender_by_number(tender_db, contract_number)
    
    if not tender:
        logger.error(f"❌ Торг с номером {contract_number} не найден в базе данных")
        tender_db.disconnect()
        sys.exit(1)
    
    tender_id = tender["id"]
    registry_type = tender["registry_type"]
    tender_link = tender.get("tender_link", "")
    
    logger.info(f"✅ Торг найден:")
    logger.info(f"   ID: {tender_id}")
    logger.info(f"   Тип: {registry_type}")
    logger.info(f"   Ссылка: {tender_link}")
    logger.info("")
    
    # Получаем документы
    documents = get_tender_documents(tender_db, tender_id, registry_type)
    
    if not documents:
        logger.warning("⚠️  У торга нет документов в базе данных")
        tender_db.disconnect()
        sys.exit(0)
    
    logger.info(f"📄 Найдено документов в БД: {len(documents)}")
    logger.info("")
    
    # Определяем директорию загрузки
    if config.document_download_dir:
        download_dir = Path(config.document_download_dir).expanduser().resolve()
    else:
        logger.error("❌ DOCUMENT_DOWNLOAD_DIR не настроен в .env файле!")
        tender_db.disconnect()
        sys.exit(1)
    
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # Скачиваем документы
    logger.info("🚀 Начинаю скачивание документов...")
    logger.info("="*80)
    
    downloaded_paths = download_all_documents(
        documents=documents,
        tender_id=tender_id,
        registry_type=registry_type,
        download_dir=download_dir,
        unrar_path=config.unrar_tool,
        winrar_path=config.winrar_path,
    )
    
    logger.info("")
    logger.info("="*80)
    logger.info("📊 ИТОГИ")
    logger.info("="*80)
    logger.info(f"📄 Всего документов в БД: {len(documents)}")
    logger.info(f"✅ Успешно скачано: {len(downloaded_paths)}")
    logger.info(f"📁 Папка: {download_dir / f'{registry_type}_{tender_id}'}")
    
    # Закрываем соединение
    tender_db.disconnect()
    logger.info("\n✅ Готово!")


if __name__ == "__main__":
    main()











