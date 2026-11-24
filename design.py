import os
import base64
import random
import re
import datetime
import streamlit as st

# ==========================================
# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ И ФОНОВОЕ ИЗОБРАЖЕНИЕ
# ==========================================
st.set_page_config(
    page_title="ИИ-Копирайтер | Центр-инвест",
    page_icon="🚀",
    layout="wide"
)

def get_base64_bg(image_filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(base_dir, image_filename)
    if not os.path.exists(image_path):
        st.warning(f"⚠️ Картинка {image_filename} не найдена в папке: {base_dir}")
        return ""
    with open(image_path, "rb") as f:
        raw = f.read()
    # Определяем реальный формат файла по первым байтам
    if raw.startswith(b"\x89PNG"):
        mime = "image/png"
    elif raw.startswith(b"RIFF") and b"WEBP" in raw[:16]:
        mime = "image/webp"
    else:
        mime = "image/jpeg"
    encoded = base64.b64encode(raw).decode("utf-8").replace("\n", "")
    return f"data:{mime};base64,{encoded}"

bg_data_uri = get_base64_bg("fon.jpg")

bg_css = (
    f'background-image: linear-gradient(rgba(240, 247, 255, 0.55), rgba(240, 247, 255, 0.55)), url("{bg_data_uri}") !important;'
    if bg_data_uri else ""
)

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
        background-color: #F0F7FF !important;
        {bg_css}
        background-size: cover !important;
        background-position: center center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
        color: #0F2942 !important;
        font-family: 'Inter', sans-serif !important;
    }}

    [data-testid="stHeader"] {{
        background: transparent !important;
    }}

    .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 1.5rem !important;
    }}

    div.stButton > button, div.stFormSubmitButton > button {{
        background-color: #BAE6FD !important;
        color: #0C4A6E !important;
        border: 1px solid #7DD3FC !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease;
    }}
    div.stButton > button:hover, div.stFormSubmitButton > button:hover {{
        background-color: #93C5FD !important;
        color: #082F49 !important;
        border-color: #60A5FA !important;
    }}

    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: rgba(255, 255, 255, 0.94) !important;
        border: 1px solid #D0E4F7 !important;
        border-radius: 14px !important;
        padding: 16px;
        box-shadow: 0 4px 16px rgba(15, 41, 66, 0.05);
    }}

    input, textarea, div[data-baseweb="select"] > div {{
        background-color: #F7FBFF !important;
        border-color: #B8D4F0 !important;
        color: #0F2942 !important;
        border-radius: 8px !important;
    }}

    button[data-baseweb="tab"] {{
        font-weight: 600 !important;
        color: #3B5978 !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: #0369A1 !important;
        border-bottom-color: #38BDF8 !important;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. БАЗЫ ДАННЫХ И НАСТРОЙКИ (ЦА, ТОН, ЛИМИТЫ)
# ==========================================
AUDIENCE_PRESETS = {
    "Молодёжь (18–25)": {
        "hooks": [
            "Хватит сливать бюджет впустую — зацени {name}!",
            "Тот самый апгрейд, который ты искал: {name}.",
            "Залетай в тему с {name} — быстро, чётко и без лишней духоты."
        ],
        "bodies": [
            "Короче, суть простая: {desc}. Главный плюс — {adv}.",
            "Без лишней воды: {desc}. Почему это топ? Потому что {adv}.",
            "{desc}. Реально экономит время и нервы, ведь {adv}."
        ],
        "ctas": [
            "Забирай сейчас за {price} — ссылка ниже 👇",
            "Кликай и тестируй, пока прайс всего {price}!",
            "Жми сюда и забирай свой вариант за {price}."
        ]
    },
    "Семьи с детьми": {
        "hooks": [
            "Больше времени для близких вместе с {name}.",
            "Забота и комфорт каждый день: встречайте {name}.",
            "Надёжное решение для всей семьи — {name}."
        ],
        "bodies": [
            "{desc}. Мы продумали всё до мелочей: {adv}.",
            "Выбирая {name}, вы получаете спокойствие: {desc}. Главное преимущество — {adv}.",
            "Идеально впишется в ваш ритм жизни: {desc}. Плюс к этому — {adv}."
        ],
        "ctas": [
            "Оформите заказ за {price} и порадуйте семью уже сегодня.",
            "Узнайте подробности и закажите по цене {price} →",
            "Попробуйте {name} за {price} — перейдите на сайт."
        ]
    },
    "B2B-клиенты / Бизнес": {
        "hooks": [
            "Оптимизируйте рабочие процессы с помощью {name}.",
            "{name}: измеримый результат и надёжность для вашего бизнеса.",
            "Снижайте издержки и масштабируйтесь вместе с {name}."
        ],
        "bodies": [
            "{desc}. Ключевой аргумент для внедрения: {adv}.",
            "Практичный инструмент для задач бизнеса: {desc}. Вы получаете: {adv}.",
            "Решение проверено на практике: {desc}. Конкурентное преимущество — {adv}."
        ],
        "ctas": [
            "Запросите коммерческое предложение (от {price}).",
            "Оставьте заявку на расчёт — стоимость от {price}.",
            "Перейдите по ссылке, чтобы обсудить внедрение ({price})."
        ]
    },
    "Пенсионеры": {
        "hooks": [
            "Просто, понятно и с пользой: {name}.",
            "Доступное и проверенное решение — {name}.",
            "Позаботьтесь о себе с комфортом: {name}."
        ],
        "bodies": [
            "{desc}. Всё устроено максимально удобно: {adv}.",
            "Никаких сложностей: {desc}. Главное достоинство — {adv}.",
            "{desc}. Вы оцените практичность, ведь {adv}."
        ],
        "ctas": [
            "Закажите по честной цене {price} — нажмите здесь.",
            "Узнайте подробнее и оформите за {price}.",
            "Позвоните или оставьте заявку, цена — {price}."
        ]
    }
}

TONE_MODIFIERS = {
    "Дружелюбный 😊": ("Привет! ", " 😊"),
    "Формальный / Деловой": ("Уважаемый клиент. ", "."),
    "Молодёжный 🔥": ("Йоу! ", " 🔥"),
    "Экспертный": ("Факт: ", " — проверено практикой.")
}

PLATFORM_LIMITS = {
    "Соцсети (VK / TG)": 500,
    "Баннер (короткий)": 140,
    "Email-рассылка": 1000,
    "Карточка товара (WB / Ozon)": 600
}

FORBIDDEN_WORDS = {
    "самый лучший": "один из лучших",
    "гарантированный результат": "предсказуемый результат",
    "гарантируем": "стремимся обеспечить",
    "100%": "высокая вероятность",
    "№1": "лидер в сегменте",
    "номер один": "один из лидеров",
    "абсолютно бесплатно": "без доплат на старте"
}

CTA_MARKERS = [
    "перейд", "жми", "клик", "закаж", "оформ",
    "забир", "оставьте", "запрос", "узнай", "попроб", "ссылк"
]

# ==========================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ГЕНЕРАЦИИ И ПРОВЕРКИ
# ==========================================
def get_preset(audience, custom_aud=""):
    if audience in AUDIENCE_PRESETS:
        return AUDIENCE_PRESETS[audience]
    focus = custom_aud.strip() if custom_aud.strip() else "ваши задачи и комфорт"
    return {
        "hooks": [
            f"Специальное предложение для тех, кому важны {focus}: {{name}}.",
            f"Обратите внимание на {{name}} — создано с учётом запроса: {focus}.",
            f"Новое решение для вашей аудитории ({focus}): {{name}}.",
        ],
        "bodies": [
            "{desc}. Ключевое преимущество: {adv}.",
            "Почему стоит выбрать {name}? {desc}. Главный плюс — {adv}.",
            "{desc}. Выгодно выделяется тем, что {adv}.",
        ],
        "ctas": [
            "Узнайте подробности и оформите за {price} →",
            "Перейдите по ссылке, чтобы получить предложение ({price}).",
            "Оставьте заявку сейчас — стоимость {price}.",
        ]
    }


def build_part(part_type, audience, data, tone, index=None, exclude=None, custom_aud=""):
    preset = get_preset(audience, custom_aud)
    templates = preset[part_type]
    prefix, suffix = TONE_MODIFIERS[tone]

    def format_piece(tpl):
        text = tpl.format(**data)
        if part_type == "hooks":
            text = prefix + text
        elif part_type == "bodies":
            text = text.rstrip(".") + suffix
        return text

    if index is not None:
        return format_piece(templates[index % len(templates)])

    candidates = [format_piece(t) for t in templates if format_piece(t) != exclude]
    return random.choice(candidates) if candidates else exclude


def validate_text(text, platform):
    issues = []
    limit = PLATFORM_LIMITS[platform]
    if len(text) > limit:
        issues.append(f"⚠️ Превышен лимит площадки ({len(text)}/{limit} симв.)")

    found_forbidden = [
        w for w in FORBIDDEN_WORDS
        if re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE)
    ]
    if found_forbidden:
        issues.append(
            f"🚫 Запрещённые слова по ФЗ «О рекламе»: {', '.join(found_forbidden)}"
        )

    if not any(marker in text.lower() for marker in CTA_MARKERS):
        issues.append("⚠️ Не найден явный призыв к действию (CTA)")
    return issues


def clean_forbidden(text):
    for bad, good in FORBIDDEN_WORDS.items():
        text = re.sub(rf"\b{re.escape(bad)}\b", good, text, flags=re.IGNORECASE)
    return text


# ==========================================
# 4. ИНТЕРФЕЙС: 2 КОЛОНКИ НА ГЛАВНОМ ЭКРАНЕ
# ==========================================
st.title("🚀 ИИ-помощник для генерации рекламы (Центр-инвест)")
st.caption(
    "Модуль ввода параметров → адаптация под целевую аудиторию → "
    "генерация 3 вариантов → проверка по ФЗ «О рекламе»."
)

left_col, right_col = st.columns([1, 1.7], gap="large")

# ---------------- ЛЕВАЯ КОЛОНКА: ФОРМА ВВОДА ----------------
with left_col:
    with st.container(border=True):
        st.subheader("📋 Параметры рекламы")

        audience = st.selectbox(
            "Целевая аудитория",
            list(AUDIENCE_PRESETS.keys()) + ["Своя аудитория"]
        )
        custom_aud = ""
        if audience == "Своя аудитория":
            custom_aud = st.text_input(
                "Опишите боли и интересы ЦА",
                "Студенты, хотят копить и получать кэшбэк"
            )

        with st.form("input_module_form", border=False):
            col_n, col_pr = st.columns([1.4, 1])
            with col_n:
                name = st.text_input(
                    "Название продукта",
                    value="Дебетовая карта Центр-инвест"
                )
            with col_pr:
                price = st.text_input(
                    "Цена / Оффер",
                    value="0 ₽ за обслуживание"
                )

            desc = st.text_area(
                "Описание предложения",
                value="Бесплатное обслуживание, повышенный кэшбэк на АЗС и супермаркеты, честный доход на остаток",
                height=72
            )
            adv = st.text_input(
                "Главное преимущество (УТП)",
                value="кэшбэк реальными рублями без скрытых комиссий"
            )

            col_p, col_t = st.columns(2)
            with col_p:
                platform = st.selectbox("Площадка", list(PLATFORM_LIMITS.keys()))
            with col_t:
                tone = st.selectbox("Тональность", list(TONE_MODIFIERS.keys()))

            submit_btn = st.form_submit_button(
                "✨ Сгенерировать 3 варианта",
                use_container_width=True
            )

# ---------------- ОБРАБОТКА ФОРМЫ ----------------
if submit_btn:
    if not name.strip() or not desc.strip():
        st.error("⚠️ Название и описание продукта не могут быть пустыми!")
    else:
        data = {
            "name": name.strip(),
            "desc": desc.strip(),
            "adv": adv.strip(),
            "price": price.strip()
        }
        variants = []
        for i in range(3):
            variants.append({
                "hook": build_part("hooks", audience, data, tone, index=i, custom_aud=custom_aud),
                "body": build_part("bodies", audience, data, tone, index=i, custom_aud=custom_aud),
                "cta": build_part("ctas", audience, data, tone, index=i, custom_aud=custom_aud),
            })
        st.session_state["variants"] = variants
        st.session_state["meta"] = {
            "data": data,
            "audience": audience,
            "custom_aud": custom_aud,
            "platform": platform,
            "tone": tone,
            "time": datetime.datetime.now().strftime("%H:%M:%S")
        }

# ---------------- ПРАВАЯ КОЛОНКА: РЕЗУЛЬТАТ ВКЛАДКАМИ ----------------
with right_col:
    with st.container(border=True):
        st.subheader("📝 Сгенерированные тексты и проверка")

        if "variants" in st.session_state:
            meta = st.session_state["meta"]
            st.caption(
                f"Аудитория: **{meta['audience']}**  |  "
                f"Площадка: **{meta['platform']}**  |  "
                f"Обновлено в {meta['time']}"
            )

            tabs = st.tabs(["✨ Вариант #1", "✨ Вариант #2", "✨ Вариант #3"])

            for idx, tab in enumerate(tabs):
                with tab:
                    v = st.session_state["variants"][idx]
                    full_text = f"{v['hook']}\n\n{v['body']}\n\n{v['cta']}"

                    edited_text = st.text_area(
                        "Текст объявления (можно редактировать вручную):",
                        value=full_text,
                        height=205,
                        key=f"editor_{idx}"
                    )

                    issues = validate_text(edited_text, meta["platform"])
                    limit = PLATFORM_LIMITS[meta["platform"]]
                    st.caption(f"Длина текста: **{len(edited_text)} / {limit}** символов")

                    if not issues:
                        st.success("✓ Текст прошёл проверку: лимит в норме, есть CTA, без запрещённых слов.")
                    else:
                        for issue in issues:
                            st.warning(issue)

                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("🔄 Перегенерировать вариант", key=f"regen_{idx}", use_container_width=True):
                            st.session_state["variants"][idx] = {
                                "hook": build_part("hooks", meta["audience"], meta["data"], meta["tone"], exclude=v["hook"], custom_aud=meta["custom_aud"]),
                                "body": build_part("bodies", meta["audience"], meta["data"], meta["tone"], exclude=v["body"], custom_aud=meta["custom_aud"]),
                                "cta": build_part("ctas", meta["audience"], meta["data"], meta["tone"], exclude=v["cta"], custom_aud=meta["custom_aud"]),
                            }
                            st.rerun()

                    with btn_col2:
                        if any("Запрещённые" in i for i in issues):
                            if st.button("🪄 Исправить стоп-слова", key=f"clean_{idx}", use_container_width=True):
                                cleaned = clean_forbidden(edited_text)
                                parts = cleaned.split("\n\n")
                                if len(parts) >= 3:
                                    st.session_state["variants"][idx] = {
                                        "hook": parts[0],
                                        "body": parts[1],
                                        "cta": "\n\n".join(parts[2:])
                                    }
                                else:
                                    st.session_state["variants"][idx] = {
                                        "hook": cleaned,
                                        "body": "",
                                        "cta": ""
                                    }
                                st.rerun()
        else:
            st.info("👈 Заполните параметры продукта в левой карточке и нажмите **«Сгенерировать 3 варианта»**.")
