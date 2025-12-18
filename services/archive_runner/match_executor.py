"""
Модуль для параллельного поиска совпадений в Excel файлах.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from loguru import logger

from services.error_logger import get_error_logger

from services.document_search.match_finder import MatchFinder


class MatchExecutor:
    """Запускает многопоточный поиск совпадений по списку Excel файлов."""

    def __init__(
        self,
        base_match_finder: MatchFinder,
        max_workers: int = 2,
        get_avg_time_func: Optional[Callable[[], float]] = None,
        batch_delay: float = 5.0,
    ):
        self.base_match_finder = base_match_finder
        self.max_workers = max(1, max_workers)
        self._get_avg_time = get_avg_time_func
        self.batch_delay = max(0.0, batch_delay)

    def run(self, workbook_paths: List[Path]) -> List[Dict[str, Any]]:
        """Возвращает список лучших совпадений по каждому товару."""
        matches: Dict[str, Dict[str, Any]] = {}
        unique_paths = list({Path(p).resolve() for p in workbook_paths})
        total_files = len(unique_paths)
        duplicates_removed = len(workbook_paths) - total_files

        if total_files == 0:
            return []

        if duplicates_removed > 0:
            logger.warning(
                f"Обнаружено {duplicates_removed} дубликатов, будет обработано файлов: {total_files}"
            )
        else:
            logger.info(f"Начинаем обработку {total_files} уникальных файлов")

        workers = min(self.max_workers, total_files)
        
        # Обрабатываем файлы партиями для снижения нагрузки на CPU
        # Размер партии = количество потоков * 2, но не более 10 файлов
        batch_size = min(workers * 2, 10, total_files)

        def process_file(workbook_path: Path) -> Tuple[Path, List[Dict[str, Any]], Optional[Exception], float]:
            start_time = time.time()
            logger.info(f"Начинаем обработку файла: {workbook_path.name}")
            thread_match_finder = MatchFinder(
                self.base_match_finder.product_names,
                stop_phrases=getattr(self.base_match_finder, "stop_phrases", None),
            )
            try:
                # Определяем тип файла
                suffix = workbook_path.suffix.lower()
                is_pdf = suffix == ".pdf"
                is_word = suffix in {".docx", ".doc"}
                
                if is_pdf:
                    # Обрабатываем PDF файлы
                    file_matches = thread_match_finder.search_pdf_for_products(workbook_path)
                    additional_matches = thread_match_finder.search_additional_phrases_in_pdf(workbook_path)
                elif is_word:
                    # Обрабатываем Word документы
                    file_matches = thread_match_finder.search_word_for_products(workbook_path)
                    additional_matches = thread_match_finder.search_additional_phrases_in_word(workbook_path)
                else:
                    # Обрабатываем Excel файлы
                    file_matches = thread_match_finder.search_workbook_for_products(workbook_path)
                    additional_matches = thread_match_finder.search_additional_phrases(workbook_path)
                
                # Объединяем все совпадения
                all_matches = file_matches + additional_matches
                
                elapsed = time.time() - start_time
                
                # Подсчитываем дополнительные фразы отдельно для логирования
                additional_count = sum(1 for m in additional_matches if m.get("is_additional_phrase"))
                
                logger.debug(
                    f"Файл {workbook_path.name} обработан за {elapsed:.1f} сек: "
                    f"основных совпадений {len(file_matches)}, "
                    f"дополнительных фраз {additional_count}, "
                    f"всего {len(all_matches)}"
                )
                
                if additional_count > 0:
                    logger.info(
                        f"Найдено дополнительных фраз в файле {workbook_path.name}: {additional_count}"
                    )
                
                return workbook_path, all_matches, None, elapsed
            except Exception as error:
                elapsed = time.time() - start_time
                logger.error(f"Ошибка при обработке файла {workbook_path.name}: {error}")
                return workbook_path, [], error, elapsed

        avg_time_per_file = self._get_avg_time() if self._get_avg_time else 0.0
        processed_count = 0
        failed_count = 0
        total_elapsed_time = 0.0

        logger.info(f"Запускаем обработку {total_files} файлов в {workers} потоков (партиями по {batch_size} файлов)")
        
        # Обрабатываем файлы партиями для снижения нагрузки на CPU
        batch_number = 0
        
        for batch_start in range(0, total_files, batch_size):
            batch_end = min(batch_start + batch_size, total_files)
            batch_paths = unique_paths[batch_start:batch_end]
            batch_number += 1
            
            logger.info(f"📦 Партия {batch_number}: обработка файлов {batch_start + 1}-{batch_end} из {total_files}")
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_path = {
                    executor.submit(process_file, workbook_path): workbook_path
                    for workbook_path in batch_paths
                }
                
                logger.debug(f"Партия {batch_number}: все задачи отправлены в очередь, ожидаем результаты...")
            
                # Отслеживаем зависшие задачи
                last_progress_log = time.time()

                for future in as_completed(future_to_path):
                    # Логируем, если долго ждем результатов
                    current_time = time.time()
                    if current_time - last_progress_log > 30:
                        remaining_futures = len([f for f in future_to_path.keys() if not f.done()])
                        logger.warning(
                            f"⏳ Ожидание результатов: обработано {processed_count}/{total_files}, "
                            f"ожидаем {remaining_futures} файлов"
                        )
                        last_progress_log = current_time
                    
                    workbook_path = future_to_path[future]
                    processed_count += 1
                    try:
                        file_size_mb = 0
                        try:
                            file_size_mb = workbook_path.stat().st_size / (1024 * 1024)
                        except OSError:
                            pass

                        # Таймаут для обработки одного файла: 5 минут
                        try:
                            _, file_matches, error, elapsed_time = future.result(timeout=300)
                        except FutureTimeoutError:
                            logger.error(
                                f"⏱️ Таймаут обработки файла {workbook_path.name} (превышено 5 минут), пропускаем"
                            )
                            get_error_logger().log_search_error(
                                file_path=workbook_path,
                                error_message="Таймаут обработки (превышено 5 минут)",
                                file_size_mb=file_size_mb,
                                processing_time=300.0,
                            )
                            failed_count += 1
                            continue
                        
                        total_elapsed_time += elapsed_time

                        if error:
                            logger.error(
                                f"Ошибка при поиске по файлу {workbook_path.name} (размер {file_size_mb:.2f} МБ, время {elapsed_time:.1f} сек): {error}"
                            )
                            get_error_logger().log_search_error(
                                file_path=workbook_path,
                                error_message=str(error),
                                file_size_mb=file_size_mb,
                                processing_time=elapsed_time,
                            )
                            failed_count += 1
                        else:
                            if elapsed_time > 120:
                                logger.warning(
                                    f"Файл {workbook_path.name} обрабатывался долго: {elapsed_time:.1f} сек (размер {file_size_mb:.2f} МБ)"
                                )

                            match_info = f"найдено {len(file_matches)} совпадений" if file_matches else "совпадений не найдено"
                            # Логируем информацию о score совпадений для отладки
                            if file_matches:
                                scores = [m.get("score", 0) for m in file_matches]
                                min_score = min(scores) if scores else 0
                                max_score = max(scores) if scores else 0
                                avg_score = sum(scores) / len(scores) if scores else 0
                                logger.debug(
                                    f"Файл {workbook_path.name}: найдено {len(file_matches)} совпадений, "
                                    f"score min={min_score:.1f}, max={max_score:.1f}, avg={avg_score:.1f}"
                                )
                            logger.info(
                                f"✅ Поиск по документу {workbook_path.name} ({processed_count}/{total_files}) — {match_info}, время {elapsed_time:.1f} сек, размер {file_size_mb:.2f} МБ"
                            )

                            for match in file_matches:
                                # Не фильтруем по score здесь - все найденные совпадения должны попасть в результат
                                # Фильтрация по score будет происходить при сохранении в БД
                                product_name = match.get("product_name")
                                if not product_name:
                                    continue
                                existing = matches.get(product_name)
                                if not existing or existing.get("score", 0) < match.get("score", 0):
                                    matches[product_name] = {**match, "source_file": str(workbook_path)}

                        remaining_files = total_files - processed_count
                        if remaining_files > 0:
                            estimated_time_per_file = (
                                avg_time_per_file
                                if avg_time_per_file > 0
                                else (total_elapsed_time / processed_count if processed_count > 0 else 0)
                            )
                            estimated_time_per_file_adjusted = estimated_time_per_file / workers if workers > 0 else estimated_time_per_file
                            estimated_remaining_seconds = remaining_files * estimated_time_per_file_adjusted
                            time_str = self._format_eta(estimated_remaining_seconds)
                            logger.info(
                                f"Прогресс: обработано {processed_count}/{total_files} файлов, осталось примерно {time_str}"
                            )

                    except Exception as error:
                        failed_count += 1
                        logger.error(f"Ошибка при обработке файла {workbook_path.name}: {error}")
                        continue
            
            # Пауза между батчами файлов для охлаждения процессора
            if batch_end < total_files and self.batch_delay > 0:
                remaining_batches = (total_files - batch_end) // batch_size + (1 if (total_files - batch_end) % batch_size > 0 else 0)
                logger.info(f"⏸️  Пауза после партии {batch_number}. Осталось партий: {remaining_batches}. Охлаждение процессора {self.batch_delay:.1f} сек...")
                time.sleep(self.batch_delay)

        logger.info(
            f"Обработка файлов завершена: успешно {processed_count - failed_count}/{total_files}, ошибок {failed_count}, уникальных совпадений {len(matches)}"
        )
        return list(matches.values())

    @staticmethod
    def _format_eta(seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)} сек"
        if seconds < 3600:
            minutes = int(seconds / 60)
            sec = int(seconds % 60)
            return f"{minutes} мин {sec} сек"
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours} ч {minutes} мин"
