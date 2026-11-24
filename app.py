# -*- coding: utf-8 -*-
# ↑ Указываем кодировку UTF-8 — чтобы кириллица и эмодзи в строках не ломались.

"""
Кейс 9. Регион 2 — прототип ИИ-помощника по генерации рекламных текстов.
Модули: ввод данных → генерация → адаптация под ЦА → проверка → UI → документация.
Запуск: python app.py   (ключ API — в файле config.py рядом с программой)
"""

import random                                              # Импорт модуля random — нужен для случайного выбора фраз.
import tkinter as tk                                       # Импорт tkinter — базовый GUI-движок (основной модуль).
from tkinter import ttk, messagebox                        # ttk — «современные» виджеты; messagebox — всплывающие окна.
import json                                                # Разбор JSON-ответа модели.
import os                                                  # Пути к файлам (ищем config.py рядом).
import sys                                                 # Управление путями импорта.
import requests                                            # HTTP-запросы к API (пакет уже установлен).
from pathlib import Path                                    # Безопасный путь к фону.
try:
    from PIL import Image, ImageTk                         # Загрузка и масштабирование JPG-фона.
except ImportError:
    Image = ImageTk = None
import guides as guide
import validator as text_validator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Чтобы config.py нашёлся при любом способе запуска.
try:                                                       # Ключи API держим в отдельном файле config.py…
    from config import AI_API_KEY, AI_BASE_URL, AI_MODEL   # …он лежит рядом с этим файлом.
except ImportError:                                        # Если файла нет…
    AI_API_KEY = ""                                        # …ключа нет, работаем на шаблонах.
    AI_BASE_URL = "https://api.deepseek.com/v1"            # Адрес API по умолчанию.
    AI_MODEL = "deepseek-chat"                             # Модель по умолчанию.


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
    lo, hi = guide.PLATFORM_LIMITS.get(data["platform"], (0, 5000))  # Лимиты символов под площадку.
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
        f"Запрещено использовать: {', '.join(guide.FORBIDDEN)}.\n"
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
    if key in guide.AUDIENCE_STYLES:                             # Если аудитория из готовых шаблонов…
        return guide.AUDIENCE_STYLES[key]                        # …возвращаем её стиль.
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
    tone = guide.TONES[data["tone"]]                             # Получаем блок тональности.
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

    parts.append(random.choice(guide.CTA_BY_PLATFORM[data["platform"]]))  # Случайный CTA под площадку.
    parts.append(tone["closing"].format(product=data["product"]))   # Подпись с подстановкой названия.

    return "\n".join(parts)                                # Склеиваем строки через \n.


def build_short_text(data):                                # Собирает короткий текст под баннер.
    """Короткий текст под баннер (до ~90 символов)."""
    benefit = data["benefits"][0] if data["benefits"] else data["description"]  # Берём 1-ю выгоду или описание.
    if benefit and len(benefit) > 45:                      # Если выгода слишком длинная…
        benefit = benefit[:45].rstrip() + "…"              # …обрезаем до 45 симв. и добавляем многоточие.
    cta = random.choice(guide.CTA_BY_PLATFORM["Баннер"])         # Случайный короткий CTA.
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


# ============================ ВАЛИДАЦИЯ ============================

# ============================ ИНТЕРФЕЙС ============================

# ---------- скруглённые элементы (мягкий квадрат) ----------
def _rounded_rect(canvas, x1, y1, x2, y2, radius, fill, outline, width=1, tags=None):
    # Рисует прямоугольник со скруглёнными углами на Canvas.
    r = max(2, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=32,
                                 fill=fill, outline=outline, width=width, tags=tags)


