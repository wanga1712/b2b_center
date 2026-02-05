"""
MODULE: services.archive_runner.result_saver
RESPONSIBILITY: Aggregates and saves processing results to DB using repository.
ALLOWED: TenderMatchRepository, logging.
FORBIDDEN: Direct DB queries (use repository).
ERRORS: None.

Модуль сохранения результатов обработки тендера.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from loguru import logger

from services.match_services.tender_match_repository_facade import TenderMatchRepositoryFacade


class ResultSaver:
    """Сохраняет агрегированные результаты обработки в базу данных."""

    def __init__(
        self,
        tender_match_repo: TenderMatchRepositoryFacade,
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
        folder_name: Optional[str] = None,
        failed_files: Optional[List[Dict[str, Any]]] = None,
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
        
        # Определяем, есть ли ошибки обработки файлов
        has_error = bool(failed_files)
        
        logger.info(
            f"💾 Сохранение результатов для торга {tender_id} ({registry_type}): "
            f"совпадений={len(matches)}, файлов={len(workbook_paths)}, "
            f"проблемных файлов={len(failed_files) if failed_files else 0}, "
            f"has_error={has_error}, "
            f"размер={total_size / (1024 * 1024):.2f} МБ, время={processing_time:.1f} сек"
        )
        
        try:
            logger.debug(f"Вызов tender_match_repo.save_match_result для торга {tender_id}...")
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
                folder_name,
                has_error,
            )
            logger.debug(f"save_match_result вернул match_id={match_id} для торга {tender_id}")
            
            
            
            if not match_id:
                
                logger.error(f"❌ Не удалось сохранить итоговую запись для торга {tender_id}")
                return None

            # Сохраняем информацию о проблемных файлах
            if failed_files:
                try:
                    self._call_repo(
                        self.tender_match_repo.save_file_errors,
                        match_id,
                        failed_files,
                    )
                    logger.info(f"💾 Сохранена информация о {len(failed_files)} проблемных файлах для торга {tender_id}")
                except Exception as file_errors_error:
                    logger.error(f"❌ Ошибка при сохранении информации об ошибках файлов для торга {tender_id}: {file_errors_error}")
                    # Не прерываем выполнение, основная запись уже сохранена

            if matches:
                
                
                try:
                    self._call_repo(
                        self.tender_match_repo.save_match_details,
                        match_id,
                        matches,
                    )
                    
                except Exception as details_error:
                    
                    logger.error(f"❌ Ошибка при сохранении детальных совпадений для торга {tender_id}: {details_error}")
                    # Не прерываем выполнение, основная запись уже сохранена
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
        
        
        try:
            if self._safe_call:
                result = self._safe_call(func, *args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            
            
            return result
        except Exception as call_error:
            
            raise


    def create_skipped_result(
        self,
        tender_id: int,
        registry_type: str,
        reason: str,
        match_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Создает результат для пропущенного тендера."""
        result = {
            "tender_id": tender_id,
            "registry_type": registry_type,
            "skipped": True,
            "reason": reason,
        }
        if match_result:
            result.update({
                "match_count": match_result.get("match_count", 0),
                "match_percentage": match_result.get("match_percentage", 0.0),
            })
        else:
            result.update({
                "match_count": 0,
                "match_percentage": 0.0,
            })
        return result

    def save_error_result(
        self,
        tender_id: int,
        registry_type: str,
        error_reason: str,
        error_message: Optional[str] = None,
        folder_name: Optional[str] = None,
        processing_time: float = 0.0,
    ) -> Dict[str, Any]:
        """Сохраняет запись об ошибке в БД и возвращает результат ошибки."""
        error_saved = False
        try:
            self.save(
                tender_id,
                registry_type,
                [],
                [],
                processing_time,
                error_reason=error_reason,
                folder_name=folder_name,
            )
            error_saved = True
        except Exception:
            logger.exception(f"Не удалось сохранить ошибку '{error_reason}' в БД для торга {tender_id}")

        return {
            "tender_id": tender_id,
            "registry_type": registry_type,
            "match_count": 0,
            "match_percentage": 0.0,
            "skipped": True,  # Ошибки часто трактуются как skip обработки
            "reason": error_reason,
            "error_message": error_message or error_reason,
            "error_saved": error_saved,
            "error": True # Явный флаг ошибки
        }

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


