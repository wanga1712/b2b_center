"""
Модуль для обработки блокировок файлов.

Если файл заблокирован другим процессом, пытается найти и завершить процесс,
затем повторяет операцию.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar, Any
import time

from loguru import logger

T = TypeVar('T')

# Проверка доступности psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.debug("psutil не установлен, автоматическое завершение процессов будет недоступно")


def try_kill_process_holding_file(file_path: Path) -> bool:
    """
    Пытается найти и завершить процесс, который держит файл.
    
    Args:
        file_path: Путь к заблокированному файлу
        
    Returns:
        True если процесс найден и завершен, False в противном случае
    """
    if not PSUTIL_AVAILABLE:
        logger.debug("psutil недоступен, невозможно определить процесс, держащий файл")
        return False
    
    try:
        file_path_abs = file_path.resolve()
        file_path_str = str(file_path_abs).lower()
        
        # Список процессов, которые могут держать файл
        processes_to_kill = []
        
        for proc in psutil.process_iter():
            try:
                # Получаем открытые файлы процесса
                open_files = proc.open_files()
                for file_info in open_files:
                    try:
                        file_path_to_check = str(Path(file_info.path).resolve()).lower()
                        if file_path_to_check == file_path_str:
                            processes_to_kill.append(proc)
                            logger.info(
                                f"🔪 Найден процесс, держащий файл {file_path.name}: "
                                f"PID={proc.pid}, Name={proc.name()}"
                            )
                            break  # Найден процесс, переходим к следующему
                    except (OSError, ValueError):
                        # Не удалось разрешить путь, пропускаем
                        continue
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Процесс уже завершился или нет доступа
                continue
            except Exception as error:
                logger.debug(f"Ошибка при проверке процесса PID={proc.pid}: {error}")
                continue
        
        if not processes_to_kill:
            logger.debug(f"Не найдено процессов, держащих файл {file_path.name}")
            return False
        
        # Завершаем найденные процессы
        killed_count = 0
        for proc in processes_to_kill:
            try:
                logger.info(f"🔪 Завершаем процесс PID={proc.pid} ({proc.name()})")
                proc.terminate()  # Сначала мягкое завершение
                try:
                    proc.wait(timeout=3)  # Ждем до 3 секунд
                except psutil.TimeoutExpired:
                    # Если не завершился - принудительно
                    logger.warning(f"Процесс {proc.pid} не завершился, принудительное завершение")
                    proc.kill()
                    proc.wait(timeout=1)
                killed_count += 1
                logger.info(f"✅ Процесс PID={proc.pid} успешно завершен")
            except psutil.NoSuchProcess:
                # Процесс уже завершился
                killed_count += 1
            except psutil.AccessDenied:
                logger.warning(f"Нет доступа для завершения процесса PID={proc.pid}")
            except Exception as error:
                logger.warning(f"Ошибка при завершении процесса PID={proc.pid}: {error}")
        
        if killed_count > 0:
            # Даем время процессу освободить файл
            time.sleep(1.0)
            logger.info(f"✅ Завершено {killed_count} процессов, державших файл {file_path.name}")
            return True
        
        return False
    except Exception as error:
        logger.warning(f"Ошибка при поиске процессов, держащих файл {file_path.name}: {error}")
        return False


def handle_file_lock(
    file_path: Path,
    operation: Callable[[], T],
    max_retries: int = 2,
    retry_delay: float = 1.0,
) -> T:
    """
    Выполняет операцию с файлом, обрабатывая блокировки.
    
    Если файл заблокирован другим процессом, пытается найти и завершить процесс,
    затем повторяет операцию.
    
    Args:
        file_path: Путь к файлу
        operation: Функция, которая выполняет операцию с файлом (например, load_workbook)
        max_retries: Максимальное количество попыток
        retry_delay: Задержка между попытками в секундах
        
    Returns:
        Результат выполнения операции
        
    Raises:
        Исключение, если операция не удалась после всех попыток
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except (PermissionError, OSError, IOError) as error:
            last_error = error
            error_code = getattr(error, 'winerror', None) or getattr(error, 'errno', None)
            
            # Коды ошибок блокировки файла в Windows
            # 32 - файл используется другим процессом
            # 13 - доступ запрещен (может быть из-за блокировки)
            is_lock_error = (
                error_code in (32, 13) or
                "being used by another process" in str(error).lower() or
                "permission denied" in str(error).lower() or
                "access is denied" in str(error).lower()
            )
            
            if is_lock_error and attempt < max_retries:
                logger.warning(
                    f"⚠️ Файл {file_path.name} заблокирован другим процессом "
                    f"(попытка {attempt + 1}/{max_retries + 1}). "
                    f"Пытаемся найти и завершить процесс..."
                )
                
                if try_kill_process_holding_file(file_path):
                    # Если процесс завершен, ждем и повторяем
                    time.sleep(retry_delay)
                    logger.info(f"Повторная попытка открыть файл {file_path.name}...")
                    continue
                else:
                    # Процесс не найден или не удалось завершить
                    if attempt < max_retries:
                        logger.warning(
                            f"Не удалось завершить процесс, держащий файл {file_path.name}. "
                            f"Повторная попытка через {retry_delay} сек..."
                        )
                        time.sleep(retry_delay)
                        continue
            
            # Если это не ошибка блокировки или попытки закончились - пробрасываем исключение
            raise
        except Exception as error:
            # Другие ошибки пробрасываем сразу
            raise
    
    # Если дошли сюда - все попытки исчерпаны
    raise last_error

