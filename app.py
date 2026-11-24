# -*- coding: utf-8 -*-
# ↑ Указываем кодировку UTF-8 — чтобы кириллица и эмодзи в строках не ломались.

"""
Кейс 9. Регион 2 — прототип ИИ-помощника по генерации рекламных текстов.
Модули: ввод данных → генерация → адаптация под ЦА → проверка → UI → документация.
Запуск: python keys_9_ai.py   (ключ API — в файле config.py рядом с программой)
"""

import random                                              # Импорт модуля random — нужен для случайного выбора фраз.
import tkinter as tk                                       # Импорт tkinter — базовый GUI-движок (основной модуль).
from tkinter import ttk, messagebox                        # ttk — «современные» виджеты; messagebox — всплывающие окна.
import json                                                # Разбор JSON-ответа модели.
import os                                                  # Пути к файлам (ищем config.py рядом).
import sys                                                 # Управление путями импорта.
import requests                                            # HTTP-запросы к API (пакет уже установлен).

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Чтобы config.py нашёлся при любом способе запуска.
try:                                                       # Ключи API держим в отдельном файле config.py…
    from config import AI_API_KEY, AI_BASE_URL, AI_MODEL   # …он лежит рядом с этим файлом.
except ImportError:                                        # Если файла нет…
    AI_API_KEY = ""                                        # …ключа нет, работаем на шаблонах.
    AI_BASE_URL = "https://api.deepseek.com/v1"            # Адрес API по умолчанию.
    AI_MODEL = "deepseek-chat"                             # Модель по умолчанию.

from regeneration import regenerate_with_validation       # Умная перегенерация с повторной проверкой.


# ============================ СПРАВОЧНИКИ ============================

AUDIENCE_STYLES = {                                        # Словарь стилей под каждую целевую аудиторию.
    "Молодёжь (16–25)": {                                  # Ключ — название сегмента.
        "hooks": [                                         # Список «хуков» — цепляющих первых фраз.
            "Стоп-скролл! Это реально про тебя.",          # Хук №1.
            "Есть тема, которая зайдёт.",                  # Хук №2.
            "Не листай дальше — тут по делу.",             # Хук №3.
        ],                                                 # Конец списка хуков.
        "args": [                                          # Список аргументов-выгод под сегмент.
            "Экономит время, пока ты занимаешься тем, что важно.",  # Аргумент №1.
            "Без сложных условий — разберёшься за минуту.",         # Аргумент №2.
            "Современно, удобно и без лишней воды.",                # Аргумент №3.
        ],                                                 # Конец списка аргументов.
    },                                                     # Конец блока «Молодёжь».
    "Семьи с детьми": {                                    # Аудитория «Семьи с детьми».
        "hooks": [                                         # Хуки под семьи.
            "Мамы и папы, это для вас.",                   # Хук №1.
            "Забота о семье начинается с простых решений.",# Хук №2.
            "Больше времени на близких — меньше на быт.",  # Хук №3.
        ],                                                 # Конец хуков.
        "args": [                                          # Аргументы под семьи.
            "Помогает освободить время для семьи.",        # Аргумент №1.
            "Продумано до мелочей и безопасно.",           # Аргумент №2.
            "Выгодно для семейного бюджета.",              # Аргумент №3.
        ],                                                 # Конец аргументов.
    },                                                     # Конец блока «Семьи с детьми».
    "B2B-клиенты": {                                       # Аудитория «B2B-клиенты».
        "hooks": [                                         # Хуки под B2B.
            "Уважаемые коллеги, предлагаем решение для вашего бизнеса.",  # Хук №1.
            "Коротко о том, что снизит ваши издержки.",    # Хук №2.
            "Решение, которое окупается.",                 # Хук №3.
        ],                                                 # Конец хуков.
        "args": [                                          # Аргументы под B2B.
            "Прозрачные условия и понятная экономика внедрения.",      # Аргумент №1.
            "Подходит для команд любого размера.",         # Аргумент №2.
            "Снижает трудозатраты и ускоряет процессы.",   # Аргумент №3.
        ],                                                 # Конец аргументов.
    },                                                     # Конец блока «B2B».
    "Пенсионеры (55+)": {                                  # Аудитория «Пенсионеры».
        "hooks": [                                         # Хуки под пенсионеров.
            "Уважаемые друзья, это предложение для вас.",  # Хук №1.
            "Просто, понятно и с заботой о вас.",          # Хук №2.
            "Внимание к деталям — в каждом решении.",      # Хук №3.
        ],                                                 # Конец хуков.
        "args": [                                          # Аргументы под пенсионеров.
            "Ничего сложного — всё понятно и доступно.",   # Аргумент №1.
            "Поддержка на каждом шаге.",                   # Аргумент №2.
            "Честные условия без мелкого шрифта.",         # Аргумент №3.
        ],                                                 # Конец аргументов.
    },                                                     # Конец блока «Пенсионеры».
}                                                          # Конец словаря AUDIENCE_STYLES.

