from app.config import ROOT
from app.faq import parse_faq


def test_faq_has_119_sequential_entries_and_seven_sections():
    entries = parse_faq(ROOT / "data" / "chatbot-faq-119.md")
    assert len(entries) == 119
    assert [entry.id for entry in entries] == list(range(1, 120))
    assert len({entry.section for entry in entries}) == 7
    assert entries[0].question == "Что такое X-RayDent?"
    assert "не ставит диагноз" in entries[-1].answer


def test_categories_and_medical_flags_are_added():
    entries = parse_faq(ROOT / "data" / "chatbot-faq-119.md")
    assert any(entry.category == "clinical" for entry in entries)
    assert any(entry.medical_escalation for entry in entries)
