from app.config import ROOT
from app.faq import parse_faq
from app.retrieval import FaqRetriever


def make_retriever():
    return FaqRetriever(parse_faq(ROOT / "data" / "chatbot-faq-119.md"), "unused", enable_semantic=False)


def test_all_original_questions_are_top_one():
    retriever = make_retriever()
    for entry in retriever.entries:
        assert retriever.search(entry.question, top_k=1)[0].entry.id == entry.id


def test_common_rephrasings_find_expected_faq():
    retriever = make_retriever()
    cases = {
        "Расскажите, что представляет собой X-RayDent": 1,
        "Подскажите как мне загрузить ОПТГ": 20,
        "ПДФ файл с отчетом не открывается": 105,
        "Я забыл свой пароль": 106,
        "С какими браузерами работает сайт": 110,
    }
    for query, expected in cases.items():
        assert expected in [hit.entry.id for hit in retriever.search(query, top_k=3)]
