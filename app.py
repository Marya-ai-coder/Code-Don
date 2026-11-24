import streamlit as st
import datetime

# --- 1. Настройка страницы и заголовок ---
st.set_page_config(
    page_title="Модуль ввода | Генератор контента",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Модуль ввода (Генератор контента)")
st.caption("Заполните форму ниже, чтобы отправить запрос на генерацию контента. Вы можете скопировать результат или перегенерировать его.")

# --- Вспомогательная функция генерации (с поддержкой YandexGPT / OpenAI и Demo-режима) ---
def generate_response(prompt: str, mode: str) -> str:
    """
    Функция генерации контента:
    - При наличии API-ключей в st.secrets использует внешние LLM (YandexGPT или OpenAI).
    - При отсутствии ключей работает в автономном демонстрационном режиме.
    """
    # 1. Попытка использовать YandexGPT, если ключи заданы
    if "YANDEX_OAUTH_TOKEN" in st.secrets and "YANDEX_FOLDER_ID" in st.secrets:
        try:
            from yandex_gpt import YandexGPT, Messages, SystemMessage, UserMessage
            client = YandexGPT(st.secrets["YANDEX_OAUTH_TOKEN"], st.secrets["YANDEX_FOLDER_ID"])
            messages = Messages(
                SystemMessage(f"Ты — полезный ассистент. Твой стиль: {mode}."),
                UserMessage(f"Запрос: {prompt}. Режим: {mode}")
            )
            response = client.completion(messages)
            return response.alternatives[0].message
        except Exception as e:
            st.warning(f"Ошибка обращения к YandexGPT: {e}. Переключение на локальную генерацию.")

    # 2. Попытка использовать OpenAI, если задан OPENAI_API_KEY
    elif "OPENAI_API_KEY" in st.secrets:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Ты — эксперт-помощник. Стиль ответа: {mode}."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            st.warning(f"Ошибка обращения к OpenAI: {e}. Переключение на локальную генерацию.")

    # 3. Автономный режим генерации (без необходимости внешних ключей)
    now = datetime.datetime.now().strftime("%H:%M:%S")
    mode_templates = {
        "Креативный копирайтер": f"✨ [Креативный режим] ✨\nТема: {prompt}\n\nСвежая идея: Превратите эту тему в яркую захватывающую историю, которая привлекает внимание с первых секунд!\n(Сгенерировано в {now})",
        "Деловой стиль": f"📄 [Официально-деловой ответ]\nПо вопросу: «{prompt}»\n\nСообщаем, что основные тезисы структурированы и готовы для включения в отчет или презентацию.\n(Сгенерировано в {now})",
        "Технический эксперт": f"⚙️ [Технический анализ]\nЗапрос: {prompt}\n\nАрхитектурный подход: модульная реализация с валидацией входных данных и обработкой исключений.\n(Сгенерировано в {now})",
        "Краткий пересказ": f"📌 [Краткая выжимка (TL;DR)]\nСуть запроса: {prompt}.\nКлючевой вывод: задача решается быстро и эффективно.\n(Сгенерировано в {now})"
    }
    return mode_templates.get(mode, f"Ответ на запрос «{prompt}» в режиме [{mode}]. (Время: {now})")

# --- 2. Каркас формы ввода (st.form) ---
with st.form("input_form"):
    st.subheader("Параметры запроса")
    
    # Поле ввода запроса
    user_input = st.text_area(
        label="Введите ваш запрос:",
        placeholder="Например: напиши короткий пост о пользе утренней зарядки...",
        height=120,
        help="Текст запроса для генерации нейросетью"
    )
    
    # Поле выбора роли / режима
    option = st.selectbox(
        label="Выберите режим / роль:",
        options=[
            "Креативный копирайтер",
            "Деловой стиль",
            "Технический эксперт",
            "Краткий пересказ"
        ],
        help="Стиль и формат генерируемого ответа"
    )
    
    # Кнопка отправки формы
    submitted = st.form_submit_button("🚀 Сгенерировать")

# --- 3. Обработка нажатия кнопки формы ---
if submitted:
    if not user_input.strip():
        st.error("⚠️ Поле запроса не может быть пустым! Пожалуйста, введите текст.")
    else:
        try:
            with st.spinner("Генерация ответа..."):
                # Сохраняем исходные параметры для возможной перегенерации
                st.session_state["last_prompt"] = user_input.strip()
                st.session_state["last_option"] = option
                
                # Вызываем генерацию
                result_text = generate_response(user_input.strip(), option)
                st.session_state["result"] = result_text
                st.success("Ответ успешно сгенерирован!")
        except Exception as e:
            st.error(f"❌ Произошла непредвиденная ошибка при обработке: {e}")

# --- 4. Отображение результата и кнопка копирования ---
has_result = "result" in st.session_state and bool(st.session_state["result"])

st.markdown("---")
st.subheader("Результат")

if has_result:
    st.caption("Нажмите иконку копирования в правом верхнем углу блока с текстом, чтобы скопировать ответ в буфер обмена:")
    # st.code с language=None даёт встроенную кнопку копирования в один клик
    st.code(st.session_state["result"], language=None)
else:
    st.caption("Здесь появится результат генерации после отправки формы.")

# --- 5. Кнопка «Перегенерировать» с параметром disabled ---
# Кнопка строго за пределами формы!
col1, col2 = st.columns([1, 3])
with col1:
    regenerate_clicked = st.button(
        "🔄 Перегенерировать",
        disabled=not has_result,
        help="Повторно сгенерировать ответ для последнего введенного запроса"
    )

if regenerate_clicked:
    if "last_prompt" in st.session_state and "last_option" in st.session_state:
        try:
            with st.spinner("Перегенерация ответа..."):
                new_result = generate_response(
                    st.session_state["last_prompt"],
                    st.session_state["last_option"]
                )
                st.session_state["result"] = new_result
                st.rerun()
        except Exception as e:
            st.error(f"❌ Ошибка при перегенерации: {e}")
