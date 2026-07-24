from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyDecision:
    flag: str
    answer: str
    escalation: str | None


URGENT_PATTERNS = (
    r"трудно\s+(дышать|глотать)", r"не могу\s+(дышать|глотать)",
    r"сильн\w*\s+(от[её]к|кровотеч)", r"кровотеч\w*\s+не\s+останав",
    r"потер\w*\s+сознани", r"травм\w*\s+(лица|челюст)",
    r"резко\s+ухудш", r"очень\s+сильн\w*\s+боль",
)
CLINICAL_PATTERNS = (
    r"постав\w*\s+диагноз", r"что\s+у\s+меня", r"чем\s+леч",
    r"назнач\w*\s+(леч|лекар|антибиот)", r"болит\s+(зуб|десн|челюст)",
    r"можно\s+ли\s+принимать", r"расшифруй\w*.*\b(снимок|рентген|оптг)\b",
    r"какая\s+патолог", r"опасн\w*\s+симптом",
)
INJECTION_PATTERNS = (
    r"игнорир\w*\s+(предыдущ|системн|инструкц)", r"забудь\s+(правила|инструкц)",
    r"покажи\s+(системн|скрыт)\w*\s+(промпт|инструкц)", r"developer\s+message",
    r"system\s+prompt", r"jailbreak",
)
SENSITIVE_PATTERNS = (
    r"\b(?:пароль|пин[- ]?код|код подтверждения)\s*[:=]", r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\b",
    r"\b\d{4}[ -]?\d{6}\b", r"полный\s+(медицинск|паспортн)\w*\s+(документ|данн)",
)


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def route_safety(message: str) -> SafetyDecision | None:
    normalized = " ".join(message.split()).lower()
    if _matches(URGENT_PATTERNS, normalized):
        return SafetyDecision(
            flag="urgent_symptoms",
            answer=("По описанию помощь лучше не откладывать. Обратитесь за срочной медицинской помощью "
                    "или позвоните 112, особенно если трудно дышать или глотать, нарастает отёк либо "
                    "не останавливается кровотечение. Чат не может оценить состояние или поставить диагноз."),
            escalation="urgent_care",
        )
    if _matches(INJECTION_PATTERNS, normalized):
        return SafetyDecision(
            flag="prompt_injection",
            answer="Я не могу отключить правила безопасности или раскрыть служебные инструкции. Задайте вопрос о работе X‑RayDent — постараюсь помочь.",
            escalation=None,
        )
    if _matches(SENSITIVE_PATTERNS, normalized):
        return SafetyDecision(
            flag="sensitive_data",
            answer=("Не отправляйте в чат пароли, коды подтверждения, полные медицинские документы или "
                    "персональные данные. Удалите чувствительные сведения и опишите только шаги и текст ошибки."),
            escalation="support",
        )
    if _matches(CLINICAL_PATTERNS, normalized):
        return SafetyDecision(
            flag="clinical_question",
            answer=("X‑RayDent и этот чат не ставят диагноз и не назначают лечение. По вопросу конкретного "
                    "пациента обратитесь к лечащему врачу: он оценит жалобы, осмотр и все исследования вместе."),
            escalation="doctor",
        )
    return None
