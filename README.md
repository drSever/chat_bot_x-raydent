# X‑RayDent Support Bot MVP

Локальный русскоязычный чат-бот поддержки со 119 FAQ, семантическим поиском, safety-router, Qwen3‑0.6B и отдельным PEFT/LoRA-адаптером. В проект входят FastAPI backend, встраиваемый Shadow DOM-виджет, тестовая страница, CPU-тренировка и Google Colab notebook.

## Что умеет MVP

- отвечает по базе X‑RayDent и показывает использованные FAQ;
- ищет похожие формулировки через multilingual MiniLM;
- формулирует короткий ответ локальной Qwen3‑0.6B;
- не ставит диагноз и не назначает лечение;
- отдельно обрабатывает острые симптомы, prompt injection и чувствительные данные;
- не записывает сообщения и обращения на диск;
- работает без моделей в режиме точных FAQ-ответов.

Неподтверждённые общие знания отключены по умолчанию: контрольная проверка показала, что компактная Qwen3‑0.6B может уверенно ошибаться вне предметной области. Для экспериментов режим можно включить через `XRAYDENT_ALLOW_GENERAL_KNOWLEDGE=true`, но для клиентского использования это не рекомендуется.

## Быстрый запуск на Windows

Требуется 64-битный Python 3.11 или 3.12 и около 8 ГБ свободного места. На первом запуске нужен интернет. На компьютере без NVIDIA генерация и особенно обучение будут медленными.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
.\.venv\Scripts\python.exe scripts\download_models.py
.\scripts\start.ps1
```

Откройте `http://127.0.0.1:8000`. API-документация доступна на `http://127.0.0.1:8000/docs`.

Сервер по умолчанию работает с `XRAYDENT_OFFLINE=true`: он использует локальный кэш и не начинает скрытое скачивание при старте. Если весов нет, `/api/health` покажет fallback, а готовые FAQ продолжат работать.

Чтобы сначала проверить интерфейс без загрузки весов:

```powershell
$env:XRAYDENT_ENABLE_SEMANTIC='false'
$env:XRAYDENT_ENABLE_LLM='false'
.\scripts\start.ps1
```

## Обучение LoRA

Сначала формируется SFT-датасет из FAQ и safety-сценариев:

```powershell
.\.venv\Scripts\python.exe training\build_dataset.py
.\.venv\Scripts\python.exe training\train_lora.py --profile cpu-mvp
```

CPU-профиль намеренно использует 32 примера, один epoch и LoRA rank 8: это проверяемый тренировочный MVP, а не финальная продуктовая модель.

[Открыть обучение в Google Colab](https://colab.research.google.com/github/drSever/chat_bot_x-raydent/blob/main/training/colab_qwen3_lora.ipynb)

В Colab выберите T4 GPU и выполните все ячейки сверху вниз. Ноутбук проверит GPU, соберёт полный датасет, обучит адаптер, проверит веса и скачает `xraydent-qwen3-lora.zip`. Полученный архив распакуйте в `artifacts/adapter`.

В поставку включён фактически обученный быстрый адаптер: 8 примеров, 1 epoch, 2 optimizer steps, 1 146 880 обучаемых параметров. Он предназначен для end-to-end проверки; перед production используйте полный датасет и GPU-профиль.

При наличии `artifacts/adapter/adapter_config.json` backend автоматически загружает адаптер. `/api/health` показывает режим `qwen3+lora`, `qwen3-base` или `faq-direct`.

## Встраивание на лендинг

```html
<script
  src="http://127.0.0.1:8000/static/widget.js"
  data-api-url="http://127.0.0.1:8000"
  data-position="right"
  data-theme="light">
</script>
```

Виджет изолирует стили через Shadow DOM. Для production нужно заменить адрес, ограничить CORS разрешённым доменом и поставить backend за HTTPS.

## API

- `POST /api/chat` — сообщение, идентификатор сессии и до шести элементов истории;
- `POST /api/feedback` — оценка `up`/`down`, только счётчики в памяти;
- `POST /api/support/demo` — проверка демо-обращения без отправки и хранения;
- `GET /api/health` — состояние FAQ, retrieval, LLM и адаптера.

## Тесты

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Тесты не скачивают модели: они проверяют все 119 FAQ, оригинальные вопросы, контрольные перефразировки, медицинскую эскалацию, prompt injection, API и запрет чувствительных данных.

## Ограничения MVP

Это информационный помощник, а не медицинское изделие или замена врачу. Демо-форма не связана с CRM/email. Авторизация, production-хранилище, аналитика, обработка снимков и облачное развёртывание не входят в этот прототип.
