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
            }

        sorted_matches = sorted(found_matches.values(), key=lambda item: item["score"], reverse=True)
        return sorted_matches[:50]

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

