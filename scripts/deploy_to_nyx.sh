#!/bin/bash
# Скрипт для копирования модуля обработки документов на сервер nyx

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Параметры
REMOTE_USER="wanga"
REMOTE_HOST="nyx"
REMOTE_PATH="/home/wanga/tender_document_processor"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${GREEN}🚀 Начало развертывания модуля обработки документов на сервер nyx${NC}"
echo ""

# Проверка SSH подключения
echo -e "${YELLOW}Проверка SSH подключения...${NC}"
if ! ssh -o ConnectTimeout=5 "$REMOTE_USER@$REMOTE_HOST" "echo 'SSH connection OK'" > /dev/null 2>&1; then
    echo -e "${RED}❌ Не удалось подключиться к серверу $REMOTE_HOST${NC}"
    exit 1
fi
echo -e "${GREEN}✅ SSH подключение установлено${NC}"

# Создание структуры директорий на сервере
echo -e "${YELLOW}Создание структуры директорий на сервере...${NC}"
ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_PATH/{config,core,services/{archive_runner,document_search,helpers,storage},scripts,logs}"

# Копирование файлов конфигурации
echo -e "${YELLOW}Копирование файлов конфигурации...${NC}"
scp -r "$PROJECT_ROOT/config/"*.py "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/config/" 2>/dev/null || true
scp "$PROJECT_ROOT/config/__init__.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/config/" 2>/dev/null || true

# Копирование core модулей
echo -e "${YELLOW}Копирование core модулей...${NC}"
scp -r "$PROJECT_ROOT/core/"*.py "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/core/" 2>/dev/null || true
scp "$PROJECT_ROOT/core/__init__.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/core/" 2>/dev/null || true

# Копирование services/archive_runner
echo -e "${YELLOW}Копирование services/archive_runner...${NC}"
scp -r "$PROJECT_ROOT/services/archive_runner/"*.py "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/archive_runner/" 2>/dev/null || true
scp "$PROJECT_ROOT/services/archive_runner/__init__.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/archive_runner/" 2>/dev/null || true

# Копирование services/document_search
echo -e "${YELLOW}Копирование services/document_search...${NC}"
scp -r "$PROJECT_ROOT/services/document_search/"*.py "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/document_search/" 2>/dev/null || true
scp "$PROJECT_ROOT/services/document_search/__init__.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/document_search/" 2>/dev/null || true

# Копирование других services файлов
echo -e "${YELLOW}Копирование других services модулей...${NC}"
scp "$PROJECT_ROOT/services/archive_background_runner.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/" 2>/dev/null || true
scp "$PROJECT_ROOT/services/tender_repository.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/" 2>/dev/null || true
scp "$PROJECT_ROOT/services/tender_match_repository.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/" 2>/dev/null || true
scp "$PROJECT_ROOT/services/document_search_service.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/" 2>/dev/null || true
scp "$PROJECT_ROOT/services/product_repository.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/" 2>/dev/null || true
scp "$PROJECT_ROOT/services/error_logger.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/" 2>/dev/null || true
scp "$PROJECT_ROOT/services/fuzzy_search.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/" 2>/dev/null || true
scp "$PROJECT_ROOT/services/__init__.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/" 2>/dev/null || true

# Копирование services/helpers
echo -e "${YELLOW}Копирование services/helpers...${NC}"
scp -r "$PROJECT_ROOT/services/helpers/"*.py "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/helpers/" 2>/dev/null || true

# Копирование services/storage (Яндекс Диск)
echo -e "${YELLOW}Копирование services/storage...${NC}"
scp -r "$PROJECT_ROOT/services/storage/"*.py "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/storage/" 2>/dev/null || true
scp "$PROJECT_ROOT/services/storage/__init__.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/services/storage/" 2>/dev/null || true

# Копирование scripts
echo -e "${YELLOW}Копирование scripts...${NC}"
scp "$PROJECT_ROOT/scripts/run_document_processing_daemon.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/scripts/" 2>/dev/null || true

# Копирование requirements.txt
echo -e "${YELLOW}Копирование requirements.txt...${NC}"
scp "$PROJECT_ROOT/requirements.txt" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/" 2>/dev/null || true

# Создание __init__.py файлов если их нет
echo -e "${YELLOW}Создание __init__.py файлов...${NC}"
ssh "$REMOTE_USER@$REMOTE_HOST" "touch $REMOTE_PATH/__init__.py $REMOTE_PATH/services/__init__.py $REMOTE_PATH/config/__init__.py $REMOTE_PATH/core/__init__.py"

echo ""
echo -e "${GREEN}✅ Файлы скопированы на сервер${NC}"
echo ""
echo -e "${YELLOW}Следующие шаги:${NC}"
echo "1. Подключитесь к серверу: ssh $REMOTE_USER@$REMOTE_HOST"
echo "2. Перейдите в директорию: cd $REMOTE_PATH"
echo "3. Создайте .env файл с настройками БД"
echo "4. Установите зависимости: pip3 install -r requirements.txt"
echo "5. Установите системные пакеты: sudo apt install -y tesseract-ocr poppler-utils unrar"
echo "6. Настройте systemd service (см. scripts/tender-processor.service)"
echo "7. Запустите сервис: sudo systemctl start tender-processor"
