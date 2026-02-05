"""
Тесты для проверки сохранения результатов в TenderProcessor.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from services.archive_runner.tender_processor import TenderProcessor
from services.archive_runner.result_saver import ResultSaver


class TestTenderProcessorSave:
    """Тесты для проверки вызова result_saver.save() в TenderProcessor"""
    
    @pytest.fixture
    def mock_tender_match_repo(self):
        """Мок TenderMatchRepository"""
        repo = Mock()
        repo.get_match_result = Mock(return_value=None)  # Торг не обработан
        repo.save_match_result = Mock(return_value=123)
        repo.save_match_details = Mock()
        return repo
    
    @pytest.fixture
    def mock_result_saver(self, mock_tender_match_repo):
        """Мок ResultSaver"""
        saver = Mock(spec=ResultSaver)
        saver.save = Mock(return_value={
            "tender_id": 12345,
            "registry_type": "44fz",
            "match_count": 2,
            "match_percentage": 100.0,
        })
        saver.tender_match_repo = mock_tender_match_repo
        return saver
    
    @pytest.fixture
    def mock_match_executor(self):
        """Мок MatchExecutor"""
        executor = Mock()
        executor.run = Mock(return_value=[
            {"product_name": "Товар 1", "score": 100.0},
            {"product_name": "Товар 2", "score": 100.0},
        ])
        return executor
    
    @pytest.fixture
    def mock_workbook_manager(self):
        """Мок WorkbookManager"""
        manager = Mock()
        manager.prepare_workbook_paths = Mock(return_value=(
            [Path("/tmp/file1.xlsx"), Path("/tmp/file2.xlsx")],  # workbook_paths
            [],  # archive_paths
            [],  # excel_paths
        ))
        return manager
    
    @pytest.fixture
    def mock_folder_manager(self):
        """Мок TenderFolderManager"""
        manager = Mock()
        folder_path = Path("/tmp/44fz_12345")
        folder_path.mkdir(parents=True, exist_ok=True)
        manager.prepare_tender_folder = Mock(return_value=folder_path)
        return manager
    
    @pytest.fixture
    def tender_processor(self, mock_result_saver, mock_match_executor, 
                        mock_workbook_manager, mock_folder_manager):
        """Создание TenderProcessor с моками"""
        processor = TenderProcessor(
            tender_match_repo=Mock(),
            folder_manager=mock_folder_manager,
            document_search_service=Mock(),
            selector=Mock(),
            downloader=Mock(),
            extractor=Mock(),
            match_finder=Mock(),
            file_cleaner=Mock(),
            max_workers=2,
            safe_call_func=None,
            get_avg_time_func=None,
            batch_delay=5.0,
        )
        # Заменяем внутренние компоненты на моки
        processor.result_saver = mock_result_saver
        processor.match_executor = mock_match_executor
        processor.workbook_manager = mock_workbook_manager
        processor.download_manager = Mock()
        return processor
    
    def test_process_tender_calls_result_saver_save(self, tender_processor, mock_result_saver, mock_folder_manager, tmp_path):
        """Тест, что process_tender вызывает result_saver.save() после обработки"""
        # Создаем реальные файлы для теста
        test_file1 = tmp_path / "file1.xlsx"
        test_file1.write_bytes(b"test content")
        test_file2 = tmp_path / "file2.xlsx"
        test_file2.write_bytes(b"test content")
        
        # Настраиваем folder_manager для возврата реальной папки
        folder_path = tmp_path / "44fz_12345"
        folder_path.mkdir()
        mock_folder_manager.prepare_tender_folder.return_value = folder_path
        
        # Копируем файлы в папку
        import shutil
        shutil.copy(test_file1, folder_path / "file1.xlsx")
        shutil.copy(test_file2, folder_path / "file2.xlsx")
        
        tender = {
            "id": 12345,
            "registry_type": "44fz",
            "auction_name": "Тестовый торг",
        }
        existing_records = [
            {
                "doc": None,
                "paths": [folder_path / "file1.xlsx"],
                "source": "existing",
            }
        ]
        
        result = tender_processor.process_tender(
            tender=tender,
            existing_records=existing_records,
            processed_tenders_cache={},
            tender_type="new",
        )
        
        # Проверяем, что result_saver.save был вызван
        assert mock_result_saver.save.called, "result_saver.save() должен быть вызван"
        
        # Проверяем параметры вызова
        call_args = mock_result_saver.save.call_args
        # save() вызывается с позиционными аргументами
        args = call_args[0]
        assert args[0] == 12345  # tender_id
        assert args[1] == "44fz"  # registry_type
        assert len(args[2]) == 2  # matches (2 совпадения из match_executor)
        assert len(args[3]) >= 1  # workbook_paths (хотя бы 1 файл)
        assert args[4] > 0  # processing_time > 0
        # Проверяем folder_name, если он передан (может быть 6-м или 7-м параметром)
        if len(args) > 6:
            assert args[6] == "44fz_12345"  # folder_name
        elif len(args) > 5 and args[5] is None:
            # Если error_reason=None, то folder_name может быть 6-м параметром
            pass  # folder_name может быть передан как именованный параметр
        
        # Проверяем результат
        assert result is not None
        assert result.get("tender_id") == 12345
    
    def test_process_tender_saves_folder_name(self, tender_processor, mock_result_saver, mock_folder_manager, tmp_path):
        """Тест, что folder_name передается в result_saver.save()"""
        # Создаем реальные файлы для теста
        test_file = tmp_path / "file1.xlsx"
        test_file.write_bytes(b"test content")
        
        # Настраиваем folder_manager для возврата конкретного пути
        folder_path = tmp_path / "223fz_12346"
        folder_path.mkdir()
        mock_folder_manager.prepare_tender_folder.return_value = folder_path
        
        # Копируем файл в папку
        import shutil
        shutil.copy(test_file, folder_path / "file1.xlsx")
        
        tender = {
            "id": 12346,
            "registry_type": "223fz",
            "auction_name": "Тестовый торг 2",
        }
        existing_records = [
            {
                "doc": None,
                "paths": [folder_path / "file1.xlsx"],
                "source": "existing",
            }
        ]
        
        tender_processor.process_tender(
            tender=tender,
            existing_records=existing_records,
            processed_tenders_cache={},
            tender_type="new",
        )
        
        # Проверяем, что folder_name был передан
        call_args = mock_result_saver.save.call_args
        args = call_args[0]
        # folder_name может быть передан как позиционный или именованный параметр
        if len(args) > 6:
            assert args[6] == "223fz_12346"  # folder_name
        else:
            # Проверяем именованные параметры
            kwargs = call_args[1] if len(call_args) > 1 else {}
            assert kwargs.get("folder_name") == "223fz_12346" or args[-1] == "223fz_12346"
    
    def test_process_tender_saves_with_error(self, tender_processor, mock_result_saver):
        """Тест сохранения ошибки при отсутствии workbook_paths"""
        tender = {
            "id": 12347,
            "registry_type": "44fz",
            "auction_name": "Тестовый торг 3",
        }
        existing_records = []
        
        # Мокируем prepare_workbook_paths для возврата пустого списка
        tender_processor.workbook_manager.prepare_workbook_paths = Mock(return_value=(
            [],  # workbook_paths пустой
            [],
            [],
        ))
        
        result = tender_processor.process_tender(
            tender=tender,
            existing_records=existing_records,
            processed_tenders_cache={},
            tender_type="new",
        )
        
        # Проверяем, что result_saver.save был вызван с error_reason
        assert mock_result_saver.save.called
        call_args = mock_result_saver.save.call_args
        args = call_args[0]
        # error_reason может быть 5-м или 6-м параметром
        if len(args) > 5:
            assert args[5] == "no_workbook_files" or args[5] == "no_documents"  # error_reason
        else:
            # Проверяем именованные параметры
            kwargs = call_args[1] if len(call_args) > 1 else {}
            assert kwargs.get("error_reason") in ["no_workbook_files", "no_documents"]
    
    def test_process_tender_skips_already_processed(self, tender_processor, mock_result_saver):
        """Тест, что уже обработанные торги пропускаются"""
        tender = {
            "id": 12348,
            "registry_type": "44fz",
            "auction_name": "Тестовый торг 4",
        }
        processed_tenders_cache = {
            (12348, "44fz"): {
                "id": 1,
                "tender_id": 12348,
                "registry_type": "44fz",
                "match_count": 5,
                "processed_at": "2025-01-01 12:00:00",
            }
        }
        
        result = tender_processor.process_tender(
            tender=tender,
            existing_records=[],
            processed_tenders_cache=processed_tenders_cache,
            tender_type="new",
        )
        
        # Проверяем, что result_saver.save НЕ был вызван
        assert not mock_result_saver.save.called, "result_saver.save() не должен вызываться для уже обработанных торгов"
        
        # Проверяем, что результат содержит skipped
        assert result is not None
        assert result.get("skipped") is True