class RoundedField(tk.Frame):
    # Поле ввода в «мягком квадрате»: скруглённый светло-голубой фон вместо белого.
    BG = "#EAF6FF"
    BORDER = "#B8D4F0"
    FOCUS = "#60A5FA"
    FG = "#0F2942"

    def __init__(self, parent, kind="entry", radius=8, height=32,
                 font=("Segoe UI", 10)):
        parent_bg = parent.cget("bg")
        super().__init__(parent, bg=parent_bg, bd=0, highlightthickness=0)
        self.radius = radius
        self._kind = kind
        self._focused = False
        self.canvas = tk.Canvas(self, bg=parent_bg, bd=0, highlightthickness=0, height=height)
        self.canvas.pack(fill="both", expand=True)
        if kind == "text":
            self.widget = tk.Text(self.canvas, bd=0, relief="flat", highlightthickness=0,
                                  bg=self.BG, fg=self.FG, insertbackground="#0369A1",
                                  font=font, wrap="word", padx=6, pady=4)
        elif kind == "combo":
            self.widget = ttk.Combobox(self.canvas, state="readonly", font=font,
                                       style="Field.TCombobox")
        else:
            self.widget = tk.Entry(self.canvas, bd=0, relief="flat", highlightthickness=0,
                                   bg=self.BG, fg=self.FG, insertbackground="#0369A1",
                                   font=font)
        self._win = self.canvas.create_window(0, 0, anchor="nw", window=self.widget)
        self.canvas.bind("<Configure>", self._redraw)
        self.widget.bind("<FocusIn>", lambda _e: self._redraw(True), add="+")
        self.widget.bind("<FocusOut>", lambda _e: self._redraw(False), add="+")
        self._redraw()

    def _redraw(self, focused=None):
        if focused is not None:
            self._focused = bool(focused)
        c = self.canvas
        width, height = c.winfo_width(), c.winfo_height()
        if width < 4 or height < 4:
            return
        c.delete("field")
        _rounded_rect(c, 1, 1, width - 1, height - 1, self.radius, self.BG,
                      self.FOCUS if self._focused else self.BORDER, tags="field")
        c.tag_lower("field")
        if self._kind == "text":
            pad = 5
            c.coords(self._win, pad, pad)
            c.itemconfigure(self._win, width=width - 2 * pad, height=height - 2 * pad)
        else:
            c.coords(self._win, 8, 2)
            c.itemconfigure(self._win, width=width - 16, height=height - 4)


class RoundedButton(tk.Canvas):
    # Кнопка со скруглёнными углами в стиле design.py (radius 10, #BAE6FD).
    def __init__(self, parent, text, command, radius=10, bg="#BAE6FD", hover="#93C5FD",
                 fg="#0C4A6E", border="#7DD3FC", hover_border="#60A5FA",
                 font=("Segoe UI", 10, "bold"), width=120, height=32):
        parent_bg = parent.cget("bg")
        super().__init__(parent, bg=parent_bg, bd=0, highlightthickness=0,
                         width=width, height=height, cursor="hand2")
        self._text = text
        self._command = command
        self._radius = radius
        self._bg = bg
        self._hover = hover
        self._fg = fg
        self._border = border
        self._hover_border = hover_border
        self._font = font
        self._hovered = False
        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda _e: self._command())
        self._redraw()

    def _on_enter(self, _event=None):
        self._hovered = True
        self._redraw()

    def _on_leave(self, _event=None):
        self._hovered = False
        self._redraw()

    def _redraw(self):
        width, height = self.winfo_width(), self.winfo_height()
        if width < 4 or height < 4:
            return
        self.delete("all")
        _rounded_rect(self, 1, 1, width - 1, height - 1, self._radius,
                      self._hover if self._hovered else self._bg,
                      self._hover_border if self._hovered else self._border)
        self.create_text(width // 2, height // 2, text=self._text,
                         fill=self._fg, font=self._font)


