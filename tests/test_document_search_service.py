import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from openpyxl import Workbook

from services.document_search_service import DocumentSearchService
from core.exceptions import DocumentSearchError


class FakeDBManager:
    """Простой мок менеджера БД для тестов."""

    def __init__(self, names):
        self._names = names

    def execute_query(self, query, params=None):
        return [{"name": name} for name in self._names]


class DocumentSearchServiceTestCase(unittest.TestCase):
    """Тесты сервиса поиска по документации."""

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.download_dir = Path(self.temp_dir.name) / "downloads"
        self.db_manager = FakeDBManager(["iPhone 14", "Samsung Galaxy"])
        self.service = DocumentSearchService(self.db_manager, self.download_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_sample_workbook(self, text: str) -> Path:
        """Создание временного XLSX файла с указанным текстом."""
        file_path = Path(self.temp_dir.name) / "sample.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet["A1"] = text
        workbook.save(file_path)
        return file_path

    def test_run_document_search_returns_matches(self):
        """Должен находить товары с учетом опечаток."""
        sample_file = self._create_sample_workbook("Ipone 14")
        documents = [{"file_name": "16. Смета Проходная АР.xlsx", "document_links": "http://example.com/doc.xlsx"}]

        with patch.object(DocumentSearchService, "_download_required_documents", return_value=[sample_file]), \
                patch.object(DocumentSearchService, "_prepare_workbook_path", return_value=sample_file):
            result = self.service.run_document_search(documents)

        self.assertIn("file_path", result)
        self.assertTrue(result["matches"])
        product_names = [match["product_name"] for match in result["matches"]]
        self.assertIn("iPhone 14", product_names)

    def test_run_document_search_no_keyword_raises(self):
        """Если нет документа со словом 'смета', выбрасывается исключение."""
        documents = [{"file_name": "Протокол заседания.xlsx", "document_links": "http://example.com/doc.xlsx"}]
        with self.assertRaises(DocumentSearchError):
            self.service.run_document_search(documents)

    def test_run_document_search_accepts_smetnaya(self):
        """Документы со словом 'сметная' также должны находиться."""
        sample_file = self._create_sample_workbook("Ipone 14")
        documents = [{"file_name": "Сметная_документация.part01.rar", "document_links": "http://example.com/doc.part1"}]

        with patch.object(DocumentSearchService, "_download_required_documents", return_value=[sample_file]), \
                patch.object(DocumentSearchService, "_prepare_workbook_path", return_value=sample_file):
            result = self.service.run_document_search(documents)

        self.assertTrue(result["matches"])

    def test_parallel_download_preserves_order(self):
        """Параллельная загрузка должна сохранять исходный порядок частей."""
        docs = [
            {"file_name": f"Сметная_документация.part{str(i).zfill(2)}.rar", "document_links": f"http://example.com/{i}"}
            for i in range(10)
        ]
        service = DocumentSearchService(self.db_manager, self.download_dir)

        def fake_download(doc):
            path = Path(self.temp_dir.name) / doc["file_name"]
            path.touch()
            return path

        with patch.object(DocumentSearchService, "_is_rar_document", return_value=True), \
                patch.object(DocumentSearchService, "_collect_related_archives", return_value=docs), \
                patch.object(DocumentSearchService, "_download_document", side_effect=fake_download):
            result_paths = service._download_required_documents(docs[0], docs)

        self.assertEqual([path.name for path in result_paths], [doc["file_name"] for doc in docs])

    def test_parallel_download_handles_errors(self):
        """При ошибке скачивания должен возникать DocumentSearchError."""
        docs = [
            {"file_name": f"Сметная_документация.part{str(i).zfill(2)}.rar", "document_links": f"http://example.com/{i}"}
            for i in range(3)
        ]
        service = DocumentSearchService(self.db_manager, self.download_dir)

        def fake_download(doc):
            if doc["file_name"].endswith("02.rar"):
                raise ValueError("network error")
            path = Path(self.temp_dir.name) / doc["file_name"]
            path.touch()
            return path

        with patch.object(DocumentSearchService, "_is_rar_document", return_value=True), \
                patch.object(DocumentSearchService, "_collect_related_archives", return_value=docs), \
                patch.object(DocumentSearchService, "_download_document", side_effect=fake_download):
            with self.assertRaises(DocumentSearchError):
                service._download_required_documents(docs[0], docs)

    def test_extract_rar_without_tool(self):
        """Если отсутствует unrar, должен вернуться DocumentSearchError."""
        archive_path = Path(self.temp_dir.name) / "Сметная_документация.part1.rar"
        archive_path.touch()

        with patch.object(DocumentSearchService, "_ensure_unrar_available", side_effect=DocumentSearchError("Нет unrar")):
            with self.assertRaises(DocumentSearchError):
                extract_dir = Path(self.temp_dir.name) / "extract"
                self.service._extract_rar_archive(archive_path, extract_dir)


if __name__ == "__main__":
    unittest.main()