TONES = {                                                  # Словарь тональностей.
    "Формальный": {                                        # Формальный тон.
        "intro": "Добрый день!",                           # Приветствие.
        "style": [                                         # Стилевые фразы.
            "Предложение действительно для новых клиентов.",   # Фраза №1.
            "Условия прозрачны и зафиксированы в договоре.",    # Фраза №2.
        ],                                                 # Конец стилевых фраз.
        "closing": "С уважением, команда «{product}».",    # Подпись с подстановкой названия.
    },                                                     # Конец формального.
    "Дружелюбный": {                                       # Дружелюбный тон.
        "intro": "Привет! 👋",                             # Приветствие с эмодзи.
        "style": [                                         # Стилевые фразы.
            "Мы всегда рядом и готовы помочь.",            # Фраза №1.
            "Просто, по-человечески и без сложностей.",    # Фраза №2.
        ],                                                 # Конец фраз.
        "closing": "Будем рады помочь — команда «{product}».",  # Подпись.
    },                                                     # Конец дружелюбного.
    "Молодёжный": {                                        # Молодёжный тон.
        "intro": "Йоу! 🔥",                                # Приветствие.
        "style": [                                         # Стилевые фразы.
            "Это по-настоящему удобно.",                   # Фраза №1.
            "Без душноты — только по делу.",               # Фраза №2.
        ],                                                 # Конец фраз.
        "closing": "Погнали — «{product}».",               # Подпись.
    },                                                     # Конец молодёжного.
    "Экспертный": {                                        # Экспертный тон.
        "intro": "Здравствуйте!",                          # Приветствие.
        "style": [                                         # Стилевые фразы.
            "Подход опирается на проверенную методику.",   # Фраза №1.
            "Решение протестировано на реальных задачах.", # Фраза №2.
        ],                                                 # Конец фраз.
        "closing": "Команда «{product}».",                 # Подпись.
    },                                                     # Конец экспертного.
}                                                          # Конец словаря TONES.

CTA_BY_PLATFORM = {                                        # Словарь призывов к действию по площадкам.
    "Соцсети (пост)": [                                    # CTA для соцсетей.
        "👉 Переходи по ссылке и выбирай!",                # CTA №1.
        "Жми «Подробнее» и забирай своё!",                 # CTA №2.
        "Напиши «+» в комментариях — расскажем подробнее!",# CTA №3.
    ],                                                     # Конец CTA соцсетей.
    "Email": [                                             # CTA для email.
        "Перейдите по ссылке, чтобы оформить заказ.",      # CTA №1.
        "Ответьте на письмо — подберём решение под вас.",  # CTA №2.
    ],                                                     # Конец CTA email.
    "Баннер": ["Узнать больше", "Заказать", "Перейти"],    # CTA для баннера (короткие).
    "Карточка товара": [                                   # CTA для карточки товара.
        "Добавьте в корзину.",                             # CTA №1.
        "Оформите заказ сейчас.",                          # CTA №2.
        "Нажмите «Купить».",                               # CTA №3.
    ],                                                     # Конец CTA карточки.
}                                                          # Конец CTA_BY_PLATFORM.

PLATFORMS = list(CTA_BY_PLATFORM.keys())                   # Список площадок для Combobox.
TONES_LIST = list(TONES.keys())                            # Список тонов для Combobox.
AUDIENCES = list(AUDIENCE_STYLES.keys()) + ["Своя аудитория"]  # Список ЦА + вариант «своя».

PLATFORM_LIMITS = {                                        # (мин, макс) символов под каждую площадку.
    "Соцсети (пост)": (80, 1000),                          # Пост — 80–1000.
    "Email": (120, 1500),                                  # Email — 120–1500.
    "Баннер": (5, 90),                                     # Баннер — 5–90.
    "Карточка товара": (60, 500),                          # Карточка — 60–500.
}                                                          # Конец словаря лимитов.

CTA_WORDS = [                                              # Список слов-маркеров призыва к действию.
    "закажи", "закажите", "заказать", "перейди", "перейдите", "перейти",  # Глаголы в разных формах.
    "переходи", "оставь", "оставьте", "купи", "купите", "узнай", "узнайте",  # Часть 2.
    "узнать", "подпишись", "подпишитесь", "жми", "нажмите", "попробуй",  # Часть 3.
    "попробуйте", "звони", "звоните", "оформи", "оформите", "получи",   # Часть 4.
    "получите", "добавьте", "выбирай", "забирай", "напиши", "ответьте", # Часть 5.
]                                                          # Конец списка CTA-слов.

FORBIDDEN = [                                              # Список запрещённых формулировок (по ТЗ).
    "самый лучший", "лучший в мире", "лучший на рынке",    # Превосходные степени.
    "гарантированный результат", "гарантируем", "100%",    # Обещания результата.
    "абсолютно безопасно", "абсолютно",                    # Абсолютные утверждения.
]                                                          # Конец списка.


# ============================ ИИ (API) ============================

AI_SYSTEM_PROMPT = (                                       # Системная инструкция для модели.
    "Ты — профессиональный копирайтер банка «Центр-инвест». Пишешь рекламные тексты "
    "по ФЗ «О рекламе» РФ: без запрещённых формулировок, обмана и навязчивого капса. "
    "Отвечай ТОЛЬКО валидным JSON без markdown-обёртки."
)


