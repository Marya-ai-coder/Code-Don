# -*- coding: utf-8 -*-

FORBIDDEN_PHRASES = [
    # Абсолютные рекламные заявления
    "самый лучший",
    "самая лучшая",
    "самое лучшее",
    "самые лучшие",
    "лучший на рынке",
    "лучшая на рынке",
    "лучшее на рынке",
    "номер один",
    "номер 1",
    "№1",

    # Гарантии результата
    "гарантированный результат",
    "гарантированным результатом",
    "гарантированный успех",
    "гарантированным успехом",
    "гарантированный доход",
    "гарантированным доходом",
    "гарантированный заработок",
    "гарантированным заработком",
    "гарантирует результат",
    "гарантирует успех",
    "гарантирует доход",
    "гарантирует заработок",
    "гарантируем результат",
    "гарантируем успех",
    "гарантируем доход",
    "гарантируем заработок",
    "гарантированно получите",
    "результат гарантирован",
    "успех гарантирован",
    "доход гарантирован",

    # Нереалистичные обещания
    "мгновенный результат",
    "результат за один день",
    "результат за неделю",
    "быстрый успех",
    "легкий заработок",
    "лёгкий заработок",
    "заработок без вложений",
    "доход без вложений",
    "без риска",
    "без усилий",
    "навсегда изменит вашу жизнь",
]

REVIEW_PHRASES = [
    # Спорные фразы не блокируют текст автоматически
    "только сегодня",
    "успейте купить",
    "успейте заказать",
    "последний шанс",
    "нельзя упустить",
    "поторопитесь",
]

CALL_TO_ACTIONS = [
    "купите",
    "закажите",
    "запишитесь",
    "оставьте заявку",
    "узнайте подробнее",
    "попробуйте",
    "выберите",
    "скачайте",
    "перейдите",
    "свяжитесь с нами",
    "напишите нам",
    "позвоните",
    "начните",
    "закажи",
    "заказать",
    "перейди",
    "перейти",
    "переходи",
    "оставь",
    "купи",
    "узнай",
    "узнать",
    "подпишитесь",
    "подпишись",
    "жми",
    "нажмите",
    "попробуй",
    "звони",
    "звоните",
    "оформи",
    "оформите",
    "получи",
    "получите",
    "добавьте",
    "выбирай",
    "забирай",
    "напиши",
    "ответьте",
]

DEFAULT_MAX_ATTEMPTS = 3


def validate_text(text, max_length=200, attempt=1, max_attempts=DEFAULT_MAX_ATTEMPTS):
    if text is None:
        text = ""

    text = str(text).strip()
    lower_text = text.lower()
    text_length = len(text)

    errors = []
    warnings = []
    found_forbidden_phrases = []
    found_review_phrases = []

    if not text:
        errors.append("Рекламный текст пустой.")

    for phrase in FORBIDDEN_PHRASES:
        if phrase in lower_text:
            found_forbidden_phrases.append(phrase)
            errors.append("Найдена запрещённая формулировка: " + phrase)

    for phrase in REVIEW_PHRASES:
        if phrase in lower_text:
            found_review_phrases.append(phrase)
            warnings.append("Найдена спорная фраза: " + phrase)

    if text_length > max_length:
        errors.append(
            f"Текст слишком длинный: {text_length} символов из {max_length}."
        )

    if not any(call_to_action in lower_text for call_to_action in CALL_TO_ACTIONS):
        errors.append("Не найден призыв к действию.")

    is_valid = not errors

    return {
        "is_valid": is_valid,
        "can_show": is_valid,
        "can_rewrite": not is_valid and attempt < max_attempts,
        "errors": errors,
        "warnings": warnings,
        "forbidden_phrases": found_forbidden_phrases,
        "review_phrases": found_review_phrases,
        "text_length": text_length,
        "max_length": max_length,
        "attempt": attempt,
        "max_attempts": max_attempts,
    }


def build_rewrite_request(
    original_text,
    validation_result,
    attempt_number,
    max_attempts=DEFAULT_MAX_ATTEMPTS,
):
    errors = validation_result.get("errors", [])
    max_length = validation_result.get("max_length", 200)

    instructions = [
        "Переделай рекламный текст.",
        "Сохрани основной смысл и информацию о продукте.",
        "Сохрани целевую аудиторию, площадку, тональность и преимущества.",
        "Сохрани или добавь понятный призыв к действию.",
        "Удали запрещённые формулировки.",
        f"Длина нового текста должна быть не больше {max_length} символов.",
        "Верни только готовый рекламный текст без объяснений.",
    ]

    if errors:
        instructions.append("Причины переделки: " + "; ".join(errors))

    instructions.append(
        f"Это попытка {attempt_number} из {max_attempts}. "
        "Не запускай бесконечную генерацию."
    )

    return (
        "Исходный текст:\n"
        + original_text
        + "\n\nИнструкция:\n- "
        + "\n- ".join(instructions)
    )


def validate_and_rewrite(text, max_length, rewrite_fn, max_attempts=DEFAULT_MAX_ATTEMPTS):
    """Проверяет текст и переделывает его через переданную функцию rewrite_fn.

    rewrite_fn(prompt) -> новый текст. Валидатор сам не знает про API,
    поэтому его можно использовать и с ИИ, и с шаблонами, и в тестах.
    """
    for attempt in range(1, max_attempts + 1):
        result = validate_text(
            text,
            max_length=max_length,
            attempt=attempt,
            max_attempts=max_attempts,
        )

        if not result["errors"]:                  # Серьёзных ошибок нет — готово.
            return text, result, attempt

        if attempt == max_attempts:               # Три попытки закончились.
            break

        prompt = build_rewrite_request(
            text, result, attempt + 1, max_attempts
        )
        text = rewrite_fn(prompt)                 # Переделываем через ИИ.

    return text, result, attempt


def print_result(result):
    print("\nРезультат проверки:")
    print("Текст прошёл проверку." if result["is_valid"] else "Текст не прошёл проверку.")

    for error in result["errors"]:
        print("Ошибка:", error)
    for warning in result["warnings"]:
        print("Предупреждение:", warning)

    print("Длина:", result["text_length"], "из", result["max_length"])
    print("Попытка:", result["attempt"], "из", result["max_attempts"])
    print("Можно показать:", result["can_show"])
    print("Можно переделать автоматически:", result["can_rewrite"])


def main():
    # TODO: заменить input на функцию получения текста из интерфейса или backend.
    text = input("Введите рекламный текст: ")
    result = validate_text(text, max_length=200, attempt=1, max_attempts=3)
    print_result(result)

    if result["can_rewrite"]:
        rewrite_request = build_rewrite_request(
            text,
            result,
            result["attempt"],
            result["max_attempts"],
        )
        print("\nИнструкция для backend/нейронки:")
        print(rewrite_request)

        # TODO: передать rewrite_request в функцию backend/нейронки.
        # TODO: указать имя файла и функции, которые принимают этот запрос.
        # TODO: получить из backend только новый рекламный текст.
        # TODO: передать результат повторно в validate_text.
    elif result["review_phrases"] and not result["errors"]:
        print("\nЕсть спорные фразы. Решение об оставлении или переделке принимает пользователь.")


if __name__ == "__main__":
    main()
