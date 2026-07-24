from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path


QUESTION_RE = re.compile(
    r"(?ms)^(?P<id>\d+)\. \*\*(?P<question>.+?)\*\*\s*\n\s*(?P<answer>.*?)(?=^\d+\. \*\*|^## |\Z)"
)
SECTION_RE = re.compile(r"(?m)^##\s+(?P<title>.+)$")
CLINICAL_TERMS = {
    "диагноз", "лечение", "патолог", "симптом", "болит", "боль", "врач",
    "пациент", "клиничес", "десн", "зуб", "отёк", "отек", "кровотеч",
}


@dataclass(frozen=True)
class FaqEntry:
    id: int
    section: str
    question: str
    answer: str
    category: str
    medical_escalation: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _clean(value: str) -> str:
    value = value.replace("  \n", "\n")
    return re.sub(r"\s+", " ", value).strip()


def _category(section: str) -> str:
    lowered = section.lower()
    if "клиничес" in lowered or "пациент" in lowered:
        return "clinical"
    if "техничес" in lowered or "безопас" in lowered or "поддерж" in lowered:
        return "support"
    if "обработ" in lowered or "отчёт" in lowered or "отчет" in lowered:
        return "report"
    if "клиник" in lowered or "врач" in lowered:
        return "clinic"
    if "загруз" in lowered or "начало" in lowered:
        return "onboarding"
    return "service"


def parse_faq(path: Path) -> list[FaqEntry]:
    text = path.read_text(encoding="utf-8")
    sections = [(match.start(), _clean(match.group("title"))) for match in SECTION_RE.finditer(text)]
    entries: list[FaqEntry] = []
    for match in QUESTION_RE.finditer(text):
        section = next((title for pos, title in reversed(sections) if pos < match.start()), "Без раздела")
        question = _clean(match.group("question"))
        answer = _clean(match.group("answer"))
        haystack = f"{question} {answer}".lower()
        entries.append(
            FaqEntry(
                id=int(match.group("id")),
                section=section,
                question=question,
                answer=answer,
                category=_category(section),
                medical_escalation=any(term in haystack for term in CLINICAL_TERMS),
            )
        )
    if len(entries) != 119:
        raise ValueError(f"Ожидалось 119 FAQ, найдено {len(entries)} в {path}")
    ids = [entry.id for entry in entries]
    if ids != list(range(1, 120)):
        raise ValueError("FAQ должны иметь последовательные номера 1–119")
    return entries