def ai_is_enabled():                                       # Включён ли ИИ (задан ли ключ).
    return bool(str(AI_API_KEY).strip())                   # Пустой ключ = режим шаблонов.


def ai_request(messages, temperature=0.9, max_tokens=3000, json_mode=True):  # Один запрос к API.
    payload = {                                            # Тело запроса (формат OpenAI-совместимых API).
        "model": AI_MODEL,                                 # Модель.
        "messages": messages,                              # Сообщения (system + user).
        "temperature": temperature,                        # «Творческость».
        "max_tokens": max_tokens,                          # Ограничение длины ответа.
    }
    if json_mode:                                          # Если нужен именно JSON…
        payload["response_format"] = {"type": "json_object"}  # …просим чистый JSON.
    headers = {"Authorization": f"Bearer {AI_API_KEY}",    # Ключ в заголовке.
               "Content-Type": "application/json"}         # Тип данных.
    url = AI_BASE_URL.rstrip("/") + "/chat/completions"    # Полный адрес метода.
    r = requests.post(url, headers=headers, json=payload, timeout=60)  # Отправляем запрос.
    if r.status_code == 400 and "response_format" in payload:  # Провайдер не умеет JSON-режим…
        payload.pop("response_format")                     # …убираем его…
        r = requests.post(url, headers=headers, json=payload, timeout=60)  # …и повторяем запрос.
    if r.status_code != 200:                               # Если ошибка…
        raise RuntimeError(f"API вернул {r.status_code}: {r.text[:300]}")  # …пробрасываем наверх.
    # Некоторые провайдеры возвращают content=None, если модели не хватило max_tokens
    # на рассуждение. Берём только завершённые ответы с непустым content.
    message = r.json().get("choices", [{}])[0].get("message", {})
    content = message.get("content")
    if content is None or not str(content).strip():
        reason = message.get("reasoning_content") or "модель не вернула content"
        raise RuntimeError(f"Пустой ответ модели (увеличьте max_tokens или смените модель): {str(reason)[:180]}")
    return str(content)                                      # Достаём текст ответа.


def ai_ping():                                             # Короткий запрос для проверки ключа.
    reply = ai_request(                                    # Без JSON-режима — просто «жив ли ИИ».
        [{"role": "user", "content": "Ответь одним словом: работает"}],
        temperature=0, max_tokens=300, json_mode=False)
    return str(reply).strip()[:60] or "ok"                 # Возвращаем короткий ответ модели.


def ai_parse_json(raw):                                    # Достаём JSON из ответа модели.
    raw = (raw or "").strip()                              # Убираем пробелы по краям.
    start, end = raw.find("{"), raw.rfind("}")             # Ищем границы объекта.
    if start == -1 or end == -1:                           # Если объекта нет…
        raise ValueError("в ответе модели нет JSON")       # …ошибка (сработает фолбэк на шаблоны).
    return json.loads(raw[start:end + 1])                  # Разбираем JSON.


def ai_prompt_for_variants(data, n):                       # Промпт с параметрами продукта.
    lo, hi = PLATFORM_LIMITS.get(data["platform"], (0, 5000))  # Лимиты символов под площадку.
    audience = (data.get("audience_custom") or "").strip()  # Своя ЦА…
    if data["audience"] != "Своя аудитория":               # …или выбранный сегмент.
        audience = data["audience"]                        # Берём сегмент из списка.
    return (                                               # Собираем текст промпта.
        f"Сгенерируй {n} разных рекламных текста.\n"
        f"Продукт: {data['product']}\n"
        f"Описание: {data['description'] or '—'}\n"
        f"Преимущества: {'; '.join(data['benefits']) or '—'}\n"
        f"Цена: {data['price'] or '—'}\n"
        f"Целевая аудитория: {audience}\n"
        f"Тон: {data['tone']}\n"
        f"Площадка: {data['platform']} — от {lo} до {hi} символов на текст\n"
        f"Обязательно: в каждом тексте есть призыв к действию.\n"
        f"Запрещено использовать: {', '.join(FORBIDDEN)}.\n"
        f"Тексты должны заметно отличаться друг от друга.\n"
        'Верни строго JSON: {"variants": ["текст 1", "текст 2", "текст 3"]}'
    )


def ai_generate_variants(data, n=3):                       # n текстов одним запросом.
    raw = ai_request([                                     # Запрос к модели.
        {"role": "system", "content": AI_SYSTEM_PROMPT},   # Роль и правила.
        {"role": "user", "content": ai_prompt_for_variants(data, n)},  # Параметры продукта.
    ])
    found = ai_parse_json(raw).get("variants") or []       # Достаём список текстов.
    texts = [str(t).strip() for t in found if str(t).strip()]  # Чистим пустые строки.
    if not texts:                                          # Если модель вернула пусто…
        raise ValueError("модель не вернула тексты")       # …ошибка (сработает фолбэк).
    return texts                                           # Возвращаем тексты.


# ============================ ГЕНЕРАЦИЯ ============================

