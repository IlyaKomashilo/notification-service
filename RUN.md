# Как это всё запустить

Памятка, чтобы каждый раз не вспоминать команды.
Терминалы открываем в папке проекта.

## Сначала окружение

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

В новом терминале снова активируем .venv. Ставить зависимости каждый раз не надо,
только если поменялся requirements.txt.

PostgreSQL у меня локальный, docker его не запускает. Адрес и пароль лежат в .env,
пример настроек есть в .env.example. Нужны две базы: notifications для приложения
и notifications_test для тестов. Не путать их

## Поднимаем рэббит

```bash
colima start
docker volume create notifications-rabbitmq-data
docker compose up -d
docker compose ps
```

Volume создаём один раз. Если он уже есть, ничего не сотрётся.
Кролику в панель: http://127.0.0.1:15672. Логин и пароль: guest / guest


## API

```bash
python -m src.db.check_connection
alembic upgrade head
uvicorn src.main:app --reload --port 9000
```

Сваггер тут: http://127.0.0.1:9000/docs.
Первые две команды проверяют БД и применяют миграции. Последняя запускает API.
Для примера из scripts/send_event.py нужен шаблон. Создаём через POST /templates:

```json
{
  "code": "welcome_message",
  "subject": "Привет, {{ username }}!",
  "body": "Рады тебя видеть, {{ username }}!"
}
```

## Слушать очередь

В отдельном терминале с активной .venv:

```bash
python -m src.consumers.notification_events
```

Если пишет, что подключился, и дальше молчит, всё нормально. Он ждёт сообщения.
Сохраняет уведомления в БД, но письма сам пока не отправляет. API ему не нужен.

## Кинуть событие для проверки

```bash
python -m scripts.send_event
```

Запускаем в другом терминале. Данные меняем в scripts/send_event.py.
Новое событие = новый event_id

В панели кролика смотрим notification_events. Отклонённые сообщения лежат
в notification_events.failed

## Посмотреть письма

У меня Mailpit лежит в ~/mailpit. Запускаю отдельно:

```bash
~/mailpit/mailpit --listen 127.0.0.1:8025 --smtp 127.0.0.1:1025
```

Открываем http://127.0.0.1:8025.
Для отправки писем нужен ещё один терминал с воркером:

```bash
celery -A src.core.celery_app:app worker --loglevel=INFO --pool=solo
```

POST /notifications/{id}/send в сваггере кладёт задачу в рэббит.
Ответ 202 значит, что задачу приняли. Письмо появится после работы воркера.
Итоговый статус смотрим через GET /notifications/{id}.

## Перед коммитом

```bash
ruff check . --fix
ruff format .
TEST_RABBITMQ_URL=amqp://guest:guest@localhost/ pytest -q
```

Перед тестами проверь, что БД и рэббит запущены. Миграции тесты накатят сами.
Можно просто pytest -q, но тогда два теста с кроликом пропустятся.

## Что пока не закрыто

- Сообщение в notification_events создаёт запись. Чтобы ушло письмо, отдельно вызываем POST /notifications/{id}/send.
- Если SMTP упал, запись станет failed. Автоматического повтора пока нет.
- Если воркер упал в середине отправки, запись может остаться в processing. Письмо могло уже уйти, поэтому вслепую отправлять ещё раз нельзя.
- Рэббит с guest/guest и Mailpit настроены для локального запуска. Выставлять их наружу нельзя.

## Если что-то не работает

Если рэббит чудит, сначала смотрим логи:

```bash
docker compose logs --tail 50 rabbitmq
```
