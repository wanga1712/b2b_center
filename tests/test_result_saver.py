"""
Тесты для модуля сохранения результатов обработки тендеров.
"""

import pytest
from unittest.mock import Mock, MagicMock, call
from pathlib import Path
from services.archive_runner.result_saver import ResultSaver
from services.match_services.tender_match_repository_facade import TenderMatchRepositoryFacade


class TestResultSaver:
    """Тесты для ResultSaver"""
    
    @pytest.fixture
    def mock_tender_match_repo(self):
        """Мок репозитория для сохранения результатов"""
        repo = Mock(spec=TenderMatchRepositoryFacade)
        repo.save_match_result = Mock(return_value=123)  # Возвращаем match_id
        repo.save_match_details = Mock()
        return repo
    
    @pytest.fixture
    def result_saver(self, mock_tender_match_repo):
        """Создание ResultSaver с мок-репозиторием"""
        return ResultSaver(mock_tender_match_repo, safe_call=None)
    
    def test_save_with_matches(self, result_saver, mock_tender_match_repo):
        """Тест сохранения результатов с найденными совпадениями"""
        matches = [
            {"product_name": "Товар 1", "score": 100.0},
            {"product_name": "Товар 2", "score": 85.0},
            {"product_name": "Товар 3", "score": 50.0},
        ]
        workbook_paths = [Path("/tmp/file1.xlsx"), Path("/tmp/file2.xlsx")]
        
        result = result_saver.save(
            tender_id=12345,
            registry_type="44fz",
            matches=matches,
            workbook_paths=workbook_paths,
            processing_time=10.5,
            error_reason=None,
            folder_name="44fz_12345",
        )
        
        # Проверяем, что save_match_result был вызван с правильными параметрами
        mock_tender_match_repo.save_match_result.assert_called_once_with(
            12345,  # tender_id
            "44fz",  # registry_type
            3,  # match_count (len(matches))
            100.0,  # match_percentage (есть exact match)
            10.5,  # processing_time
            2,  # total_files_processed (len(workbook_paths))
            pytest.approx(0, abs=1),  # total_size_bytes (файлы не существуют)
            None,  # error_reason
            "44fz_12345",  # folder_name
            False,  # has_error
        )
        
        # Проверяем, что save_match_details был вызван
        mock_tender_match_repo.save_match_details.assert_called_once_with(123, matches)
        
        # Проверяем возвращаемое значение
        assert result is not None
        assert result["tender_id"] == 12345
        assert result["match_count"] == 3
        assert result["match_percentage"] == 100.0
    
    def test_save_with_good_matches(self, result_saver, mock_tender_match_repo):
        """Тест сохранения результатов с хорошими совпадениями (85%)"""
        matches = [
            {"product_name": "Товар 1", "score": 85.0},
            {"product_name": "Товар 2", "score": 90.0},
        ]
        workbook_paths = [Path("/tmp/file1.xlsx")]
        
        result = result_saver.save(
            tender_id=12346,
            registry_type="223fz",
            matches=matches,
            workbook_paths=workbook_paths,
            processing_time=5.0,
            error_reason=None,
            folder_name="223fz_12346",
        )
        
        # Проверяем, что match_percentage = 85.0 (нет exact, но есть good)
        mock_tender_match_repo.save_match_result.assert_called_once()
        call_args = mock_tender_match_repo.save_match_result.call_args[0]
        assert call_args[3] == 85.0  # match_percentage
        
        assert result["match_percentage"] == 85.0
    
    def test_save_with_no_matches(self, result_saver, mock_tender_match_repo):
        """Тест сохранения результатов без совпадений"""
        matches = []
        workbook_paths = [Path("/tmp/file1.xlsx")]
        
        result = result_saver.save(
            tender_id=12347,
            registry_type="44fz",
            matches=matches,
            workbook_paths=workbook_paths,
            processing_time=2.0,
            error_reason=None,
            folder_name="44fz_12347",
        )
        
        # Проверяем, что match_percentage = 0.0
        mock_tender_match_repo.save_match_result.assert_called_once()
        call_args = mock_tender_match_repo.save_match_result.call_args[0]
        assert call_args[3] == 0.0  # match_percentage
        
        # Проверяем, что save_match_details НЕ был вызван (нет совпадений)
        mock_tender_match_repo.save_match_details.assert_not_called()
        
        assert result["match_count"] == 0
        assert result["match_percentage"] == 0.0
    
    def test_save_with_error_reason(self, result_saver, mock_tender_match_repo):
        """Тест сохранения результатов с ошибкой"""
        result = result_saver.save(
            tender_id=12348,
            registry_type="44fz",
            matches=[],
            workbook_paths=[],
            processing_time=1.0,
            error_reason="no_workbook_files",
            folder_name="44fz_12348",
        )
        
        # Проверяем, что error_reason был передан
        mock_tender_match_repo.save_match_result.assert_called_once()
        call_args = mock_tender_match_repo.save_match_result.call_args[0]
        assert call_args[7] == "no_workbook_files"  # error_reason
    
    def test_save_with_folder_name_none(self, result_saver, mock_tender_match_repo):
        """Тест сохранения результатов без folder_name"""
        result = result_saver.save(
            tender_id=12349,
            registry_type="44fz",
            matches=[],
            workbook_paths=[],
            processing_time=1.0,
            error_reason=None,
            folder_name=None,
        )
        
        # Проверяем, что folder_name=None был передан
        mock_tender_match_repo.save_match_result.assert_called_once()
        call_args = mock_tender_match_repo.save_match_result.call_args[0]
        assert call_args[8] is None  # folder_name
    
    def test_save_failure_returns_none(self, result_saver, mock_tender_match_repo):
        """Тест обработки ошибки при сохранении"""
        # Мокируем ошибку при сохранении
        mock_tender_match_repo.save_match_result.return_value = None
        
        result = result_saver.save(
            tender_id=12350,
            registry_type="44fz",
            matches=[],
            workbook_paths=[],
            processing_time=1.0,
            error_reason=None,
            folder_name="44fz_12350",
        )
        
        # Проверяем, что вернулся None
        assert result is None
    
    def test_save_with_exception(self, result_saver, mock_tender_match_repo):
        """Тест обработки исключения при сохранении"""
        # Мокируем исключение
        mock_tender_match_repo.save_match_result.side_effect = Exception("DB error")
        
        result = result_saver.save(
            tender_id=12351,
            registry_type="44fz",
            matches=[],
            workbook_paths=[],
            processing_time=1.0,
            error_reason=None,
            folder_name="44fz_12351",
        )
        
        # Проверяем, что вернулся None при ошибке
        assert result is None

