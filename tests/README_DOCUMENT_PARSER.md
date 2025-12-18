# Тестирование парсера документов

## Описание

Универсальный парсер документов поддерживает следующие форматы:
- **Excel**: .xlsx, .xls
- **Word**: .docx, .doc (старый формат)
- **PDF**: обычные PDF и отсканированные PDF (с OCR)

## Установка зависимостей

### Обязательные библиотеки для всех форматов

```bash
pip install -r requirements.txt
```

### Дополнительно для Word документов (.docx)

```bash
pip install python-docx
```

### Дополнительно для старых Word документов (.doc)

**Вариант 1: Windows COM (требует установленный Microsoft Word)**
```bash
pip install pywin32
```

**Вариант 2: Linux/Mac - antiword (внешний инструмент)**
```bash
# Ubuntu/Debian
sudo apt-get install antiword

# Mac
brew install antiword
```

### Дополнительно для PDF файлов

**Обычные PDF:**
```bash
pip install PyPDF2 pdfplumber
```

**Отсканированные PDF (OCR):**

1. Установите Python библиотеки:
```bash
pip install pytesseract Pillow pdf2image
```

2. Установите Tesseract OCR:

**Windows:**
- Скачайте установщик: https://github.com/UB-Mannheim/tesseract/wiki
- Установите в стандартный путь: `C:\Program Files\Tesseract-OCR\`
- Или укажите путь через переменную окружения: `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

**Linux:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-rus
```

**Mac:**
```bash
brew install tesseract tesseract-lang
```

## Создание тестовых файлов

Перед запуском тестов создайте тестовые файлы:

```bash
python tests/create_test_files.py
```

Это создаст следующие файлы в `tests/test_files/`:
- `test_excel.xlsx` - Excel файл нового формата
- `test_excel.xls` - Excel файл старого формата
- `test_word.docx` - Word документ
- `test_pdf.pdf` - PDF файл с текстом
- `test_pdf_scanned.pdf` - PDF с изображением (для OCR тестирования)

## Запуск тестов

### Все тесты

```bash
python -m pytest tests/test_document_parser.py -v
```

или

```bash
python tests/test_document_parser.py
```

### Отдельные тесты

```bash
# Только Excel
python -m pytest tests/test_document_parser.py::TestDocumentParser::test_parse_excel_xlsx -v

# Только Word
python -m pytest tests/test_document_parser.py::TestDocumentParser::test_parse_word -v

# Только PDF
python -m pytest tests/test_document_parser.py::TestDocumentParser::test_parse_pdf -v

# OCR тест
python -m pytest tests/test_document_parser.py::TestDocumentParser::test_parse_pdf_scanned -v
```

## Использование в коде

### Базовое использование

```python
from pathlib import Path
from services.document_search.document_parser import DocumentParser

# Создаем парсер
parser = DocumentParser()

# Парсим документ
file_path = Path("path/to/document.xlsx")
result = parser.parse_document(file_path)

print(f"Тип документа: {result['type']}")
print(f"Текст: {result['text'][:100]}...")
print(f"Количество ячеек: {len(result['cells'])}")
```

### Определение типа документа

```python
doc_type = parser.detect_document_type(file_path)
print(f"Тип документа: {doc_type}")
```

### Извлечение текста

```python
text = parser.extract_text(file_path)
print(text)
```

### Итерация по ячейкам

```python
for cell in parser.iter_document_cells(file_path):
    print(f"Ячейка {cell['cell_address']}: {cell['text']}")
```

### Принудительное использование OCR для PDF

```python
result = parser.parse_document(pdf_file, force_ocr=True)
```

## Обработка ошибок

Парсер обрабатывает следующие ситуации:

1. **Несуществующий файл** - выбрасывает `DocumentSearchError`
2. **Неподдерживаемый формат** - выбрасывает `DocumentSearchError`
3. **Отсутствующие библиотеки** - логирует предупреждение и выбрасывает `DocumentSearchError` при попытке парсинга
4. **Поврежденный файл** - логирует ошибку и возвращает результат с полем `error`

Пример обработки ошибок:

```python
from core.exceptions import DocumentSearchError

try:
    result = parser.parse_document(file_path)
    if 'error' in result:
        print(f"Ошибка: {result['error']}")
    else:
        print("Успешно обработан!")
except DocumentSearchError as e:
    print(f"Ошибка документа: {e}")
except Exception as e:
    print(f"Неожиданная ошибка: {e}")
```

## Проверка доступности библиотек

### Проверка Word

```python
from services.document_search.word_processor import WordProcessor

processor = WordProcessor()
# Проверяем в логах, какие библиотеки доступны
```

### Проверка PDF и OCR

```python
from services.document_search.pdf_processor import PDFProcessor

processor = PDFProcessor()
# Проверяем в логах, доступен ли OCR
```

## Устранение проблем

### Word документы не парсятся

1. Проверьте, установлен ли `python-docx`:
   ```bash
   pip list | grep python-docx
   ```

2. Для .doc файлов проверьте:
   - Windows: установлен ли Microsoft Word и `pywin32`
   - Linux: установлен ли `antiword`

### PDF не парсится

1. Проверьте установленные библиотеки:
   ```bash
   pip list | grep -E "PyPDF2|pdfplumber"
   ```

2. Если PDF отсканированный, проверьте Tesseract:
   ```bash
   tesseract --version
   ```

### OCR не работает

1. **Windows**: Проверьте путь к Tesseract в логах
   - Установите Tesseract из официального источника
   - Парсер автоматически найдет его в стандартных путях
   - Или укажите путь через переменную окружения `TESSERACT_CMD`

2. **Linux/Mac**: Установите Tesseract и языковые пакеты:
   ```bash
   sudo apt-get install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng
   ```

3. Проверьте установку Python библиотек:
   ```bash
   pip list | grep -E "pytesseract|Pillow|pdf2image"
   ```

## Логирование

Все действия парсера логируются через `loguru`. Для просмотра логов:

```python
from loguru import logger

# Логи будут выводиться в консоль и файл (если настроено)
```

Уровни логирования:
- `INFO` - успешные операции
- `WARNING` - недоступные библиотеки, но парсинг возможен
- `ERROR` - ошибки при парсинге
- `DEBUG` - детальная информация для отладки

## Производительность

- **Excel**: быстрый парсинг (обычно < 1 секунды для файлов до 1000 строк)
- **Word**: средняя скорость (1-5 секунд для документов до 50 страниц)
- **PDF текст**: быстрый (обычно < 2 секунды)
- **PDF OCR**: медленный (10-60 секунд на страницу, в зависимости от размера и качества)

## Дальнейшее развитие

- [ ] Поддержка .rtf файлов
- [ ] Поддержка .odt файлов (OpenDocument)
- [ ] Кэширование результатов парсинга
- [ ] Параллельная обработка нескольких документов
- [ ] Улучшение качества OCR через настройки Tesseract

