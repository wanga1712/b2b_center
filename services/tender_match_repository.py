"""
Репозиторий для работы с результатами поиска совпадений в документации закупок

Предоставляет методы для:
- Сохранения результатов поиска
- Получения результатов по ID закупки
- Обновления статуса интереса (интересно/неинтересно)
- Фильтрации неинтересных закупок
"""

from typing import Optional, Dict, Any, List, Sequence
from datetime import datetime
import json
from loguru import logger
from core.tender_database import TenderDatabaseManager
from core.exceptions import DatabaseQueryError, DatabaseConnectionError
from psycopg2.extras import RealDictCursor


class TenderMatchRepository:
    """
    Репозиторий для работы с результатами поиска совпадений
    """
    
    def __init__(self, db_manager: TenderDatabaseManager):
        """
        Инициализация репозитория
        
        Args:
            db_manager: Менеджер базы данных tender_monitor
        """
        self.db_manager = db_manager
    
    def save_match_result(
        self,
        tender_id: int,
        registry_type: str,
        match_count: int,
        match_percentage: float,
        processing_time_seconds: Optional[float] = None,
        total_files_processed: int = 0,
        total_size_bytes: int = 0,
        error_reason: Optional[str] = None,
    ) -> Optional[int]:
        """
        Сохранение или обновление результата поиска совпадений
        
        Args:
            tender_id: ID закупки
            registry_type: Тип реестра ('44fz' или '223fz')
            match_count: Количество найденных совпадений
            match_percentage: Процент совпадений (0.0-100.0)
            processing_time_seconds: Время обработки в секундах
            total_files_processed: Количество обработанных файлов
            total_size_bytes: Размер обработанных файлов в байтах
            error_reason: Причина ошибки (None = успешно, текст = описание ошибки)
        
        Returns:
            True если успешно сохранено, False в противном случае
        """
        try:
            # Проверяем существование записи
            existing = self.get_match_result(tender_id, registry_type)
            match_id: Optional[int] = existing["id"] if existing else None
            
            # Автоматически устанавливаем is_interesting на основе процента совпадений:
            # - Если найдено 100% совпадение - интересно (True)
            # - Если найдено 85% совпадение - интересно (True)
            # - Если ничего не найдено (match_count = 0) - неинтересно (False)
            if match_count == 0:
                is_interesting_value = False  # Неинтересно, если ничего не найдено
            elif match_percentage >= 85.0:
                is_interesting_value = True  # Интересно, если есть 85% или 100% совпадения
            else:
                is_interesting_value = False  # Неинтересно, если процент меньше 85%
            
            if existing:
                # Обновляем существующую запись
                query = """
                    UPDATE tender_document_matches
                    SET match_count = %s,
                        match_percentage = %s,
                        is_interesting = COALESCE(is_interesting, %s),
                        processed_at = CURRENT_TIMESTAMP,
                        processing_time_seconds = %s,
                        total_files_processed = %s,
                        total_size_bytes = %s
                    WHERE tender_id = %s AND registry_type = %s
                """
                params = (
                    match_count,
                    match_percentage,
                    is_interesting_value,
                    processing_time_seconds,
                    total_files_processed,
                    total_size_bytes,
                    tender_id,
                    registry_type,
                )
            else:
                # Создаем новую запись
                query = """
                    INSERT INTO tender_document_matches (
                        tender_id, registry_type, match_count, match_percentage,
                        is_interesting, processing_time_seconds, total_files_processed, total_size_bytes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    tender_id,
                    registry_type,
                    match_count,
                    match_percentage,
                    is_interesting_value,
                    processing_time_seconds,
                    total_files_processed,
                    total_size_bytes,
                )
            
            self.db_manager.execute_update(query, params)
            if match_id is None:
                match_id = self._fetch_match_id(tender_id, registry_type)
            
            # Выводим детальную информацию о сохраненных данных
            if error_reason:
                logger.warning(
                    f"Сохранена запись об ошибке для закупки {tender_id} ({registry_type}): "
                    f"error_reason={error_reason} (match_id={match_id})"
                )
            else:
                logger.info(
                    f"Сохранен результат поиска для закупки {tender_id} ({registry_type}): "
                    f"{match_count} совпадений, {match_percentage:.1f}% (match_id={match_id})"
                )
                logger.info(
                    f"Детали сохраненных данных в БД: tender_id={tender_id}, registry_type={registry_type}, "
                    f"match_count={match_count}, match_percentage={match_percentage:.2f}%, "
                    f"processing_time={processing_time_seconds or 0.0:.2f} сек, "
                    f"files_processed={total_files_processed}, size_bytes={total_size_bytes}"
                )
            return match_id
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении результата поиска: {e}")
            return None

    def save_match_details(self, match_id: int, details: Sequence[Dict[str, Any]]) -> None:
        """
        Сохраняет детальные совпадения для записи tender_document_matches.
        """
        try:
            # Проверяем существование таблицы
            if not self._table_exists("tender_document_match_details"):
                logger.warning("Таблица tender_document_match_details не существует. Пропускаем сохранение деталей.")
                logger.info("Для создания таблицы выполните SQL скрипт: scripts/create_tender_document_match_details_table.sql")
                return
            
            # Если нет деталей для сохранения, не удаляем существующие
            if not details:
                logger.debug(f"Нет деталей для сохранения (match_id={match_id}), пропускаем обновление")
                return
            
            # Удаляем старые детали только если есть новые для вставки
            delete_query = """
                DELETE FROM tender_document_match_details
                WHERE match_id = %s
            """
            self.db_manager.execute_update(delete_query, (match_id,))

            insert_query = """
                INSERT INTO tender_document_match_details (
                    match_id,
                    product_name,
                    score,
                    sheet_name,
                    row_index,
                    column_letter,
                    cell_address,
                    source_file,
                    matched_text,
                    matched_display_text,
                    matched_keywords,
                    row_data
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Фильтруем совпадения для сохранения - только >= 56% (чтобы показывать все с цветами)
            filtered_details = [m for m in details if m.get("score", 0) >= 56.0]
            
            for match in filtered_details:
                score = match.get("score", 0)
                
                row_data = match.get("row_data") or {}
                matched_keywords = match.get("matched_keywords") or []
                
                # Добавляем полную строку, контекст и имена столбцов в row_data
                enhanced_row_data = {
                    **row_data,
                    "full_row": match.get("full_row", []),
                    "left_context": match.get("left_context", []),
                    "right_context": match.get("right_context", []),
                    "column_names": match.get("column_names", {}),
                }
                
                params = (
                    match_id,
                    match.get("product_name"),
                    score,
                    match.get("sheet_name"),
                    match.get("row"),
                    match.get("column"),
                    match.get("cell_address"),
                    match.get("source_file"),
                    match.get("matched_text"),
                    match.get("matched_display_text"),
                    matched_keywords if matched_keywords else None,
                    json.dumps(enhanced_row_data, ensure_ascii=False),
                )
                self.db_manager.execute_update(insert_query, params)
            
            # Выводим детальную информацию о сохраненных совпадениях
            logger.info(f"Записано детальных совпадений: {len(filtered_details)} из {len(details)} (match_id={match_id}, фильтр >= 56%)")
            if filtered_details:
                logger.info(f"Детали сохраненных совпадений для match_id={match_id}:")
                for idx, match in enumerate(filtered_details[:10], 1):  # Показываем первые 10
                    product_name = match.get('product_name', 'N/A')
                    score = match.get('score', 0.0)
                    sheet_name = match.get('sheet_name', 'N/A')
                    row = match.get('row', 'N/A')
                    cell_address = match.get('cell_address', 'N/A')
                    source_file = match.get('source_file', 'N/A')
                    
                    # Получаем полную строку
                    full_row = match.get('full_row', [])
                    left_context = match.get('left_context', [])
                    right_context = match.get('right_context', [])
                    column_names = match.get('column_names', {})
                    
                    logger.info(
                        f"  {idx}. Товар: {product_name}, "
                        f"Оценка: {score:.2f}%, "
                        f"Лист: {sheet_name}, "
                        f"Строка: {row}, "
                        f"Ячейка: {cell_address}, "
                        f"Файл: {source_file}"
                    )
                    
                    # Выводим полную строку
                    if full_row:
                        row_values = [f"{cell.get('column', '')}:{cell.get('value', '')}" for cell in full_row if cell.get('value')]
                        if row_values:
                            logger.info(f"    Полная строка: {' | '.join(row_values[:10])}" + (" ..." if len(row_values) > 10 else ""))
                    
                    # Выводим контекст слева и справа
                    if left_context:
                        left_values = [f"{cell.get('column', '')}({cell.get('column_name', '')}):{cell.get('value', '')}" 
                                      for cell in left_context if cell.get('value')]
                        if left_values:
                            logger.info(f"    Слева: {' | '.join(left_values)}")
                    
                    if right_context:
                        right_values = [f"{cell.get('column', '')}({cell.get('column_name', '')}):{cell.get('value', '')}" 
                                       for cell in right_context if cell.get('value')]
                        if right_values:
                            logger.info(f"    Справа: {' | '.join(right_values)}")
                    
                    # Выводим имена столбцов
                    if column_names:
                        relevant_columns = {k: v for k, v in list(column_names.items())[:10] if v}
                        if relevant_columns:
                            col_names_str = ', '.join([f"{k}:{v}" for k, v in relevant_columns.items()])
                            logger.info(f"    Имена столбцов: {col_names_str}")
                    
                    logger.info("")  # Пустая строка для разделения
                    
                if len(details) > 10:
                    logger.info(f"  ... и еще {len(details) - 10} совпадений")
        except Exception as error:
            logger.error(f"Ошибка при сохранении деталей совпадений (match_id={match_id}): {error}")
    
    def _table_exists(self, table_name: str) -> bool:
        """
        Проверяет существование таблицы в базе данных.
        
        Args:
            table_name: Имя таблицы для проверки
            
        Returns:
            True если таблица существует, False в противном случае
        """
        try:
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """
            result = self.db_manager.execute_query(query, (table_name,))
            return result[0].get('exists', False) if result else False
        except Exception as error:
            logger.debug(f"Ошибка при проверке существования таблицы {table_name}: {error}")
            return False
    
    def get_match_result(
        self,
        tender_id: int,
        registry_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Получение результата поиска для закупки.
        
        Args:
            tender_id: ID закупки
            registry_type: Тип реестра ('44fz' или '223fz')
        
        Returns:
            Словарь с данными результата или None
        """
        try:
            query = """
                SELECT 
                    id,
                    tender_id,
                    registry_type,
                    match_count,
                    match_percentage,
                    is_interesting,
                    processed_at,
                    processing_time_seconds,
                    total_files_processed,
                    total_size_bytes
                FROM tender_document_matches
                WHERE tender_id = %s AND registry_type = %s
            """
            logger.debug(
                "[get_match_result] tender_id=%s, registry_type=%s",
                tender_id,
                registry_type,
            )
            results = self.db_manager.execute_query(
                query,
                (tender_id, registry_type),
                RealDictCursor
            )
            if results:
                return dict(results[0])
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении результата поиска: {e}")
            return None
    
    def get_match_summary(
        self,
        tender_id: int,
        registry_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Получение сводки по совпадениям для закупки с разбивкой по типам (100%/85%/0%).
        
        Args:
            tender_id: ID закупки
            registry_type: Тип реестра ('44fz' или '223fz')
        
        Returns:
            Словарь с полями:
            - match_result: основной результат из tender_document_matches
            - exact_count: количество совпадений с score >= 100
            - good_count: количество совпадений с 85 <= score < 100
            - total_count: общее количество совпадений
            Или None, если закупка не обработана
        """
        try:
            logger.debug(
                "[get_match_summary] tender_id=%s, registry_type=%s",
                tender_id,
                registry_type,
            )
            match_result = self.get_match_result(tender_id, registry_type)
            if not match_result:
                return None
            
            match_id = match_result.get('id')
            match_count = match_result.get('match_count', 0)
            
            if not match_id:
                return {
                    'match_result': match_result,
                    'exact_count': 0,
                    'good_count': 0,
                    'brown_count': 0,
                    'total_count': match_count,
                }
            
            if not self._table_exists("tender_document_match_details"):
                return {
                    'match_result': match_result,
                    'exact_count': 0,
                    'good_count': 0,
                    'brown_count': 0,
                    'total_count': match_count,
                }
            
            query = """
                SELECT 
                    COUNT(*) FILTER (WHERE score >= 100.0) as exact_count,
                    COUNT(*) FILTER (WHERE score >= 85.0 AND score < 100.0) as good_count,
                    COUNT(*) FILTER (WHERE score >= 56.0 AND score < 85.0) as brown_count,
                    COUNT(*) as total_count
                FROM tender_document_match_details
                WHERE match_id = %s
            """
            results = self.db_manager.execute_query(
                query,
                (match_id,),
                RealDictCursor
            )
            
            stats = {}
            if results:
                stats = dict(results[0])
            
            return {
                'match_result': match_result,
                'exact_count': int(stats.get('exact_count', 0) or 0),
                'good_count': int(stats.get('good_count', 0) or 0),
                'brown_count': int(stats.get('brown_count', 0) or 0),
                'total_count': int(stats.get('total_count', 0) or 0),
                'error_reason': None,  # Колонка error_reason не существует в таблице
            }
            
        except Exception as e:
            logger.error("Ошибка при получении сводки по совпадениям: %s", e)
            return None
    
    def get_match_details(
        self,
        tender_id: int,
        registry_type: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Возвращает детализированные совпадения для закупки.
        
        Args:
            tender_id: ID закупки
            registry_type: Тип реестра ('44fz' или '223fz')
            limit: Максимальное количество записей
        
        Returns:
            Список словарей с информацией о совпадениях
        """
        if limit <= 0:
            return []
        
        try:
            match_result = self.get_match_result(tender_id, registry_type)
            if not match_result:
                return []
            
            match_id = match_result.get('id')
            if not match_id or not self._table_exists("tender_document_match_details"):
                return []
            
            query = """
                SELECT
                    id,
                    product_name,
                    score,
                    sheet_name,
                    row_index,
                    column_letter,
                    cell_address,
                    source_file,
                    matched_text,
                    matched_display_text,
                    row_data
                FROM tender_document_match_details
                WHERE match_id = %s
                ORDER BY score DESC, id ASC
                LIMIT %s
            """
            results = self.db_manager.execute_query(
                query,
                (match_id, limit),
                RealDictCursor,
            )
            return [dict(row) for row in results] if results else []
        except Exception as exc:
            logger.error("Ошибка при получении деталей совпадений: %s", exc)
            return []
    
    def set_interesting_status(
        self,
        tender_id: int,
        registry_type: str,
        is_interesting: Optional[bool],
    ) -> bool:
        """
        Установка статуса интереса для закупки
        
        Args:
            tender_id: ID закупки
            registry_type: Тип реестра ('44fz' или '223fz')
            is_interesting: True = интересно, False = неинтересно, None = сброс статуса
        
        Returns:
            True если успешно обновлено, False в противном случае
        """
        try:
            query = """
                UPDATE tender_document_matches
                SET is_interesting = %s
                WHERE tender_id = %s AND registry_type = %s
            """
            self.db_manager.execute_update(
                query,
                (is_interesting, tender_id, registry_type)
            )
            
            status_text = "интересно" if is_interesting else "неинтересно" if is_interesting is False else "сброшен"
            logger.info(
                f"Установлен статус '{status_text}' для закупки {tender_id} ({registry_type})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при установке статуса интереса: {e}")
            return False
    
    def get_match_results_batch(
        self,
        tender_ids: List[int],
        registry_type: str,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Получение результатов поиска для нескольких закупок (оптимизированная версия)
        
        Args:
            tender_ids: Список ID закупок
            registry_type: Тип реестра ('44fz' или '223fz')
        
        Returns:
            Словарь {tender_id: результат}
        """
        if not tender_ids:
            return {}
        
        try:
            placeholders = ','.join(['%s'] * len(tender_ids))
            query = f"""
                SELECT 
                    id,
                    tender_id,
                    registry_type,
                    match_count,
                    match_percentage,
                    is_interesting,
                    processed_at,
                    processing_time_seconds,
                    total_files_processed,
                    total_size_bytes
                FROM tender_document_matches
                WHERE tender_id IN ({placeholders}) AND registry_type = %s
            """
            params = list(tender_ids) + [registry_type]
            results = self.db_manager.execute_query(
                query,
                tuple(params),
                RealDictCursor
            )
            
            # Группируем результаты по tender_id
            results_dict = {}
            for row in results:
                tender_id = row['tender_id']
                results_dict[tender_id] = dict(row)
            
            return results_dict
            
        except Exception as e:
            logger.error(f"Ошибка при получении результатов поиска (batch): {e}")
            return {}
    
    def filter_uninteresting_tenders(
        self,
        tender_ids: List[int],
        registry_type: str,
    ) -> List[int]:
        """
        Фильтрация неинтересных закупок из списка
        
        Args:
            tender_ids: Список ID закупок
            registry_type: Тип реестра ('44fz' или '223fz')
        
        Returns:
            Список ID закупок, исключая неинтересные (is_interesting = FALSE)
        """
        if not tender_ids:
            return []
        
        try:
            placeholders = ','.join(['%s'] * len(tender_ids))
            query = f"""
                SELECT tender_id
                FROM tender_document_matches
                WHERE tender_id IN ({placeholders})
                    AND registry_type = %s
                    AND is_interesting = FALSE
            """
            params = list(tender_ids) + [registry_type]
            results = self.db_manager.execute_query(
                query,
                tuple(params),
                RealDictCursor
            )
            
            # Получаем список неинтересных ID
            uninteresting_ids = {row['tender_id'] for row in results}
            
            # Возвращаем только интересные или необработанные
            filtered_ids = [tid for tid in tender_ids if tid not in uninteresting_ids]
            
            logger.debug(
                f"Отфильтровано {len(uninteresting_ids)} неинтересных закупок из {len(tender_ids)}"
            )
            return filtered_ids
            
        except Exception as e:
            logger.error(f"Ошибка при фильтрации неинтересных закупок: {e}")
            # В случае ошибки возвращаем все ID
            return tender_ids

    def acquire_tender_lock(self, tender_id: int, registry_type: str, tender_type: str = 'new') -> bool:
        """
        Получение блокировки для тендера (предотвращает параллельную обработку)
        
        Args:
            tender_id: ID тендера
            registry_type: Тип реестра ('44fz' или '223fz')
            tender_type: Тип торгов ('new' для новых, 'won' для завершенных). По умолчанию 'new'.
            
        Returns:
            True если блокировка получена, False если тендер уже обрабатывается другим процессом
        """
        # Генерируем уникальный идентификатор блокировки на основе tender_id, registry_type и tender_type
        # Используем детерминированный способ для создания уникального числа
        # Комбинируем tender_id, registry_type и tender_type в одно число
        # Для 44fz используем 1, для 223fz - 2
        # Для new используем 0, для won - 1
        registry_hash = 1 if registry_type == "44fz" else 2
        tender_type_hash = 0 if tender_type == "new" else 1
        # Используем формулу для генерации уникального lock_id
        # tender_id * 4 + registry_hash * 2 + tender_type_hash гарантирует уникальность
        lock_id = (tender_id * 4 + registry_hash * 2 + tender_type_hash) % (2 ** 31)
        
        try:
            locked = self.db_manager.acquire_advisory_lock(lock_id)
            if locked:
                logger.debug(f"✅ Блокировка получена для тендера {tender_id} ({registry_type}, {tender_type}), lock_id={lock_id}")
            else:
                # Это не ошибка - просто тендер уже обрабатывается другим процессом
                logger.debug(f"⏸️ Тендер {tender_id} ({registry_type}, {tender_type}) уже обрабатывается другим процессом (lock_id={lock_id})")
            return locked
        except (DatabaseQueryError, DatabaseConnectionError) as e:
            # Это реальная ошибка (проблема с БД, например)
            logger.error(f"❌ Ошибка БД при получении блокировки для тендера {tender_id} ({registry_type}, {tender_type}): {e}", exc_info=True)
            return False
        except Exception as e:
            # Неожиданная ошибка
            logger.error(f"❌ Неожиданная ошибка при получении блокировки для тендера {tender_id} ({registry_type}, {tender_type}): {e}", exc_info=True)
            return False
    
    def release_tender_lock(self, tender_id: int, registry_type: str, tender_type: str = 'new') -> bool:
        """
        Освобождение блокировки для тендера
        
        Args:
            tender_id: ID тендера
            registry_type: Тип реестра ('44fz' или '223fz')
            tender_type: Тип торгов ('new' для новых, 'won' для завершенных). По умолчанию 'new'.
            
        Returns:
            True если блокировка освобождена, False в противном случае
        """
        # Используем ту же формулу, что и в acquire_tender_lock
        registry_hash = 1 if registry_type == "44fz" else 2
        tender_type_hash = 0 if tender_type == "new" else 1
        lock_id = (tender_id * 4 + registry_hash * 2 + tender_type_hash) % (2 ** 31)
        
        try:
            unlocked = self.db_manager.release_advisory_lock(lock_id)
            if unlocked:
                logger.debug(f"Блокировка освобождена для тендера {tender_id} ({registry_type}), lock_id={lock_id}")
            return unlocked
        except Exception as e:
            logger.error(f"Ошибка при освобождении блокировки для тендера {tender_id} ({registry_type}): {e}")
            return False
    
    def _fetch_match_id(self, tender_id: int, registry_type: str) -> Optional[int]:
        query = """
            SELECT id FROM tender_document_matches
            WHERE tender_id = %s AND registry_type = %s
        """
        results = self.db_manager.execute_query(
            query,
            (tender_id, registry_type),
            RealDictCursor,
        )
        if results:
            return results[0].get("id")
        return None

