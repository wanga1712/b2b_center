"""
Репозиторий для работы с данными торгов из базы данных tender_monitor

Предоставляет методы для:
- Получения кодов ОКПД
- Сохранения выбранных пользователем ОКПД
- Получения сохраненных ОКПД пользователя
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from core.tender_database import TenderDatabaseManager
from psycopg2.extras import RealDictCursor


class TenderRepository:
    """
    Репозиторий для работы с данными торгов
    """
    
    def __init__(self, db_manager: TenderDatabaseManager):
        """
        Инициализация репозитория
        
        Args:
            db_manager: Менеджер базы данных tender_monitor
        """
        self.db_manager = db_manager
    
    def search_okpd_codes(
        self, 
        search_text: Optional[str] = None, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Поиск кодов ОКПД по тексту или коду
        
        Args:
            search_text: Текст для поиска (по коду или названию)
            limit: Максимальное количество результатов
        
        Returns:
            Список словарей с данными ОКПД
        """
        try:
            query = """
                SELECT 
                    id,
                    main_code,
                    sub_code,
                    parent_id,
                    name
                FROM collection_codes_okpd
            """
            params = []
            
            if search_text:
                search_text = search_text.strip()
                # Если поиск по числу - ищем по коду, иначе по названию
                if search_text.isdigit() or (search_text.replace('.', '').isdigit()):
                    # Поиск по коду (начинается с введенного значения)
                    query += """
                        WHERE (main_code LIKE %s OR sub_code LIKE %s)
                    """
                    search_pattern = f"{search_text}%"
                    params = [search_pattern, search_pattern]
                else:
                    # Поиск по названию (содержит введенный текст)
                    query += """
                        WHERE LOWER(name) LIKE %s
                    """
                    search_pattern = f"%{search_text.lower()}%"
                    params = [search_pattern]
            
            query += " ORDER BY main_code NULLS LAST, sub_code NULLS LAST LIMIT %s"
            params.append(limit)
            
            results = self.db_manager.execute_query(query, tuple(params) if params else None, RealDictCursor)
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Ошибка при поиске кодов ОКПД: {e}")
            return []
    
    def get_all_okpd_codes(self, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Получение всех кодов ОКПД
        
        Args:
            limit: Максимальное количество результатов
        
        Returns:
            Список словарей с данными ОКПД
        """
        return self.search_okpd_codes(search_text=None, limit=limit)
    
    def get_user_okpd_codes(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получение сохраненных кодов ОКПД пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Список словарей с данными ОКПД пользователя
        """
        try:
            query = """
                SELECT 
                    o.id,
                    o.user_id,
                    o.okpd_code,
                    o.name,
                    o.setting_id,
                    c.main_code,
                    c.sub_code,
                    c.name as okpd_name
                FROM okpd_from_users o
                LEFT JOIN collection_codes_okpd c 
                    ON o.okpd_code = COALESCE(c.sub_code, c.main_code)
                WHERE o.user_id = %s
                ORDER BY o.okpd_code
            """
            results = self.db_manager.execute_query(
                query, 
                (user_id,), 
                RealDictCursor
            )
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Ошибка при получении ОКПД пользователя: {e}")
            return []
    
    def add_user_okpd_code(
        self, 
        user_id: int, 
        okpd_code: str, 
        name: Optional[str] = None,
        setting_id: Optional[int] = None
    ) -> bool:
        """
        Добавление кода ОКПД для пользователя
        
        Args:
            user_id: ID пользователя
            okpd_code: Код ОКПД
            name: Название (опционально)
            setting_id: ID настройки (опционально)
        
        Returns:
            True если успешно добавлено, False в противном случае
        """
        try:
            # Проверяем, не добавлен ли уже этот код
            check_query = """
                SELECT id FROM okpd_from_users 
                WHERE user_id = %s AND okpd_code = %s
            """
            existing = self.db_manager.execute_query(
                check_query, 
                (user_id, okpd_code)
            )
            
            if existing:
                logger.warning(f"ОКПД код {okpd_code} уже добавлен для пользователя {user_id}")
                return False
            
            # Получаем название из таблицы collection_codes_okpd, если не указано
            if not name:
                name_query = """
                    SELECT name FROM collection_codes_okpd
                    WHERE main_code = %s OR sub_code = %s
                    LIMIT 1
                """
                name_result = self.db_manager.execute_query(
                    name_query,
                    (okpd_code, okpd_code),
                    RealDictCursor
                )
                if name_result:
                    name = name_result[0].get('name')
            
            # Добавляем код
            insert_query = """
                INSERT INTO okpd_from_users (user_id, okpd_code, name, setting_id)
                VALUES (%s, %s, %s, %s)
            """
            self.db_manager.execute_update(
                insert_query,
                (user_id, okpd_code, name, setting_id)
            )
            logger.info(f"Добавлен ОКПД код {okpd_code} для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении ОКПД кода: {e}")
            return False
    
    def remove_user_okpd_code(self, user_id: int, okpd_id: int) -> bool:
        """
        Удаление кода ОКПД пользователя
        
        Args:
            user_id: ID пользователя
            okpd_id: ID записи в okpd_from_users
        
        Returns:
            True если успешно удалено, False в противном случае
        """
        try:
            query = """
                DELETE FROM okpd_from_users 
                WHERE id = %s AND user_id = %s
            """
            self.db_manager.execute_update(query, (okpd_id, user_id))
            logger.info(f"Удален ОКПД код (id={okpd_id}) для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при удалении ОКПД кода: {e}")
            return False
    
    def get_okpd_by_code(self, okpd_code: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации об ОКПД по коду
        
        Args:
            okpd_code: Код ОКПД
        
        Returns:
            Словарь с данными ОКПД или None
        """
        try:
            query = """
                SELECT 
                    id,
                    main_code,
                    sub_code,
                    parent_id,
                    name
                FROM collection_codes_okpd
                WHERE main_code = %s OR sub_code = %s
                LIMIT 1
            """
            results = self.db_manager.execute_query(
                query,
                (okpd_code, okpd_code),
                RealDictCursor
            )
            if results:
                return dict(results[0])
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении ОКПД по коду: {e}")
            return None
    
    def get_all_regions(self) -> List[Dict[str, Any]]:
        """
        Получение всех регионов
        
        Returns:
            Список словарей с данными регионов
        """
        try:
            query = """
                SELECT 
                    id,
                    code,
                    name
                FROM region
                ORDER BY name
            """
            results = self.db_manager.execute_query(query, None, RealDictCursor)
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Ошибка при получении регионов: {e}")
            return []
    
    def search_okpd_codes_by_region(
        self, 
        search_text: Optional[str] = None,
        region_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Поиск кодов ОКПД с фильтрацией по региону
        
        Args:
            search_text: Текст для поиска (по коду или названию)
            region_id: ID региона для фильтрации (None = все регионы)
            limit: Максимальное количество результатов
        
        Returns:
            Список словарей с данными ОКПД
        """
        try:
            # Если регион не указан, используем обычный поиск
            if region_id is None:
                return self.search_okpd_codes(search_text, limit)
            
            # Поиск ОКПД, которые используются в торгах выбранного региона
            # Связь через reestr_contract_44_fz и reestr_contract_223_fz
            query = """
                SELECT DISTINCT
                    c.id,
                    c.main_code,
                    c.sub_code,
                    c.parent_id,
                    c.name
                FROM collection_codes_okpd c
                WHERE EXISTS (
                    SELECT 1 FROM reestr_contract_44_fz r44
                    INNER JOIN customer cu ON r44.customer_id = cu.id
                    WHERE r44.okpd_id = c.id 
                    AND cu.region_id = %s
                ) OR EXISTS (
                    SELECT 1 FROM reestr_contract_223_fz r223
                    INNER JOIN customer cu ON r223.customer_id = cu.id
                    WHERE r223.okpd_id = c.id 
                    AND cu.region_id = %s
                )
            """
            params = [region_id, region_id]
            
            if search_text:
                search_text = search_text.strip()
                # Если поиск по числу - ищем по коду, иначе по названию
                if search_text.isdigit() or (search_text.replace('.', '').isdigit()):
                    # Поиск по коду (начинается с введенного значения)
                    query += """
                        AND (c.main_code LIKE %s OR c.sub_code LIKE %s)
                    """
                    search_pattern = f"{search_text}%"
                    params.extend([search_pattern, search_pattern])
                else:
                    # Поиск по названию (содержит введенный текст)
                    query += """
                        AND LOWER(c.name) LIKE %s
                    """
                    search_pattern = f"%{search_text.lower()}%"
                    params.append(search_pattern)
            
            query += " ORDER BY c.main_code NULLS LAST, c.sub_code NULLS LAST LIMIT %s"
            params.append(limit)
            
            results = self.db_manager.execute_query(query, tuple(params), RealDictCursor)
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Ошибка при поиске кодов ОКПД по региону: {e}")
            # В случае ошибки возвращаем обычный поиск
            return self.search_okpd_codes(search_text, limit)
    
    def get_user_stop_words(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получение стоп-слов пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Список словарей с данными стоп-слов
        """
        try:
            query = """
                SELECT 
                    id,
                    user_id,
                    stop_word,
                    setting_id
                FROM stop_words_names
                WHERE user_id = %s
                ORDER BY stop_word
            """
            results = self.db_manager.execute_query(
                query,
                (user_id,),
                RealDictCursor
            )
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Ошибка при получении стоп-слов пользователя: {e}")
            return []
    
    def add_user_stop_words(
        self,
        user_id: int,
        stop_words: List[str],
        setting_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Добавление стоп-слов для пользователя
        
        Args:
            user_id: ID пользователя
            stop_words: Список стоп-слов для добавления
            setting_id: ID настройки (опционально)
        
        Returns:
            Словарь с результатами: {'added': int, 'skipped': int, 'errors': List[str]}
        """
        result = {'added': 0, 'skipped': 0, 'errors': []}
        
        for stop_word in stop_words:
            stop_word = stop_word.strip()
            if not stop_word:
                continue
            
            try:
                # Проверяем, не добавлено ли уже это слово
                check_query = """
                    SELECT id FROM stop_words_names 
                    WHERE user_id = %s AND LOWER(stop_word) = LOWER(%s)
                """
                existing = self.db_manager.execute_query(
                    check_query,
                    (user_id, stop_word)
                )
                
                if existing:
                    result['skipped'] += 1
                    logger.debug(f"Стоп-слово '{stop_word}' уже добавлено для пользователя {user_id}")
                    continue
                
                # Добавляем слово
                insert_query = """
                    INSERT INTO stop_words_names (user_id, stop_word, setting_id)
                    VALUES (%s, %s, %s)
                """
                self.db_manager.execute_update(
                    insert_query,
                    (user_id, stop_word, setting_id)
                )
                result['added'] += 1
                logger.info(f"Добавлено стоп-слово '{stop_word}' для пользователя {user_id}")
                
            except Exception as e:
                error_msg = f"Ошибка при добавлении стоп-слова '{stop_word}': {e}"
                logger.error(error_msg)
                result['errors'].append(error_msg)
        
        return result
    
    def remove_user_stop_word(self, user_id: int, stop_word_id: int) -> bool:
        """
        Удаление стоп-слова пользователя
        
        Args:
            user_id: ID пользователя
            stop_word_id: ID записи в stop_words_names
        
        Returns:
            True если успешно удалено, False в противном случае
        """
        try:
            query = """
                DELETE FROM stop_words_names 
                WHERE id = %s AND user_id = %s
            """
            self.db_manager.execute_update(query, (stop_word_id, user_id))
            logger.info(f"Удалено стоп-слово (id={stop_word_id}) для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при удалении стоп-слова: {e}")
            return False
    
    def get_new_tenders_44fz(
        self,
        user_id: int,
        user_okpd_codes: List[str],
        user_stop_words: List[str],
        region_id: Optional[int] = None,
        limit: int = 1000  # Увеличено по умолчанию до 1000
    ) -> List[Dict[str, Any]]:
        """
        Получение новых торгов 44ФЗ с фильтрацией
        
        Args:
            user_id: ID пользователя
            user_okpd_codes: Список кодов ОКПД пользователя
            user_stop_words: Список стоп-слов пользователя
            region_id: ID региона (None = все регионы)
            limit: Максимальное количество результатов
        
        Returns:
            Список словарей с данными торгов
        """
        try:
            from datetime import date
            
            # Базовый запрос с JOIN для получения связанных данных
            query = """
                SELECT DISTINCT
                    r.id,
                    r.contract_number,
                    r.tender_link,
                    r.start_date,
                    r.end_date,
                    r.delivery_start_date,
                    r.delivery_end_date,
                    r.auction_name,
                    r.initial_price,
                    r.final_price,
                    r.guarantee_amount,
                    r.customer_id,
                    r.contractor_id,
                    r.trading_platform_id,
                    r.okpd_id,
                    r.region_id,
                    r.delivery_region,
                    r.delivery_address,
                    c.customer_short_name,
                    c.customer_full_name,
                    reg.name as region_name,
                    reg.code as region_code,
                    cont.short_name as contractor_short_name,
                    cont.full_name as contractor_full_name,
                    okpd.main_code as okpd_main_code,
                    okpd.sub_code as okpd_sub_code,
                    okpd.name as okpd_name,
                    tp.trading_platform_name as platform_name
                FROM reestr_contract_44_fz r
                LEFT JOIN customer c ON r.customer_id = c.id
                LEFT JOIN region reg ON r.region_id = reg.id
                LEFT JOIN contractor cont ON r.contractor_id = cont.id
                LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
                LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id
                WHERE 1=1
            """
            
            params = []
            
            # Фильтр: только новые торги (end_date >= текущей даты или NULL)
            query += " AND (r.end_date IS NULL OR r.end_date >= %s)"
            params.append(date.today())
            
            # Фильтр по ОКПД пользователя
            if user_okpd_codes:
                placeholders = ','.join(['%s'] * len(user_okpd_codes))
                query += f" AND (okpd.main_code IN ({placeholders}) OR okpd.sub_code IN ({placeholders}))"
                params.extend(user_okpd_codes)
                params.extend(user_okpd_codes)
            else:
                # Если у пользователя нет ОКПД, не показываем ничего
                return []
            
            # Фильтр по региону (если указан в настройках пользователя)
            if region_id is not None:
                query += " AND r.region_id = %s"
                params.append(region_id)
            
            # Исключаем торги со стоп-словами
            if user_stop_words:
                for stop_word in user_stop_words:
                    query += " AND LOWER(r.auction_name) NOT LIKE %s"
                    params.append(f"%{stop_word.lower()}%")
            
            # Получаем общее количество (если нужно) - делаем отдельный запрос с теми же условиями
            total_count = None
            if limit and limit > 0:
                try:
                    # Создаем COUNT запрос с теми же условиями, но без SELECT полей
                    count_query = """
                        SELECT COUNT(DISTINCT r.id) as total_count
                        FROM reestr_contract_44_fz r
                        LEFT JOIN customer c ON r.customer_id = c.id
                        LEFT JOIN region reg ON r.region_id = reg.id
                        LEFT JOIN contractor cont ON r.contractor_id = cont.id
                        LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
                        LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id
                        WHERE 1=1
                    """
                    count_params = []
                    
                    # Добавляем те же условия, что и в основном запросе (без ORDER BY и LIMIT)
                    count_query += " AND (r.end_date IS NULL OR r.end_date >= %s)"
                    count_params.append(date.today())
                    
                    if user_okpd_codes:
                        placeholders = ','.join(['%s'] * len(user_okpd_codes))
                        count_query += f" AND (okpd.main_code IN ({placeholders}) OR okpd.sub_code IN ({placeholders}))"
                        count_params.extend(user_okpd_codes)
                        count_params.extend(user_okpd_codes)
                    
                    if region_id is not None:
                        count_query += " AND r.region_id = %s"
                        count_params.append(region_id)
                    
                    if user_stop_words:
                        for stop_word in user_stop_words:
                            count_query += " AND LOWER(r.auction_name) NOT LIKE %s"
                            count_params.append(f"%{stop_word.lower()}%")
                    
                    count_results = self.db_manager.execute_query(count_query, tuple(count_params), RealDictCursor)
                    if count_results:
                        total_count = count_results[0].get('total_count', 0)
                except Exception as e:
                    logger.debug(f"Не удалось получить общее количество торгов 44ФЗ: {e}")
            
            # Добавляем ORDER BY и LIMIT к основному запросу
            query += " ORDER BY r.start_date DESC, r.id DESC"
            if limit and limit > 0:
                query += " LIMIT %s"
                params.append(limit)
            
            results = self.db_manager.execute_query(query, tuple(params) if params else None, RealDictCursor)
            tenders = [dict(row) for row in results] if results else []
            
            logger.info(f"Загружено торгов 44ФЗ: {len(tenders)} из {total_count if total_count is not None else 'неизвестно'}")
            
            # Оптимизация: загружаем все документы одним запросом
            if tenders:
                tender_ids = [tender['id'] for tender in tenders]
                all_documents = self._get_tender_document_links_44fz_batch(tender_ids)
                # Распределяем документы по торгам
                for tender in tenders:
                    tender['document_links'] = all_documents.get(tender['id'], [])
            
            # Добавляем информацию о количестве в результат
            if tenders and total_count is not None:
                tenders[0]['_total_count'] = total_count
                tenders[0]['_loaded_count'] = len(tenders)
            elif tenders:
                # Если не удалось получить общее количество, используем загруженное
                tenders[0]['_total_count'] = len(tenders) if not limit or len(tenders) < limit else None
                tenders[0]['_loaded_count'] = len(tenders)
            
            return tenders
            
        except Exception as e:
            logger.error(f"Ошибка при получении новых торгов 44ФЗ: {e}")
            return []
    
    def get_new_tenders_223fz(
        self,
        user_id: int,
        user_okpd_codes: List[str],
        user_stop_words: List[str],
        region_id: Optional[int] = None,
        limit: int = 1000  # Увеличено по умолчанию до 1000
    ) -> List[Dict[str, Any]]:
        """
        Получение новых торгов 223ФЗ с фильтрацией
        
        Args:
            user_id: ID пользователя
            user_okpd_codes: Список кодов ОКПД пользователя
            user_stop_words: Список стоп-слов пользователя
            region_id: ID региона (None = все регионы)
            limit: Максимальное количество результатов
        
        Returns:
            Список словарей с данными торгов
        """
        try:
            from datetime import date
            
            # Базовый запрос с JOIN для получения связанных данных
            query = """
                SELECT DISTINCT
                    r.id,
                    r.contract_number,
                    r.tender_link,
                    r.start_date,
                    r.end_date,
                    r.delivery_start_date,
                    r.delivery_end_date,
                    r.auction_name,
                    r.initial_price,
                    r.final_price,
                    r.guarantee_amount,
                    r.customer_id,
                    r.contractor_id,
                    r.trading_platform_id,
                    r.okpd_id,
                    r.region_id,
                    r.delivery_region,
                    r.delivery_address,
                    c.customer_short_name,
                    c.customer_full_name,
                    reg.name as region_name,
                    reg.code as region_code,
                    cont.short_name as contractor_short_name,
                    cont.full_name as contractor_full_name,
                    okpd.main_code as okpd_main_code,
                    okpd.sub_code as okpd_sub_code,
                    okpd.name as okpd_name,
                    tp.trading_platform_name as platform_name
                FROM reestr_contract_223_fz r
                LEFT JOIN customer c ON r.customer_id = c.id
                LEFT JOIN region reg ON r.region_id = reg.id
                LEFT JOIN contractor cont ON r.contractor_id = cont.id
                LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
                LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id
                WHERE 1=1
            """
            
            params = []
            
            # Фильтр: только новые торги (end_date >= текущей даты или NULL)
            query += " AND (r.end_date IS NULL OR r.end_date >= %s)"
            params.append(date.today())
            
            # Фильтр по ОКПД пользователя
            if user_okpd_codes:
                placeholders = ','.join(['%s'] * len(user_okpd_codes))
                query += f" AND (okpd.main_code IN ({placeholders}) OR okpd.sub_code IN ({placeholders}))"
                params.extend(user_okpd_codes)
                params.extend(user_okpd_codes)
            else:
                # Если у пользователя нет ОКПД, не показываем ничего
                return []
            
            # Фильтр по региону (если указан в настройках пользователя)
            if region_id is not None:
                query += " AND r.region_id = %s"
                params.append(region_id)
            
            # Исключаем торги со стоп-словами
            if user_stop_words:
                for stop_word in user_stop_words:
                    query += " AND LOWER(r.auction_name) NOT LIKE %s"
                    params.append(f"%{stop_word.lower()}%")
            
            # Получаем общее количество (если нужно) - делаем отдельный запрос с теми же условиями
            total_count = None
            if limit and limit > 0:
                try:
                    # Создаем COUNT запрос с теми же условиями, но без SELECT полей
                    count_query = """
                        SELECT COUNT(DISTINCT r.id) as total_count
                        FROM reestr_contract_223_fz r
                        LEFT JOIN customer c ON r.customer_id = c.id
                        LEFT JOIN region reg ON r.region_id = reg.id
                        LEFT JOIN contractor cont ON r.contractor_id = cont.id
                        LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
                        LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id
                        WHERE 1=1
                    """
                    count_params = []
                    
                    # Добавляем те же условия, что и в основном запросе (без ORDER BY и LIMIT)
                    count_query += " AND (r.end_date IS NULL OR r.end_date >= %s)"
                    count_params.append(date.today())
                    
                    if user_okpd_codes:
                        placeholders = ','.join(['%s'] * len(user_okpd_codes))
                        count_query += f" AND (okpd.main_code IN ({placeholders}) OR okpd.sub_code IN ({placeholders}))"
                        count_params.extend(user_okpd_codes)
                        count_params.extend(user_okpd_codes)
                    
                    if region_id is not None:
                        count_query += " AND r.region_id = %s"
                        count_params.append(region_id)
                    
                    if user_stop_words:
                        for stop_word in user_stop_words:
                            count_query += " AND LOWER(r.auction_name) NOT LIKE %s"
                            count_params.append(f"%{stop_word.lower()}%")
                    
                    count_results = self.db_manager.execute_query(count_query, tuple(count_params), RealDictCursor)
                    if count_results:
                        total_count = count_results[0].get('total_count', 0)
                except Exception as e:
                    logger.debug(f"Не удалось получить общее количество торгов 223ФЗ: {e}")
            
            # Добавляем ORDER BY и LIMIT к основному запросу
            query += " ORDER BY r.start_date DESC, r.id DESC"
            if limit and limit > 0:
                query += " LIMIT %s"
                params.append(limit)
            
            results = self.db_manager.execute_query(query, tuple(params) if params else None, RealDictCursor)
            tenders = [dict(row) for row in results] if results else []
            
            logger.info(f"Загружено торгов 223ФЗ: {len(tenders)} из {total_count if total_count is not None else 'неизвестно'}")
            
            # Оптимизация: загружаем все документы одним запросом
            if tenders:
                tender_ids = [tender['id'] for tender in tenders]
                all_documents = self._get_tender_document_links_223fz_batch(tender_ids)
                # Распределяем документы по торгам
                for tender in tenders:
                    tender['document_links'] = all_documents.get(tender['id'], [])
            
            # Добавляем информацию о количестве в результат
            if tenders and total_count is not None:
                tenders[0]['_total_count'] = total_count
                tenders[0]['_loaded_count'] = len(tenders)
            elif tenders:
                # Если не удалось получить общее количество, используем загруженное
                tenders[0]['_total_count'] = len(tenders) if not limit or len(tenders) < limit else None
                tenders[0]['_loaded_count'] = len(tenders)
            
            return tenders
            
        except Exception as e:
            logger.error(f"Ошибка при получении новых торгов 223ФЗ: {e}")
            return []
    
    def _get_tender_document_links_44fz(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получение ссылок на документы для торга 44ФЗ"""
        try:
            query = """
                SELECT 
                    id,
                    contract_id,
                    document_links,
                    file_name
                FROM links_documentation_44_fz
                WHERE contract_id = %s
            """
            results = self.db_manager.execute_query(query, (contract_id,), RealDictCursor)
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Ошибка при получении ссылок на документы 44ФЗ: {e}")
            return []
    
    def _get_tender_document_links_44fz_batch(self, contract_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        """Получение ссылок на документы для нескольких торгов 44ФЗ (оптимизированная версия)"""
        if not contract_ids:
            return {}
        
        try:
            placeholders = ','.join(['%s'] * len(contract_ids))
            query = f"""
                SELECT 
                    id,
                    contract_id,
                    document_links,
                    file_name
                FROM links_documentation_44_fz
                WHERE contract_id IN ({placeholders})
            """
            results = self.db_manager.execute_query(query, tuple(contract_ids), RealDictCursor)
            
            # Группируем документы по contract_id
            documents_dict = {}
            for row in results:
                contract_id = row['contract_id']
                if contract_id not in documents_dict:
                    documents_dict[contract_id] = []
                documents_dict[contract_id].append(dict(row))
            
            return documents_dict
        except Exception as e:
            logger.error(f"Ошибка при получении ссылок на документы 44ФЗ (batch): {e}")
            return {}
    
    def _get_tender_document_links_223fz(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получение ссылок на документы для торга 223ФЗ"""
        try:
            query = """
                SELECT 
                    id,
                    contract_id,
                    document_links,
                    file_name
                FROM links_documentation_223_fz
                WHERE contract_id = %s
            """
            results = self.db_manager.execute_query(query, (contract_id,), RealDictCursor)
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Ошибка при получении ссылок на документы 223ФЗ: {e}")
            return []
    
    def _get_tender_document_links_223fz_batch(self, contract_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        """Получение ссылок на документы для нескольких торгов 223ФЗ (оптимизированная версия)"""
        if not contract_ids:
            return {}
        
        try:
            placeholders = ','.join(['%s'] * len(contract_ids))
            query = f"""
                SELECT 
                    id,
                    contract_id,
                    document_links,
                    file_name
                FROM links_documentation_223_fz
                WHERE contract_id IN ({placeholders})
            """
            results = self.db_manager.execute_query(query, tuple(contract_ids), RealDictCursor)
            
            # Группируем документы по contract_id
            documents_dict = {}
            for row in results:
                contract_id = row['contract_id']
                if contract_id not in documents_dict:
                    documents_dict[contract_id] = []
                documents_dict[contract_id].append(dict(row))
            
            return documents_dict
        except Exception as e:
            logger.error(f"Ошибка при получении ссылок на документы 223ФЗ (batch): {e}")
            return {}