def get_audience_style(data):                              # Возвращает стиль под выбранную ЦА.
    key = data["audience"]                                 # Достаём ключ аудитории из словаря data.
    if key in AUDIENCE_STYLES:                             # Если аудитория из готовых шаблонов…
        return AUDIENCE_STYLES[key]                        # …возвращаем её стиль.
                                                           # Иначе (своя аудитория):
    custom = data.get("audience_custom", "").strip()       # Берём пользовательский ввод, чистим пробелы.
    arg = (f"Подойдёт тем, для кого важно: {custom}."      # Формируем аргумент с подстановкой.
           if custom else "Подойдёт широкой аудитории.")   # Или дефолтный аргумент.
    return {                                               # Возвращаем синтетический стиль.
        "hooks": [                                         # Пул хуков.
            "Есть предложение, которое может вас заинтересовать.",  # Хук №1.
            "Коротко о том, что может быть полезно именно вам.",     # Хук №2.
        ],                                                 # Конец хуков.
        "args": [arg],                                     # Пул аргументов — один.
    }                                                      # Конец возвращаемого словаря.


def build_long_text(data):                                 # Собирает длинный рекламный текст.
    """Полный рекламный текст под соцсети / email / карточку товара."""
    aud = get_audience_style(data)                         # Получаем стиль ЦА.
    tone = TONES[data["tone"]]                             # Получаем блок тональности.
    parts = []                                             # Список строк будущего текста.

    parts.append(f"{tone['intro']} {random.choice(aud['hooks'])}")  # 1) Приветствие + случайный хук.

    if data["description"]:                                # Если есть описание…
        parts.append(f"{data['product']} — {data['description']}")  # …добавляем «Название — описание».
    else:                                                  # Иначе…
        parts.append(data["product"])                      # …только название.

    if data["benefits"]:                                   # Если есть преимущества…
        parts.append("Что вы получаете:")                  # …заголовок списка.
        parts.extend(f"• {b}" for b in data["benefits"])   # …и сами пункты с маркерами.

    parts.append(random.choice(aud["args"]))               # Случайный аргумент под ЦА.
    parts.append(random.choice(tone["style"]))             # Случайная стилевая фраза тона.

    if data["price"]:                                      # Если указана цена…
        parts.append(f"Цена: {data['price']}.")            # …добавляем строку с ценой.

    parts.append(random.choice(CTA_BY_PLATFORM[data["platform"]]))  # Случайный CTA под площадку.
    parts.append(tone["closing"].format(product=data["product"]))   # Подпись с подстановкой названия.

    return "\n".join(parts)                                # Склеиваем строки через \n.


def build_short_text(data):                                # Собирает короткий текст под баннер.
    """Короткий текст под баннер (до ~90 символов)."""
    benefit = data["benefits"][0] if data["benefits"] else data["description"]  # Берём 1-ю выгоду или описание.
    if benefit and len(benefit) > 45:                      # Если выгода слишком длинная…
        benefit = benefit[:45].rstrip() + "…"              # …обрезаем до 45 симв. и добавляем многоточие.
    cta = random.choice(CTA_BY_PLATFORM["Баннер"])         # Случайный короткий CTA.
    if benefit:                                            # Если выгода есть…
        return f"{data['product']}: {benefit}. {cta}!"     # …формат «Продукт: выгода. CTA!».
    return f"{data['product']}. {cta}!"                    # Иначе — только продукт и CTA.


def generate_text_with_source(data):                       # Текст + источник: «ИИ» или «шаблон».
    if ai_is_enabled():                                    # Если ключ задан…
        try:                                               # …пробуем ИИ.
            return ai_generate_variants(data, 1)[0], "ИИ"  # Один текст от модели.
        except Exception as e:                             # Любая ошибка: сеть, ключ, формат ответа…
            print("ИИ недоступен, использованы шаблоны:", e)  # …сообщаем в консоль и идём дальше.
    if data["platform"] == "Баннер":                       # Если площадка — баннер…
        return build_short_text(data), "шаблон"            # …генерируем короткий текст.
    return build_long_text(data), "шаблон"                 # Иначе — длинный.


def generate_text(data):                                   # Совместимость: возвращает только текст.
    return generate_text_with_source(data)[0]


