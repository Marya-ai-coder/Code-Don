import random
import re
import datetime
import streamlit as st

# ==========================================
# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
# ==========================================
st.set_page_config(
    page_title="ИИ-Копирайтер | Центр-инвест",
    page_icon="🚀",
    layout="wide"
)

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

CTA_MARKERS = ["перейд", "жми", "клик", "закаж", "оформ", "забир", "оставьте", "запрос", "узнай", "попроб", "ссылк"]

# ==========================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
def build_part(part_type, audience, data, tone, index=None, exclude=None):
    preset = AUDIENCE_PRESETS.get(audience, AUDIENCE_PRESETS["Молодёжь (18–25)"])
    templates = preset[part_type]
    
    if index is not None:
        template = templates[index % len(templates)]
    else:
        candidates = []
        for t in templates:
            text = t.format(**data)
            if part_type == "hooks":
                text = TONE_MODIFIERS[tone][0] + text
            elif part_type == "bodies":
                text = text.rstrip(".") + TONE_MODIFIERS[tone][1]
            if text != exclude:
                candidates.append(text)
        return random.choice(candidates) if candidates else exclude

    text = template.format(**data)
    if part_type == "hooks":
        text = TONE_MODIFIERS[tone][0] + text
    elif part_type == "bodies":
        text = text.rstrip(".") + TONE_MODIFIERS[tone][1]
    return text

def validate_text(text, platform):
    issues = []
    limit = PLATFORM_LIMITS[platform]
    if len(text) > limit:
        issues.append(f"⚠️ Превышен лимит площадки ({len(text)}/{limit} симв.)")
    
    found_forbidden = [w for w in FORBIDDEN_WORDS if re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE)]
    if found_forbidden:
        issues.append(f"🚫 Запрещённые/штампованные слова по ФЗ «О рекламе»: {', '.join(found_forbidden)}")
    
    if not any(marker in text.lower() for marker in CTA_MARKERS):
        issues.append("⚠️ Не найден явный призыв к действию (CTA)")
    return issues

def clean_forbidden(text):
    for bad, good in FORBIDDEN_WORDS.items():
        text = re.sub(rf"\b{re.escape(bad)}\b", good, text, flags=re.IGNORECASE)
    return text

# ==========================================
# 4. ИНТЕРФЕЙС ВВОДА (STREAMLIT FORM)
# ==========================================
st.title("🚀 ИИ-помощник для генерации рекламы (Центр-инвест)")
st.caption("Модуль ввода: форма ввода параметров продукта, адаптация под аудиторию и генерация вариантов.")

# Выносим форму ввода в боковую панель (sidebar) или основной блок
with st.sidebar:
    st.header("📋 Форма ввода параметров")
    
    with st.form("input_module_form"):
        st.subheader("1. О продукте / услуге")
        name = st.text_input(
            label="Название продукта / услуги",
            value="Дебетовая карта Центр-инвест",
            help="Укажите бренд или название предложения"
        )
        desc = st.text_area(
            label="Описание предложения",
            value="Бесплатное обслуживание, повышенный кэшбэк на АЗС и супермаркеты, честный доход на остаток",
            height=100,
            help="Ключевые свойства и характеристики предложения"
        )
        adv = st.text_input(
            label="Главное преимущество (УТП)",
            value="кэшбэк реальными рублями без скрытых комиссий",
            help="Чем предложение выгодно отличается от конкурентов"
        )
        price = st.text_input(
            label="Цена / Оффер",
            value="0 ₽ за обслуживание",
            help="Стоимость, акция или тариф"
        )

        st.subheader("2. Настройки рекламы")
        audience = st.selectbox(
            label="Целевая аудитория",
            options=list(AUDIENCE_PRESETS.keys()) + ["Своя аудитория"]
        )
        custom_aud = ""
        if audience == "Своя аудитория":
            custom_aud = st.text_input("Опишите боли и интересы ЦА", "Студенты, хотят копить и получать кэшбэк")

        platform = st.selectbox("Площадка размещения", list(PLATFORM_LIMITS.keys()))
        tone = st.selectbox("Тон общения", list(TONE_MODIFIERS.keys()))

        # Кнопка отправки формы
        submit_btn = st.form_submit_button("✨ Сгенерировать 3 варианта", use_container_width=True)

