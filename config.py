# Настройки нейронки DeepSeek.
# Ключ НЕ хранится в файле: задайте переменную окружения DEEPSEEK_API_KEY.
# Пока ключ пустой, приложение работает на шаблонах и не делает запросы в API.

import os

AI_API_KEY  = os.getenv("DEEPSEEK_API_KEY", "")
AI_BASE_URL = "https://api.deepseek.com/v1"
AI_MODEL    = "deepseek-chat"