class AdAssistantApp:                                      # Класс приложения (весь UI).
    def __init__(self, root):                              # Конструктор — вызывается при запуске.
        self.root = root                                   # Сохраняем ссылку на главное окно.
        self.root.title("ИИ-помощник по рекламным текстам — прототип")  # Заголовок окна.
        self.root.geometry("1280x820")                     # Начальный размер окна.
        self.root.minsize(1100, 700)                       # Минимальный размер окна.
        self.root.configure(bg="#F0F7FF")                  # Цвет интерфейса из design.py.
        self._bg_original = None                            # Исходный фон.
        self._bg_photo = None                               # Ссылка, чтобы Tkinter не удалил изображение.
        self._setup_background()                            # Подключаем fon.jpg.

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

    def _setup_background(self):                         # Загружает fon.jpg (показ — в _build_ui).
        if Image is None:
            return
        image_path = Path(__file__).resolve().parent / "fon.jpg"
        if not image_path.exists():
            return
        try:
            self._bg_original = Image.open(image_path).convert("RGB")
        except Exception as exc:
            print(f"Фон не загружен: {exc}")

    def _attach_background(self, host):                  # Кладёт фото под карточки интерфейса.
        if getattr(self, "_bg_original", None) is None:
            return
        self._bg_host = host
        self._bg_size = None
        self._bg_label = tk.Label(host, bd=0, highlightthickness=0)
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._bg_label.lower()
        host.bind("<Configure>", self._resize_background)
        self._resize_background()

    def _resize_background(self, _event=None):           # Масштабирует фото по размеру окна (cover).
        if getattr(self, "_bg_original", None) is None or not hasattr(self, "_bg_label"):
            return
        width = max(self._bg_host.winfo_width(), 1)
        height = max(self._bg_host.winfo_height(), 1)
        if self._bg_size == (width, height):
            return
        self._bg_size = (width, height)
        try:
            image = self._bg_original.copy()
            scale = max(width / image.width, height / image.height)
            image = image.resize((max(int(image.width * scale) + 1, width),
                                  max(int(image.height * scale) + 1, height)),
                                 Image.Resampling.LANCZOS)
            left = max((image.width - width) // 2, 0)
            top = max((image.height - height) // 2, 0)
            image = image.crop((left, top, left + width, top + height))
            self._bg_photo = ImageTk.PhotoImage(image)
            self._bg_label.configure(image=self._bg_photo)
        except Exception as exc:
            print(f"Фон не масштабирован: {exc}")

    # ---------- построение UI ----------
    def _build_ui(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Field.TCombobox", fieldbackground="#EAF6FF", background="#EAF6FF",
                        foreground="#0F2942", borderwidth=0, relief="flat",
                        arrowcolor="#0369A1", padding=(6, 4))
        style.map("Field.TCombobox",
                  fieldbackground=[("readonly", "#EAF6FF"), ("focus", "#EAF6FF")],
                  background=[("readonly", "#EAF6FF"), ("active", "#E0F2FE")])
        style.configure("Card.TNotebook", background="#FFFFFF", borderwidth=0)
        style.configure("Card.TNotebook.Tab", background="#E0F2FE", foreground="#3B5978",
                        padding=(12, 7), font=("Segoe UI", 9, "bold"))
        style.map("Card.TNotebook.Tab", background=[("selected", "#BAE6FD")],
                  foreground=[("selected", "#0369A1")])
        style.configure("Card.Vertical.TScrollbar", background="#E0F2FE",
                        troughcolor="#FFFFFF", borderwidth=0, arrowcolor="#0369A1")

        shell = tk.Frame(self.root, bg="#F0F7FF")
        shell.pack(fill="both", expand=True, padx=26, pady=20)
        self._attach_background(shell)                     # Фото fon.jpg под карточками.
        header = tk.Frame(shell, bg="#FFFFFF", padx=20, pady=12)
        header.pack(fill="x", pady=(0, 12))
        tk.Label(header, text="ИИ-помощник для генерации рекламы", bg="#FFFFFF",
                 fg="#0F2942", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(header, text="Центр-инвест  •  адаптация под аудиторию  •  проверка текста",
                 bg="#FFFFFF", fg="#3B5978", font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))
        self.lbl_ai = tk.Label(header, text=self.ai_status_text(), bg="#FFFFFF",
                               fg="#1f4e9c" if ai_is_enabled() else "#6b6b6b",
                               font=("Segoe UI", 9), anchor="w")
        self.lbl_ai.pack(anchor="w", pady=(6, 0))

        body = tk.Frame(shell, bg="#F0F7FF")
        body.pack(fill="both", expand=True)
        left = tk.Frame(body, bg="#FFFFFF", padx=16, pady=12)
        left.pack(side="left", fill="y", padx=(0, 12))
        right = tk.Frame(body, bg="#FFFFFF", padx=18, pady=14)
        right.pack(side="left", fill="both", expand=True)

        # Кнопки прижаты к низу карточки: они видны всегда, даже если поля не помещаются.
        actions = tk.Frame(left, bg="#FFFFFF")
        actions.pack(side="bottom", fill="x", pady=(10, 0))
        RoundedButton(actions, "✨ Сгенерировать", self.generate_all).pack(fill="x", pady=(0, 6))
        RoundedButton(actions, "🔌 Тест ИИ", self.test_ai, bg="#FFFFFF", fg="#0369A1",
                      border="#B8D4F0", hover="#EAF6FF",
                      hover_border="#7DD3FC").pack(fill="x", pady=(0, 4))
        RoundedButton(actions, "Очистить", self.clear_all, bg="#FFFFFF", fg="#0369A1",
                      border="#B8D4F0", hover="#EAF6FF",
                      hover_border="#7DD3FC").pack(fill="x")

        # Поля — в прокручиваемой области, чтобы ничего не пропадало на маленьком экране.
        fields_wrap = tk.Frame(left, bg="#FFFFFF")
        fields_wrap.pack(fill="both", expand=True)
        fields_canvas = tk.Canvas(fields_wrap, bg="#FFFFFF", bd=0, highlightthickness=0, width=430)
        fields_scroll = ttk.Scrollbar(fields_wrap, orient="vertical",
                                      style="Card.Vertical.TScrollbar",
                                      command=fields_canvas.yview)
        fields_canvas.configure(yscrollcommand=fields_scroll.set)
        fields_scroll.pack(side="right", fill="y")
        fields_canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(fields_canvas, bg="#FFFFFF")
        inner_id = fields_canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda _e: fields_canvas.configure(scrollregion=fields_canvas.bbox("all")))
        fields_canvas.bind("<Configure>",
                           lambda e: fields_canvas.itemconfigure(inner_id, width=e.width))

        def _wheel(event):
            widget = event.widget
            if isinstance(widget, (tk.Text, ttk.Combobox)):
                return
            x, y = fields_canvas.winfo_pointerxy()
            if not (fields_canvas.winfo_rootx() <= x <= fields_canvas.winfo_rootx() + fields_canvas.winfo_width()
                    and fields_canvas.winfo_rooty() <= y <= fields_canvas.winfo_rooty() + fields_canvas.winfo_height()):
                return
            fields_canvas.yview_scroll(int(-event.delta / 120), "units")

        self.root.bind_all("<MouseWheel>", _wheel)

        tk.Label(inner, text="Параметры рекламы", bg="#FFFFFF", fg="#0F2942",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))

        self._field_label(inner, "Название продукта")
        self.f_product = RoundedField(inner, "entry", height=32)
        self.f_product.pack(fill="x", pady=(0, 6))
        self.e_product = self.f_product.widget

        self._field_label(inner, "Описание предложения")
        self.f_desc = RoundedField(inner, "text", height=64)
        self.f_desc.pack(fill="x", pady=(0, 6))
        self.t_desc = self.f_desc.widget

        self._field_label(inner, "Преимущества (по одному в строке)")
        self.f_benefits = RoundedField(inner, "text", height=64)
        self.f_benefits.pack(fill="x", pady=(0, 6))
        self.t_benefits = self.f_benefits.widget

        row1 = tk.Frame(inner, bg="#FFFFFF")
        row1.pack(fill="x")
        col1 = tk.Frame(row1, bg="#FFFFFF")
        col1.pack(side="left", fill="x", expand=True, padx=(0, 5))
        col2 = tk.Frame(row1, bg="#FFFFFF")
        col2.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self._field_label(col1, "Цена / оффер")
        self.f_price = RoundedField(col1, "entry", height=32)
        self.f_price.pack(fill="x", pady=(0, 6))
        self.e_price = self.f_price.widget
        self._field_label(col2, "Площадка")
        self.f_platform = RoundedField(col2, "combo", height=32)
        self.f_platform.pack(fill="x", pady=(0, 6))
        self.cb_platform = self.f_platform.widget
        self.cb_platform.configure(values=guide.PLATFORMS)
        self.cb_platform.set(guide.PLATFORMS[0])

        row2 = tk.Frame(inner, bg="#FFFFFF")
        row2.pack(fill="x")
        col3 = tk.Frame(row2, bg="#FFFFFF")
        col3.pack(side="left", fill="x", expand=True, padx=(0, 5))
        col4 = tk.Frame(row2, bg="#FFFFFF")
        col4.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self._field_label(col3, "Целевая аудитория")
        self.f_audience = RoundedField(col3, "combo", height=32)
        self.f_audience.pack(fill="x", pady=(0, 6))
        self.cb_audience = self.f_audience.widget
        self.cb_audience.configure(values=guide.AUDIENCES)
        self.cb_audience.set(guide.AUDIENCES[0])
        self._field_label(col4, "Тональность")
        self.f_tone = RoundedField(col4, "combo", height=32)
        self.f_tone.pack(fill="x", pady=(0, 6))
        self.cb_tone = self.f_tone.widget
        self.cb_tone.configure(values=guide.TONES_LIST)
        self.cb_tone.set(guide.TONES_LIST[0])

        self._field_label(inner, "Своя аудитория (необязательно)")
        self.f_audience_custom = RoundedField(inner, "entry", height=32)
        self.f_audience_custom.pack(fill="x", pady=(0, 2))
        self.e_audience_custom = self.f_audience_custom.widget

        tk.Label(right, text="Сгенерированные тексты", bg="#FFFFFF", fg="#0F2942",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(right, text="Редактируйте текст во вкладке, затем проверьте или скопируйте вариант.",
                 bg="#FFFFFF", fg="#3B5978", font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 10))
        notebook = ttk.Notebook(right, style="Card.TNotebook")
        notebook.pack(fill="both", expand=True)
        self.variant_fields = []
        for i in range(3):
            tab = tk.Frame(notebook, bg="#FFFFFF", padx=10, pady=10)
            notebook.add(tab, text=f"✨ Вариант #{i + 1}")
            lbl = tk.Label(tab, text="0 / 0 символов", bg="#FFFFFF", fg="#3B5978",
                           font=("Segoe UI", 9))
            lbl.pack(anchor="e")
            self.variant_lengths.append(lbl)
            field = RoundedField(tab, "text", height=300)
            field.pack(fill="both", expand=True, pady=(5, 10))
            self.variant_fields.append(field)
            self.variant_texts.append(field.widget)
            row = tk.Frame(tab, bg="#FFFFFF")
            row.pack(fill="x")
            RoundedButton(row, "🔄 Перегенерировать", lambda idx=i: self.regenerate(idx),
                          width=170, height=32).pack(side="left")
            RoundedButton(row, "📋 Копировать", lambda idx=i: self.copy_variant(idx),
                          width=150, height=32, bg="#FFFFFF", fg="#0369A1",
                          border="#B8D4F0", hover="#EAF6FF",
                          hover_border="#7DD3FC").pack(side="left", padx=6)
            RoundedButton(row, "✅ Проверить", lambda idx=i: self.check_variant(idx),
                          width=140, height=32, bg="#FFFFFF", fg="#0369A1",
                          border="#B8D4F0", hover="#EAF6FF",
                          hover_border="#7DD3FC").pack(side="left")

    def _field_label(self, parent, text):
        tk.Label(parent, text=text, bg="#FFFFFF", fg="#0F2942",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))

    # ---------- сбор данных ----------
    def collect_data(self):                                # Собирает введённые данные в словарь.
        product = self.e_product.get().strip()             # Читаем название продукта.
        if not product:                                    # Если пусто…
            messagebox.showwarning("Внимание", "Укажите название продукта.")  # …предупреждение.
            return None                                    # Прерываем сбор.

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
            messagebox.showinfo("Подсказка", "Сначала нажмите «Сгенерировать».")  # Подсказка.
            return                                         # Выход.
        text, source = generate_text_with_source(self.data)  # Новый текст и его источник.
        self.variants[index] = text                        # Запоминаем текст.
        self.variant_source[index] = source                # Запоминаем источник.
        self.set_variant_text(index, text)                 # Обновляем UI.
        self.lbl_ai.configure(                             # Обновляем индикатор режима.
            text=f"Последняя генерация: {source}",
            fg="#0a7d28" if source == "ИИ" else "#b06a00")

    def set_variant_text(self, index, text):               # Выводит текст в нужный виджет.
        widget = self.variant_texts[index]                 # Берём виджет по индексу.
        widget.configure(state="normal")                   # Временно разрешаем изменение.
        widget.delete("1.0", "end")                        # Очищаем поле.
        widget.insert("1.0", text)                         # Вставляем новый текст.
        widget.configure(state="disabled")                 # Снова блокируем редактирование.

        limit = guide.PLATFORM_LIMITS.get(self.data["platform"], (0, 0))[1]  # Лимит символов под площадку.
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
        max_length = guide.PLATFORM_LIMITS.get(self.data["platform"], (0, 5000))[1]
        result = text_validator.validate_text(text, max_length=max_length)
        messages = result["errors"] + result["warnings"]
        if messages:
            messagebox.showwarning(
                f"Проверка варианта {index + 1}",
                "Найдены замечания:\n\n" + "\n".join("• " + s for s in messages))
        else:
            messagebox.showinfo(
                f"Проверка варианта {index + 1}",
                "Текст соответствует базовым требованиям:\n"
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
