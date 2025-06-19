def analyze_conflict(text: str) -> str:
    # Простейший анализ — можно потом улучшить (нейросети, ключевые слова и т.п.)
    text_lower = text.lower()
    
    if "обманул" in text_lower or "обман" in text_lower:
        return "Похоже, человек действительно виноват. ❌"
    elif "без причины" in text_lower or "неправильно" in text_lower:
        return "Есть подозрение, что поступок был несправедлив. 🤔"
    elif "оскорбил" in text_lower or "мат" in text_lower:
        return "Оскорбления недопустимы. Вероятно, виновен. 🚫"
    else:
        return "Недостаточно информации для вынесения вердикта. 🕵️"
