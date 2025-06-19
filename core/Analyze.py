def analyze_conflict(text: str) -> str:
    text = text.lower()
    if "обманул" in text or "обман" in text:
        return "Похоже, человек действительно виноват. ❌"
    elif "без причины" in text or "неправильно" in text:
        return "Есть подозрение, что поступок был несправедлив. 🤔"
    elif "оскорбил" in text or "мат" in text:
        return "Оскорбления недопустимы. Вероятно, виновен. 🚫"
    else:
        return "Недостаточно информации для вынесения вердикта. 🕵️"
