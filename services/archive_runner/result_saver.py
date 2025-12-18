"""
Модуль сохранения результатов обработки тендера.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from loguru import logger

from services.tender_match_repository import TenderMatchRepository


class ResultSaver:
    """Сохраняет агрегированные результаты обработки в базу данных."""

    def __init__(
        self,
        tender_match_repo: TenderMatchRepository,
        safe_call: Optional[Callable[..., Any]] = None,
    ):
        self.tender_match_repo = tender_match_repo
        self._safe_call = safe_call

    def save(
        self,
        tender_id: int,
        registry_type: str,
        matches: List[Dict[str, Any]],
        workbook_paths: List[Path],
        processing_time: float,
        error_reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        exact_count = sum(1 for m in matches if m.get("score", 0) >= 100.0)
        good_count = sum(1 for m in matches if m.get("score", 0) >= 85.0)

        if exact_count > 0:
            match_percentage = 100.0
        elif good_count > 0:
            match_percentage = 85.0
        else:
            match_percentage = 0.0

        total_size = self._calculate_total_size(workbook_paths)

        try:
            match_id = self._call_repo(
                self.tender_match_repo.save_match_result,
                tender_id,
                registry_type,
                len(matches),
                match_percentage,
                processing_time,
                len(workbook_paths),
                total_size,
                error_reason,
            )
            if not match_id:
                logger.error(f"❌ Не удалось сохранить итоговую запись для торга {tender_id}")
                return None

            if matches:
                self._call_repo(
                    self.tender_match_repo.save_match_details,
                    match_id,
                    matches,
                )
            else:
                logger.debug(f"Нет совпадений для торга {tender_id}, детали не обновляются")

            total_size_mb = total_size / (1024 * 1024) if total_size else 0
            logger.info(
                f"💾 tender_document_matches <- tender_id={tender_id}, registry={registry_type}, matches={len(matches)}, files={len(workbook_paths)}, size={total_size_mb:.2f} МБ"
            )
            logger.info(
                f"✅ Торг {tender_id} ({registry_type}) сохранен в БД: совпадений {len(matches)}, процент {match_percentage} (match_id={match_id})"
            )
            return {
                "tender_id": tender_id,
                "registry_type": registry_type,
                "match_count": len(matches),
                "match_percentage": match_percentage,
            }
        except Exception as error:
            logger.error(f"❌ Ошибка записи результатов для торга {tender_id}: {error}")
            logger.exception("Детали ошибки:")
            return None

    def _call_repo(self, func, *args, **kwargs):
        if self._safe_call:
            return self._safe_call(func, *args, **kwargs)
        return func(*args, **kwargs)

    @staticmethod
    def _calculate_total_size(workbook_paths: List[Path]) -> int:
        total_size = 0
        for path in workbook_paths:
            try:
                if path.exists():
                    total_size += path.stat().st_size
            except OSError:
                continue
        return total_size