def rewrite_text_for_regeneration(prompt, data):           # Переделка текста при нажатии «↻».
    """Сначала пробуем ИИ, если ключа нет — возвращаемся к шаблону."""
    if ai_is_enabled():
        try:
            raw = ai_request(
                [
                    {
                        "role": "system",
                        "content": "Ты копирайтер. Верни только готовый рекламный текст без пояснений и без JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=1500,
                json_mode=False,
            )
            text = str(raw).strip()
            if text:
                return text, "ИИ"
        except Exception as e:                              # Сеть, ключ, формат ответа…
            print("ИИ недоступен при перегенерации, использован шаблон:", e)
    if data["platform"] == "Баннер":                        # Короткий формат…
        return build_short_text(data), "шаблон"
    return build_long_text(data), "шаблон"                   # Остальные площадки.


# ============================ ВАЛИДАЦИЯ ============================

def validate_text(text, platform):                         # Проверяет текст, возвращает список замечаний.
    """Модуль проверки: длина, призыв к действию, запрещённые формулировки."""
    issues = []                                            # Список замечаний (изначально пуст).
    low = text.lower()                                     # Приводим текст к нижнему регистру для поиска.
    n = len(text)                                          # Длина текста в символах.

    lo, hi = PLATFORM_LIMITS.get(platform, (0, 5000))      # Достаём лимиты под площадку (или дефолт).
    if n > hi:                                             # Если текст длиннее макс…
        issues.append(f"Текст длиннее лимита для «{platform}»: {n} симв. (макс. {hi}).")  # …замечание.
    if n < lo:                                             # Если текст короче мин…
        issues.append(f"Текст короче рекомендуемого: {n} симв. (мин. {lo}).")  # …замечание.

    if not any(w in low for w in CTA_WORDS):               # Если ни одного CTA-слова не найдено…
        issues.append("Не найден призыв к действию "       # …замечание про CTA.
                      "(например: «Закажите», «Перейдите», «Попробуйте»).")

    for bad in FORBIDDEN:                                  # Проходим по запрещённым фразам.
        if bad in low:                                     # Если фраза найдена…
            issues.append(f"Нежелательная формулировка: «{bad}».")  # …добавляем замечание.

    return issues                                          # Возвращаем список замечаний.


def validate_input(data):                                  # Только одна проверка: имя продукта.
    """Пустое имя или одни пробелы — ошибка. Больше ничего не блокируем."""
    product = str(data.get("product") or "").strip()       # Убираем пробелы по краям.
    if not product:                                        # Пусто = одни пробелы тоже.
        return ["Введите верное название продукта или услуги."], []
    return [], []                                          # Всё остальное пропускаем.

# ============================ ИНТЕРФЕЙС ============================

class AdAssistantApp:                                      # Класс приложения (весь UI).
    def __init__(self, root):                              # Конструктор — вызывается при запуске.
        self.root = root                                   # Сохраняем ссылку на главное окно.
        self.root.title("ИИ-помощник по рекламным текстам — прототип")  # Заголовок окна.
        self.root.geometry("1280x820")                     # Начальный размер окна.
        self.root.minsize(1100, 700)                       # Минимальный размер окна.

        self.data = None                                   # Здесь будут храниться введённые данные.
        self.variants = ["", "", ""]                       # Тексты трёх вариантов (пока пустые).
        self.variant_texts = []                            # Список виджетов Text для вариантов.
        self.variant_lengths = []                          # Список Label с длиной текста.
        self.variant_source = ["", "", ""]                 # Источник каждого текста: «ИИ» или «шаблон».

        self._build_ui()                                   # Строим интерфейс.

    def ai_status_text(self):                              # Текст индикатора режима работы.
        if ai_is_enabled():                                # Ключ задан…
            return f"🤖 Ключ задан: {AI_MODEL} — нажмите «Тест ИИ»"  # …модель и подсказка.
        return "📋 ИИ выключен: ключ пуст, работают шаблоны"  # Иначе — режим шаблонов.

    # ---------- построение UI ----------
    def _build_ui(self):                                   # Метод построения всех виджетов.
        left = ttk.Frame(self.root, padding=12)            # Левая колонка (форма ввода).
        left.pack(side="left", fill="y")                   # Прижимаем влево, растягиваем по высоте.

        right = ttk.Frame(self.root, padding=12)           # Правая колонка (результаты).
        right.pack(side="left", fill="both", expand=True)  # Растягиваем по ширине и высоте.

        ttk.Label(left, text="Данные о продукте",          # Заголовок секции.
                  font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))  # Жирный, слева.

        self.lbl_ai = tk.Label(left, text=self.ai_status_text(),  # Строка состояния: ИИ или шаблоны.
                               font=("Segoe UI", 9), anchor="w", justify="left",
                               fg="#1f4e9c" if ai_is_enabled() else "#6b6b6b")  # Синий/серый.
        self.lbl_ai.pack(anchor="w", pady=(0, 10))         # Под заголовком.

        ttk.Label(left, text="Название продукта").pack(anchor="w")  # Подпись поля.
        self.e_product = ttk.Entry(left, width=48)         # Поле ввода названия продукта.
        self.e_product.pack(anchor="w", pady=(0, 6))       # Прижимаем влево, отступ снизу.

        ttk.Label(left, text="Описание").pack(anchor="w")  # Подпись поля.
        self.t_desc = tk.Text(left, width=48, height=3, wrap="word",  # Многострочное поле описания.
                              font=("Segoe UI", 10))       # Шрифт.
        self.t_desc.pack(anchor="w", pady=(0, 6))          # Упаковка.

        ttk.Label(left, text="Преимущества (по одному в строке)").pack(anchor="w")  # Подпись.
        self.t_benefits = tk.Text(left, width=48, height=4, wrap="word",  # Поле преимуществ.
                                  font=("Segoe UI", 10))   # Шрифт.
        self.t_benefits.pack(anchor="w", pady=(0, 6))      # Упаковка.

        ttk.Label(left, text="Цена").pack(anchor="w")      # Подпись поля цены.
        self.e_price = ttk.Entry(left, width=48)           # Поле цены.
        self.e_price.pack(anchor="w", pady=(0, 6))         # Упаковка.

        ttk.Label(left, text="Площадка размещения").pack(anchor="w")  # Подпись.
        self.cb_platform = ttk.Combobox(left, values=PLATFORMS,  # Выпадающий список площадок.
                                        state="readonly", width=45)  # Только выбор, не ввод.
        self.cb_platform.set(PLATFORMS[0])                 # По умолчанию — первая площадка.
        self.cb_platform.pack(anchor="w", pady=(0, 6))     # Упаковка.

        ttk.Label(left, text="Целевая аудитория").pack(anchor="w")  # Подпись.
        self.cb_audience = ttk.Combobox(left, values=AUDIENCES,  # Выпадающий список ЦА.
                                        state="readonly", width=45)  # Только выбор.
        self.cb_audience.set(AUDIENCES[0])                 # По умолчанию — первый сегмент.
        self.cb_audience.pack(anchor="w", pady=(0, 6))     # Упаковка.

        ttk.Label(left, text="Своя аудитория (если выбрано «Своя аудитория»)").pack(anchor="w")  # Подпись.
        self.e_audience_custom = ttk.Entry(left, width=48) # Поле своей аудитории.
        self.e_audience_custom.pack(anchor="w", pady=(0, 6))  # Упаковка.

        ttk.Label(left, text="Тон и стиль").pack(anchor="w")  # Подпись.
        self.cb_tone = ttk.Combobox(left, values=TONES_LIST,  # Выпадающий список тонов.
                                    state="readonly", width=45)  # Только выбор.
        self.cb_tone.set(TONES_LIST[0])                    # По умолчанию — первый тон.
        self.cb_tone.pack(anchor="w", pady=(0, 12))        # Упаковка, увеличенный отступ снизу.

        btns = ttk.Frame(left)                             # Контейнер для кнопок.
        btns.pack(anchor="w", pady=(4, 0))                 # Упаковка.
        ttk.Button(btns, text="⚡ Сгенерировать 3 варианта",  # Кнопка генерации.
                   command=self.generate_all).pack(side="left")  # Привязка к методу.
        ttk.Button(btns, text="Очистить",                  # Кнопка очистки.
                   command=self.clear_all).pack(side="left", padx=8)  # Привязка к методу.
        ttk.Button(btns, text="🔌 Тест ИИ",                # Кнопка проверки подключения к API.
                   command=self.test_ai).pack(side="left")  # Привязка к методу.
        ttk.Button(btns, text="🔎 Проверить ввод",         # Новая кнопка проверки полей формы.
                   command=self.check_input).pack(side="left", padx=8)  # Привязка к методу.

        # ---------- правая часть ----------
        ttk.Label(right, text="Сгенерированные варианты",  # Заголовок правой части.
                  font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))  # Жирный.

        for i in range(3):                                 # Цикл по трём вариантам.
            frame = ttk.LabelFrame(right, text=f"Вариант {i + 1}", padding=8)  # Рамка с заголовком.
            frame.pack(fill="both", expand=True, pady=4)   # Растягиваем.

            header = ttk.Frame(frame)                      # Верхняя строка рамки.
            header.pack(fill="x")                          # Растягиваем по ширине.
            lbl = ttk.Label(header, text="0 / 0 символов") # Метка длины.
            lbl.pack(side="right")                         # Прижимаем вправо.
            self.variant_lengths.append(lbl)               # Запоминаем метку.

            txt = tk.Text(frame, height=7, wrap="word",    # Поле вывода текста варианта.
                          font=("Segoe UI", 10))           # Шрифт.
            txt.pack(fill="both", expand=True, pady=(4, 0))# Растягиваем.
            txt.configure(state="disabled")                # Запрещаем пользователю печатать.
            self.variant_texts.append(txt)                 # Запоминаем виджет.

            row = ttk.Frame(frame)                         # Нижняя строка с кнопками.
            row.pack(fill="x", pady=(6, 0))                # Упаковка.
            ttk.Button(row, text="🔄 Перегенерировать",    # Кнопка перегенерации.
                       command=lambda idx=i: self.regenerate(idx)).pack(side="left")  # Привязка с замыканием idx.
            ttk.Button(row, text="📋 Копировать",          # Кнопка копирования.
                       command=lambda idx=i: self.copy_variant(idx)).pack(side="left", padx=6)  # Привязка.
            ttk.Button(row, text="✅ Проверить",           # Кнопка проверки.
                       command=lambda idx=i: self.check_variant(idx)).pack(side="left")  # Привязка.

    # ---------- сбор данных ----------
    def _read_form(self):                                  # Просто читаем поля, без проверок.
        product = self.e_product.get().strip()             # Читаем название продукта.
        benefits = [line.strip(" -•\t")                    # Каждую строку очищаем от маркеров и пробелов.
                    for line in self.t_benefits.get("1.0", "end-1c").splitlines()]  # Построчный разбор.
        benefits = [b for b in benefits if b]              # Убираем пустые строки.

        return {                                           # Возвращаем словарь со всеми полями.
            "product": product,                            # Название продукта.
            "description": self.t_desc.get("1.0", "end-1c").strip(),  # Описание.
            "benefits": benefits,                          # Список преимуществ.
            "price": self.e_price.get().strip(),           # Цена.
            "platform": self.cb_platform.get(),            # Площадка.
            "audience": self.cb_audience.get(),            # Целевая аудитория.
            "audience_custom": self.e_audience_custom.get().strip(),  # Своя аудитория.
            "tone": self.cb_tone.get(),                    # Тон.
        }                                                  # Конец словаря.

    def collect_data(self):                                # Собираем данные и проверяем имя.
        data = self._read_form()                           # Читаем форму.
        errors, _ = validate_input(data)                   # Проверяем только название.
        if errors:                                         # Имя пустое — генерацию не запускаем.
            messagebox.showwarning(                         # Показываем понятную ошибку.
                "Проверка ввода", "\n".join("• " + e for e in errors))
            return None                                    # Прерываем сбор.
        return data                                        # Возвращаем данные.

    def check_input(self):                                 # Кнопка «Проверить ввод» — без генерации.
        data = self._read_form()                           # Читаем форму.
        errors, _ = validate_input(data)                   # Проверяем только название.
        if errors:                                         # Имя пустое…
            messagebox.showwarning(                         # …показываем ошибку.
                "Проверка ввода", "\n".join("• " + e for e in errors))
        else:                                              # Имя заполнено — всё хорошо.
            messagebox.showinfo("Проверка ввода", "Название продукта указано верно.")

    # ---------- генерация ----------
    def generate_all(self):                                # Генерирует все три варианта сразу.
        data = self.collect_data()                         # Собираем данные.
        if data is None:                                   # Если данных нет…
            return                                         # …выходим.
        self.data = data                                   # Запоминаем данные для перегенераций.

        texts = None                                       # Здесь будут тексты от ИИ.
        if ai_is_enabled():                                # Если ключ задан…
            self.root.config(cursor="watch")               # Курсор-«часики» на время запроса.
            self.root.update_idletasks()                   # Даём интерфейсу перерисоваться.
            try:                                           # Пробуем ИИ…
                texts = ai_generate_variants(data, 3)      # Три текста одним запросом.
            except Exception as e:                         # При сбое…
                print("ИИ недоступен, использованы шаблоны:", e)  # …сообщаем в консоль.
            finally:                                       # В любом случае…
                self.root.config(cursor="")                # …возвращаем обычный курсор.

        for i in range(3):                                 # Цикл по трём вариантам.
            if texts and i < len(texts):                   # Если ИИ дал текст…
                self.variants[i] = texts[i]                # …берём его.
                self.variant_source[i] = "ИИ"              # …и помечаем источник.
            elif data["platform"] == "Баннер":             # Иначе баннер…
                self.variants[i] = build_short_text(data)  # …короткий шаблон.
                self.variant_source[i] = "шаблон"          # …источник — шаблон.
            else:                                          # Иначе…
                self.variants[i] = build_long_text(data)   # …длинный шаблон.
                self.variant_source[i] = "шаблон"          # …источник — шаблон.
            self.set_variant_text(i, self.variants[i])     # Выводим текст в UI.

        used = "ИИ" if texts else "шаблоны"                # Что реально сработало.
        self.lbl_ai.configure(                             # Обновляем индикатор режима.
            text=f"Последняя генерация: {used}",
            fg="#0a7d28" if texts else "#b06a00")

    def regenerate(self, index):                           # Перегенерирует один вариант.
        if not self.data:                                  # Если данные ещё не собраны…
            messagebox.showinfo("Подсказка", "Сначала нажмите «Сгенерировать 3 варианта».")  # Подсказка.
            return                                         # Выход.
        outcome = regenerate_with_validation(               # Переделываем и проверяем заново.
            self.data,
            self.variants[index],
            validate_fn=validate_text,
            rewrite_fn=rewrite_text_for_regeneration,
            forbidden=FORBIDDEN,
            platform_limits=PLATFORM_LIMITS,
            max_attempts=3,
        )
        text = outcome["text"]                             # Итоговый текст.
        source = outcome["source"]                         # Источник: ИИ или шаблон.
        self.variants[index] = text                        # Запоминаем текст.
        self.variant_source[index] = source                # Запоминаем источник.
        self.set_variant_text(index, text)                 # Обновляем UI.
        self.lbl_ai.configure(                             # Обновляем индикатор режима.
            text=f"Последняя перегенерация: {source} · попыток {outcome['attempts']}",
            fg="#0a7d28" if outcome["ok"] else "#b06a00")
        if not outcome["ok"]:                              # Если так и не прошли проверку…
            messagebox.showwarning(                        # …показываем, что осталось.
                f"Вариант {index + 1}",
                "После 3 попыток остались замечания:\n\n"
                + "\n".join("• " + s for s in outcome["issues"]))

    def set_variant_text(self, index, text):               # Выводит текст в нужный виджет.
        widget = self.variant_texts[index]                 # Берём виджет по индексу.
        widget.configure(state="normal")                   # Временно разрешаем изменение.
        widget.delete("1.0", "end")                        # Очищаем поле.
        widget.insert("1.0", text)                         # Вставляем новый текст.
        widget.configure(state="disabled")                 # Снова блокируем редактирование.

        limit = PLATFORM_LIMITS.get(self.data["platform"], (0, 0))[1]  # Лимит символов под площадку.
        source = self.variant_source[index]                # Источник текста («ИИ» или «шаблон»).
        suffix = f" · {source}" if source else ""          # Добавка к метке длины.
        self.variant_lengths[index].configure(             # Обновляем метку длины.
            text=f"{len(text)} / {limit} символов{suffix}")  # Формат «факт / лимит · источник».

    # ---------- копирование и проверка ----------
    def copy_variant(self, index):                         # Копирует текст варианта в буфер обмена.
        text = self.variants[index]                        # Берём текст по индексу.
        if not text:                                       # Если пусто…
            messagebox.showinfo("Подсказка", "Сначала сгенерируйте текст.")  # Подсказка.
            return                                         # Выход.
        self.root.clipboard_clear()                        # Чистим буфер обмена.
        self.root.clipboard_append(text)                   # Кладём текст.
        messagebox.showinfo("Готово", f"Вариант {index + 1} скопирован в буфер обмена.")  # Уведомление.

    def check_variant(self, index):                        # Проверяет текст варианта.
        text = self.variants[index]                        # Берём текст.
        if not text:                                       # Если пусто…
            messagebox.showinfo("Подсказка", "Сначала сгенерируйте текст.")  # Подсказка.
            return                                         # Выход.
        issues = validate_text(text, self.data["platform"])# Получаем список замечаний.
        if issues:                                         # Если замечания есть…
            messagebox.showwarning(                        # …показываем окно с предупреждениями.
                f"Проверка варианта {index + 1}",          # Заголовок.
                "Найдены замечания:\n\n" + "\n".join("• " + s for s in issues))  # Текст.
        else:                                              # Иначе…
            messagebox.showinfo(                           # …показываем «всё ок».
                f"Проверка варианта {index + 1}",          # Заголовок.
                "Текст соответствует базовым требованиям:\n"  # Сообщение.
                "• длина в норме\n• есть призыв к действию\n"
                "• запрещённых формулировок не найдено")

    # ---------- сброс ----------
    def clear_all(self):                                   # Полная очистка формы и результатов.
        self.e_product.delete(0, "end")                    # Чистим название.
        self.t_desc.delete("1.0", "end")                   # Чистим описание.
        self.t_benefits.delete("1.0", "end")               # Чистим преимущества.
        self.e_price.delete(0, "end")                      # Чистим цену.
        self.e_audience_custom.delete(0, "end")            # Чистим свою аудиторию.
        self.data = None                                   # Сбрасываем сохранённые данные.
        self.variants = ["", "", ""]                       # Сбрасываем тексты вариантов.
        self.variant_source = ["", "", ""]                 # Сбрасываем источники текстов.
        for i in range(3):                                 # Цикл по трём вариантам.
            w = self.variant_texts[i]                      # Берём виджет.
            w.configure(state="normal")                    # Разрешаем изменение.
            w.delete("1.0", "end")                         # Очищаем.
            w.configure(state="disabled")                  # Блокируем обратно.
            self.variant_lengths[i].configure(text="0 / 0 символов")  # Сбрасываем метку длины.

    def test_ai(self):                                     # Проверка подключения к ИИ.
        if not ai_is_enabled():                            # Ключа нет…
            messagebox.showwarning(                        # …объясняем, что делать.
                "ИИ выключен",
                "В файле config.py не задан AI_API_KEY.\n"
                "Вставьте ключ в строку AI_API_KEY = \"...\" и перезапустите программу.")
            return
        self.root.config(cursor="watch")                   # Курсор-«часики».
        self.root.update_idletasks()                       # Перерисовываем окно.
        try:                                               # Пробуем короткий запрос…
            answer = ai_ping()                             # …к модели.
            self.lbl_ai.configure(text=f"🤖 ИИ работает: {AI_MODEL}", fg="#0a7d28")  # Зелёный статус.
            messagebox.showinfo(                           # Сообщаем успех.
                "ИИ подключён",
                f"Модель {AI_MODEL} ответила: «{answer}».\n"
                "Генерация текстов будет идти через ИИ.")
        except Exception as e:                             # Если ошибка…
            self.lbl_ai.configure(text="⚠️ ИИ не отвечает — работают шаблоны", fg="#b00020")  # Красный статус.
            messagebox.showerror(                          # …показываем причину.
                "ИИ не работает",
                f"Запрос к {AI_BASE_URL} не удался:\n{str(e)[:500]}\n\n"
                "Проверьте ключ, название модели и доступ к интернету.\n"
                "Пока программа показывает шаблонные тексты.")
        finally:                                           # В любом случае…
            self.root.config(cursor="")                    # …обычный курсор.


# ============================ ЗАПУСК ============================

def main():                                                # Точка входа программы.
    root = tk.Tk()                                         # Создаём главное окно.
    try:                                                   # Пытаемся…
        ttk.Style().theme_use("vista")                     # …поставить аккуратную тему Windows.
    except tk.TclError:                                    # Если темы нет (не Windows)…
        pass                                               # …молча игнорируем.
    print("Режим ИИ:",                                  # Пишем в консоль, что включилось.
          f"включён ({AI_MODEL})" if ai_is_enabled() else "выключен — ключ не задан, шаблоны")
    AdAssistantApp(root)                                   # Создаём приложение.
    root.mainloop()                                        # Запускаем цикл обработки событий.


if __name__ == "__main__":                                 # Если файл запущен напрямую…
    main()                                                 # …запускаем main().
