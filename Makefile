.PHONY: help build up down restart logs ps db-shell init-db health-check clean

# Цвета для вывода
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Показать справку
	@echo "$(BLUE)Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

build: ## Собрать Docker образы
	@echo "$(BLUE)Сборка Docker образов...$(NC)"
	docker-compose build

up: ## Запустить все сервисы
	@echo "$(BLUE)Запуск сервисов...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Сервисы запущены!$(NC)"
	@echo "$(YELLOW)API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)Docs: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)MinIO Console: http://localhost:9001$(NC)"

down: ## Остановить все сервисы
	@echo "$(BLUE)Остановка сервисов...$(NC)"
	docker-compose down
	@echo "$(GREEN)Сервисы остановлены!$(NC)"

restart: ## Перезапустить все сервисы
	@echo "$(BLUE)Перезапуск сервисов...$(NC)"
	docker-compose restart
	@echo "$(GREEN)Сервисы перезапущены!$(NC)"

logs: ## Показать логи всех сервисов
	docker-compose logs -f

logs-app: ## Показать логи приложения
	docker-compose logs -f app

logs-db: ## Показать логи базы данных
	docker-compose logs -f db

logs-minio: ## Показать логи MinIO
	docker-compose logs -f minio

ps: ## Показать статус сервисов
	docker-compose ps

db-shell: ## Подключиться к PostgreSQL
	@echo "$(BLUE)Подключение к PostgreSQL...$(NC)"
	docker-compose exec db psql -U postgres -d construction_docs

db-backup: ## Создать резервную копию базы данных
	@echo "$(BLUE)Создание резервной копии базы данных...$(NC)"
	docker-compose exec db pg_dump -U postgres construction_docs > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Резервная копия создана!$(NC)"

db-restore: ## Восстановить базу данных из backup.sql
	@echo "$(BLUE)Восстановление базы данных...$(NC)"
	docker-compose exec -T db psql -U postgres construction_docs < backup.sql
	@echo "$(GREEN)База данных восстановлена!$(NC)"

migrate: ## Применить миграции
	@echo "$(BLUE)Применение миграций...$(NC)"
	docker-compose exec app alembic upgrade head

migrate-create: ## Создать новую миграцию (используйте: make migrate-create MSG="description")
	@echo "$(BLUE)Создание миграции: $(MSG)$(NC)"
	docker-compose exec app alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## Откатить последнюю миграцию
	@echo "$(BLUE)Откат миграции...$(NC)"
	docker-compose exec app alembic downgrade -1

migrate-status: ## Показать статус миграций
	docker-compose exec app alembic current

migrate-history: ## Показать историю миграций
	docker-compose exec app alembic history

init-db: ## Инициализировать базу данных тестовыми данными
	@echo "$(BLUE)Инициализация базы данных...$(NC)"
	docker-compose exec app python scripts/init_db.py

health-check: ## Проверить работоспособность сервисов
	@echo "$(BLUE)Проверка работоспособности сервисов...$(NC)"
	docker-compose exec app python scripts/health_check.py

clean: ## Очистить все контейнеры, тома и образы
	@echo "$(RED)Внимание! Это удалит все данные!$(NC)"
	@read -p "Вы уверены? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker system prune -a -f; \
		echo "$(GREEN)Очистка завершена!$(NC)"; \
	else \
		echo "Отмена."; \
	fi

rebuild: ## Пересобрать и перезапустить приложение
	@echo "$(BLUE)Пересборка приложения...$(NC)"
	docker-compose build --no-cache app
	docker-compose up -d app
	@echo "$(GREEN)Приложение пересобрано и перезапущено!$(NC)"

test: ## Запустить тесты (если есть)
	@echo "$(BLUE)Запуск тестов...$(NC)"
	docker-compose exec app pytest -v

install: ## Установить зависимости локально
	@echo "$(BLUE)Установка зависимостей...$(NC)"
	pip install -r requirements.txt

run: ## Запустить приложение локально (без Docker)
	@echo "$(BLUE)Запуск приложения локально...$(NC)"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

setup: build up migrate init-db ## Полная настройка проекта (сборка, запуск, миграции, инициализация)
	@echo "$(GREEN)Проект настроен и готов к работе!$(NC)"
	@echo "$(YELLOW)API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)Docs: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Тестовые пользователи созданы (см. логи init-db)$(NC)"