# Обработка формы
if submit_btn:
    if not name.strip() or not desc.strip():
        st.error("⚠️ Название и описание продукта не могут быть пустыми!")
    else:
        st.session_state["saved_data"] = {
            "name": name.strip(),
            "desc": desc.strip(),
            "adv": adv.strip() or "высокая надежность и выгода",
            "price": price.strip() or "выгодных условиях",
            "audience": audience,
            "custom_aud": custom_aud,
            "platform": platform,
            "tone": tone
        }
        
        # Генерация 3 вариантов
        st.session_state.variants = []
        h_idx = random.sample(range(3), 3)
        b_idx = random.sample(range(3), 3)
        c_idx = random.sample(range(3), 3)
        data = st.session_state["saved_data"]
        
        for i in range(3):
            st.session_state.variants.append({
                "hooks": build_part("hooks", data["audience"], data, data["tone"], index=h_idx[i]),
                "bodies": build_part("bodies", data["audience"], data, data["tone"], index=b_idx[i]),
                "ctas": build_part("ctas", data["audience"], data, data["tone"], index=c_idx[i])
            })
        st.success("✅ 3 рекламных варианта успешно сформированы!")

# ==========================================
# 5. ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ И КОПИРОВАНИЕ
# ==========================================
has_variants = "variants" in st.session_state and len(st.session_state.variants) > 0

# Кнопка глобальной перегенерации (строго вне формы!)
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.subheader("📢 Сгенерированные рекламные материалы")
with col_head2:
    global_regen = st.button(
        "🔄 Перегенерировать все",
        disabled=not has_variants,
        use_container_width=True,
        help="Запустить повторную генерацию всех 3 вариантов"
    )

if global_regen and "saved_data" in st.session_state:
    data = st.session_state["saved_data"]
    st.session_state.variants = []
    h_idx = random.sample(range(3), 3)
    b_idx = random.sample(range(3), 3)
    c_idx = random.sample(range(3), 3)
    for i in range(3):
        st.session_state.variants.append({
            "hooks": build_part("hooks", data["audience"], data, data["tone"], index=h_idx[i]),
            "bodies": build_part("bodies", data["audience"], data, data["tone"], index=b_idx[i]),
            "ctas": build_part("ctas", data["audience"], data, data["tone"], index=c_idx[i])
        })
    st.rerun()

if not has_variants:
    st.info("👈 Заполните параметры продукта в панели слева и нажмите кнопку «✨ Сгенерировать 3 варианта».")
else:
    cur_data = st.session_state.get("saved_data", {})
    cur_platform = cur_data.get("platform", "Соцсети (VK / TG)")
    cur_aud = cur_data.get("audience", "Молодёжь (18–25)")
    cur_tone = cur_data.get("tone", "Дружелюбный 😊")

    if cur_data.get("custom_aud"):
        st.caption(f"🎯 Учтён сегмент ЦА: **{cur_data['custom_aud']}**")

    # Отображение 3 колонок с вариантами
    cols = st.columns(3)
    for i, col in enumerate(cols):
        v = st.session_state.variants[i]
        full_text = f"{v['hooks']}\n\n{v['bodies']}\n\n{v['ctas']}"
        issues = validate_text(full_text, cur_platform)

        with col:
            st.markdown(f"### Вариант #{i+1}")
            st.caption("Нажмите иконку в углу блока для быстрого копирования:")
            # Блок st.code с копированием в один клик
            st.code(full_text, language=None)

            # Валидация по ФЗ «О рекламе»
            if not issues:
                st.success("✅ Валидация пройдена (лимиты и стоп-слова в норме)")
            else:
                for iss in issues:
                    st.warning(iss)
                if any("Запрещённые" in iss for iss in issues):
                    if st.button("🧹 Исправить стоп-слова", key=f"fix_{i}", use_container_width=True):
                        for part in ["hooks", "bodies", "ctas"]:
                            st.session_state.variants[i][part] = clean_forbidden(v[part])
                        st.rerun()

            # Пофрагментная перегенерация
            st.caption("Перегенерировать фрагмент:")
            c1, c2, c3 = st.columns(3)
            if c1.button("Заголовок", key=f"h_{i}", use_container_width=True):
                st.session_state.variants[i]["hooks"] = build_part("hooks", cur_aud, cur_data, cur_tone, exclude=v["hooks"])
                st.rerun()
            if c2.button("Основу", key=f"b_{i}", use_container_width=True):
                st.session_state.variants[i]["bodies"] = build_part("bodies", cur_aud, cur_data, cur_tone, exclude=v["bodies"])
                st.rerun()
            if c3.button("CTA", key=f"c_{i}", use_container_width=True):
                st.session_state.variants[i]["ctas"] = build_part("ctas", cur_aud, cur_data, cur_tone, exclude=v["ctas"])
                st.rerun()
