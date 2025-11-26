"""
Модуль для поиска совпадений товаров в документах.

Класс MatchFinder отвечает за:
- Извлечение ключевых слов из названий товаров
- Поиск совпадений в тексте с учетом опечаток
- Оценку качества совпадений
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

from loguru import logger
from rapidfuzz import fuzz

from services.document_search.excel_parser import ExcelParser


class MatchFinder:
    """Класс для поиска совпадений товаров в документах."""

    def __init__(self, product_names: List[str]):
        """
        Args:
            product_names: Список названий товаров для поиска
        """
        self.product_names = product_names
        self._product_patterns: Optional[Dict[str, Dict[str, Any]]] = None
        self._excel_parser = ExcelParser()
        self._additional_phrases: Optional[List[str]] = None

    def search_workbook_for_products(self, file_path: Path) -> List[Dict[str, Any]]:
        """Парсинг Excel и поиск совпадений с названиями товаров по ключевым словам."""
        if not self.product_names:
            logger.warning("Список товаров пуст, поиск не будет выполнен.")
            return []

        if self._product_patterns is None:
            self._prepare_product_patterns()

        found_matches: Dict[str, Dict[str, Any]] = {}

        for cell_info in self._excel_parser.iter_workbook_cells(file_path):
            text = cell_info["text"]
            display_text = cell_info["display_text"]
            cell_matches: List[Tuple[str, Dict[str, Any]]] = []

            for product_name, pattern in self._product_patterns.items():
                match_result = self._check_keywords_match(text, pattern, product_name)
                if match_result["found"]:
                    cell_matches.append((product_name, match_result))

            if not cell_matches:
                continue

            full_matches = [
                (product_name, match_result)
                for product_name, match_result in cell_matches
                if match_result["full_match"]
            ]
            if full_matches:
                matches_to_apply = full_matches
            else:
                matches_to_apply = cell_matches

            best_product, best_match = max(matches_to_apply, key=lambda item: item[1]["score"])

            existing = found_matches.get(best_product)
            if existing and existing.get("score", 0) >= best_match["score"]:
                continue

            row_data = self._excel_parser.extract_row_data(
                file_path,
                cell_info["sheet_name"],
                cell_info["row"]
            )
            
            # Получаем полную строку с контекстом
            full_row_context = self._excel_parser.extract_full_row_with_context(
                file_path,
                cell_info["sheet_name"],
                cell_info["row"],
                cell_info["column"],
                context_cols=3
            )
            
            found_matches[best_product] = {
                "product_name": best_product,
                "score": best_match["score"],
                "matched_text": text,
                "matched_display_text": display_text,
                "sheet_name": cell_info["sheet_name"],
                "row": cell_info["row"],
                "column": cell_info["column"],
                "cell_address": cell_info["cell_address"],
                "matched_keywords": best_match["matched_keywords"],
                "row_data": row_data,
                "full_row": full_row_context.get("full_row", []),
                "left_context": full_row_context.get("left_context", []),
                "right_context": full_row_context.get("right_context", []),
                "column_names": full_row_context.get("column_names", {}),
            }

        # Фильтруем только совпадения с оценкой >= 85 (100% и 85%)
        filtered_matches = [
            match for match in found_matches.values()
            if match.get("score", 0) >= 85.0
        ]
        
        sorted_matches = sorted(filtered_matches, key=lambda item: item["score"], reverse=True)
        
        # Освобождаем память после обработки файла
        import gc
        gc.collect()
        
        return sorted_matches[:50]

    def _get_additional_search_phrases(self) -> List[str]:
        """
        Генерация дополнительных фраз для поиска по документации.
        
        Returns:
            Список фраз для поиска (в нижнем регистре)
        """
        if self._additional_phrases is not None:
            return self._additional_phrases
        
        phrases = []
        
        # 1. Композитные перильные ограждения - вариации
        composite_railing_phrases = [
            "композитное перильное ограждение",
            "композитные перильные ограждения",
            "перильное ограждение композитное",
            "перильные ограждения композитные",
            "перильные ограждения из композита",
            "перильное ограждение из композита",
            "композитное ограждение перильное",
            "композитные ограждения перильные",
            "стеклопластиковые перильные ограждения",
            "перильные ограждения стеклопластиковые",
            "перильные ограждения из стеклопластика",
            "перильное ограждение из стеклопластика",
            "стеклопластиковое перильное ограждение",
            "перильное ограждение стеклопластиковое",
            "перильные ограждения композит",
            "перильное ограждение композит",
            "композит перильные ограждения",
            "композит перильное ограждение",
        ]
        phrases.extend(composite_railing_phrases)
        
        # 2. Система внешнего армирования - вариации
        external_reinforcement_phrases = [
            "система внешнего армирования",
            "внешнее армирование",
            "армирование внешнее",
            "система армирования внешнего",
            "усиление углеволокном",
            "армирование углеволокном",
            "углеволокно для армирования",
            "армирование углеродным волокном",
            "усиление углеродным волокном",
            "fibarm",
            "carbonwrap",
            "monsterlot",
            "sika",
            "mapei",
        ]
        phrases.extend(external_reinforcement_phrases)
        
        # 3. Композитные водоотводные лотки - вариации
        composite_drainage_phrases = [
            "композитные водоотводные лотки",
            "водоотводные лотки композитные",
            "композитный водоотводный лоток",
            "водоотводный лоток композитный",
            "лотки водоотводные композитные",
            "лоток водоотводный композитный",
            "подвесные водоотводные лотки композитные",
            "композитные подвесные водоотводные лотки",
            "водоотводные лотки подвесные композитные",
            "подвесные композитные водоотводные лотки",
            "стеклопластиковые водоотводные лотки",
            "водоотводные лотки стеклопластиковые",
            "стеклопластиковый водоотводный лоток",
            "водоотводный лоток стеклопластиковый",
            "полимерные водоотводные лотки",
            "водоотводные лотки полимерные",
            "полимерный водоотводный лоток",
            "водоотводный лоток полимерный",
            "композитные лотки водоотводные",
            "композитный лоток водоотводный",
            "водоотводные лотки из композита",
            "водоотводный лоток из композита",
            "лотки из композита водоотводные",
            "лоток из композита водоотводный",
        ]
        phrases.extend(composite_drainage_phrases)

        # 4. Инъектирование и гидроизоляция - вариации
        injection_phrases = [
            "инъектирование",
            "иньектирование",
            "инъектировать",
            "инъекционные работы",
            "инъекционная гидроизоляция",
            "инъекционное заполнение",
            "инъекционная система",
            "гидроизоляция",
            "гидроизоляции",
            "гидроизоляционные работы",
            "гидроизоляционные материалы",
            "гидроизоляционные системы",
            "гидроизоляционный состав",
            "гидроизоляционные решения",
        ]
        phrases.extend(injection_phrases)

        # 5. Наливные полы - вариации
        self_leveling_phrases = [
            "наливные полы",
            "наливных полов",
            "наливной пол",
            "наливного пола",
            "наливные покрытия",
            "наливное покрытие",
            "наливной состав",
            "наливные смеси",
        ]
        phrases.extend(self_leveling_phrases)

        # 6. Промышленные полы - вариации
        industrial_floor_phrases = [
            "промышленные полы",
            "промышленных полов",
            "промышленный пол",
            "промышленного пола",
            "промышленные покрытия",
            "промышленное покрытие",
        ]
        phrases.extend(industrial_floor_phrases)

        # 7. Усиление конструкций - вариации
        reinforcement_phrases = [
            "усиление конструкций",
            "усиление конструкции",
            "усиление несущих конструкций",
            "усиление железобетонных конструкций",
            "усиление железобетонной конструкции",
            "усиление жб конструкций",
            "усиление жб конструкции",
            "усиление зданий",
            "усиление сооружений",
        ]
        phrases.extend(reinforcement_phrases)
        
        # Нормализуем все фразы (нижний регистр, убираем лишние пробелы)
        normalized_phrases = []
        for phrase in phrases:
            normalized = re.sub(r'\s+', ' ', phrase.strip().casefold())
            if normalized:
                normalized_phrases.append(normalized)
        
        self._additional_phrases = normalized_phrases
        logger.debug(f"Сгенерировано {len(normalized_phrases)} дополнительных фраз для поиска")
        return normalized_phrases

    def search_additional_phrases(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Поиск дополнительных фраз в документах.
        
        Args:
            file_path: Путь к Excel файлу
            
        Returns:
            Список найденных совпадений с дополнительными фразами
        """
        phrases = self._get_additional_search_phrases()
        if not phrases:
            return []
        
        found_matches: Dict[str, Dict[str, Any]] = {}
        
        for cell_info in self._excel_parser.iter_workbook_cells(file_path):
            text = cell_info["text"]
            text_lower = text.casefold()
            
            # Ищем каждую фразу в тексте
            for phrase in phrases:
                if phrase in text_lower:
                    # Если фраза найдена, создаем совпадение
                    product_name = phrase  # Используем саму фразу как название
                    
                    existing = found_matches.get(product_name)
                    if existing:
                        # Если уже есть совпадение, проверяем оценку
                        if existing.get("score", 0) >= 85.0:
                            continue
                    
                    row_data = self._excel_parser.extract_row_data(
                        file_path,
                        cell_info["sheet_name"],
                        cell_info["row"]
                    )
                    
                    full_row_context = self._excel_parser.extract_full_row_with_context(
                        file_path,
                        cell_info["sheet_name"],
                        cell_info["row"],
                        cell_info["column"],
                        context_cols=3
                    )
                    
                    found_matches[product_name] = {
                        "product_name": product_name,
                        "score": 85.0,  # Фиксированная оценка для дополнительных фраз
                        "matched_text": text,
                        "matched_display_text": cell_info["display_text"],
                        "sheet_name": cell_info["sheet_name"],
                        "row": cell_info["row"],
                        "column": cell_info["column"],
                        "cell_address": cell_info["cell_address"],
                        "matched_keywords": [phrase],
                        "row_data": row_data,
                        "full_row": full_row_context.get("full_row", []),
                        "left_context": full_row_context.get("left_context", []),
                        "right_context": full_row_context.get("right_context", []),
                        "column_names": full_row_context.get("column_names", {}),
                        "is_additional_phrase": True,  # Флаг, что это дополнительная фраза
                    }
        
        return list(found_matches.values())

    def _prepare_product_patterns(self) -> None:
        """Подготовка паттернов поиска для каждого товара."""
        self._product_patterns = {}
        for product_name in self.product_names:
            pattern = self._extract_keywords(product_name)
            if pattern:
                self._product_patterns[product_name] = pattern

    def _extract_keywords(self, product_name: str) -> Optional[Dict[str, Any]]:
        """
        Извлечение ключевых слов из названия товара.
        
        Примеры:
        - "ДенсТоп ЭП 203 (Комплект_1)" -> ["денстоп", "эп", "203"]
        - "Реолен Адмикс Плюс" -> ["реолен", "адмикс", "плюс"]
        """
        cleaned = re.sub(r'\([^)]*\)', '', product_name).strip()
        if not cleaned:
            return None

        keywords: List[str] = []
        normalized_full_name = re.sub(r'\s+', ' ', cleaned).casefold()
        full_phrase = normalized_full_name if len(normalized_full_name) >= 3 else None

        words = re.findall(r'[а-яёА-ЯЁa-zA-Z0-9]+', cleaned, re.IGNORECASE)

        for word in words:
            word_lower = word.casefold()
            if len(word_lower) < 3:
                continue
            if word_lower.isdigit():
                continue
            keywords.append(word_lower)

        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword)

        if not keywords and not full_phrase:
            return None

        return {
            "full_phrase": full_phrase,
            "tokens": unique_keywords,
        }

    def _check_keywords_match(
        self,
        text: str,
        pattern: Dict[str, Any],
        product_name: str
    ) -> Dict[str, Any]:
        """
        Проверка наличия ключевых слов в тексте с учетом возможных опечаток.
        
        Returns:
            Dict с полями:
            - found: bool - найдены ли ключевые слова
            - score: float - процент совпадения
            - matched_keywords: List[str] - список найденных ключевых слов
            - full_match: bool - точное совпадение
        """
        keywords = pattern.get("tokens", [])
        full_phrase = pattern.get("full_phrase")

        if not keywords and not full_phrase:
            return {"found": False, "score": 0.0, "matched_keywords": [], "full_match": False}
        
        text_lower = text.casefold()
        matched_keywords = []

        product_name_clean = re.sub(r'\([^)]*\)', '', product_name).strip()
        product_name_normalized = re.sub(r'\s+', ' ', product_name_clean).casefold()
        
        if product_name_normalized and product_name_normalized in text_lower:
            return {
                "found": True,
                "score": 100.0,
                "matched_keywords": [product_name_normalized],
                "full_match": True,
            }

        if full_phrase and full_phrase in text_lower:
            matched_keywords.append(full_phrase)
            return {
                "found": True,
                "score": 100.0,
                "matched_keywords": matched_keywords,
                "full_match": True,
            }
        
        for keyword in keywords:
            if keyword in text_lower:
                matched_keywords.append(keyword)
                continue
            
            if len(keyword) >= 3:
                words_in_text = re.findall(r'[а-яёА-ЯЁa-zA-Z0-9]+', text_lower)
                for word in words_in_text:
                    if len(word) >= 3:
                        similarity = fuzz.ratio(keyword, word)
                        if similarity >= 85:
                            matched_keywords.append(keyword)
                            break
        
        if not matched_keywords:
            return {"found": False, "score": 0.0, "matched_keywords": [], "full_match": False}
        
        keywords_ratio = len(matched_keywords) / len(keywords) if keywords else 0
        
        if keywords_ratio >= 0.6:
            score = 85.0 + (keywords_ratio - 0.6) * 15.0
        elif keywords_ratio >= 0.3:
            score = 35.0 + (keywords_ratio - 0.3) * 50.0
        else:
            return {"found": False, "score": 0.0, "matched_keywords": [], "full_match": False}
        
        return {
            "found": True,
            "score": score,
            "matched_keywords": matched_keywords,
            "full_match": False,
        }

