# -*- coding: utf-8 -*-
"""Умная перегенерация одного рекламного текста.

Модуль не импортирует app.py, tkinter или requests: все нужные функции
передаются аргументами. Поэтому его можно тестировать отдельно.
"""

MAX_ATTEMPTS = 3


def build_rewrite_prompt(
    text,
    issues,
    data,
    attempt,
    max_attempts,
    forbidden=None,
    platform_limits=None,
):
    """Составляет понятную инструкцию для модели на основе замечаний проверки."""
    lo, hi = (platform_limits or {}).get(data.get("platform"), (0, 5000))

    lines = [
        "Переделай рекламный текст, чтобы он прошёл проверку.",
        "Сохрани продукт, цену, преимущества, целевую аудиторию, тон и площадку.",
        "Верни только готовый текст без пояснений и без JSON.",
        f"Площадка: {data.get('platform')}. Длина: от {lo} до {hi} символов.",
        f"Это попытка {attempt} из {max_attempts}. Не уходи в бесконечную переделку.",
    ]

    if issues:
        lines.append("Конкретные замечания проверки:")
        lines.extend("- " + str(issue) for issue in issues)

    if forbidden:
        lines.append("Не использовать: " + ", ".join(forbidden))

    return "Текущий текст:\n" + str(text) + "\n\nИнструкция:\n" + "\n".join(lines)


def regenerate_with_validation(
    data,
    current_text,
    *,
    validate_fn,
    rewrite_fn,
    forbidden=None,
    platform_limits=None,
    max_attempts=MAX_ATTEMPTS,
):
    """Проверяет текст и переделывает его, пока проверка не пройдёт.

    validate_fn(text, platform) -> список замечаний.
    rewrite_fn(prompt, data) -> (новый_текст, источник).
    """
    text = "" if current_text is None else str(current_text)
    source = ""
    history = []

    for attempt in range(1, max_attempts + 1):
        issues = validate_fn(text, data["platform"])
        history.append(
            {
                "attempt": attempt,
                "text": text,
                "issues": list(issues),
                "source": source,
            }
        )

        if not issues:
            return {
                "text": text,
                "source": source,
                "issues": [],
                "history": history,
                "ok": True,
                "attempts": attempt,
            }

        if attempt == max_attempts:
            break

        prompt = build_rewrite_prompt(
            text,
            issues,
            data,
            attempt + 1,
            max_attempts,
            forbidden=forbidden,
            platform_limits=platform_limits,
        )
        text, source = rewrite_fn(prompt, data)

    return {
        "text": text,
        "source": source,
        "issues": list(history[-1]["issues"]) if history else [],
        "history": history,
        "ok": False,
        "attempts": len(history),
    }
