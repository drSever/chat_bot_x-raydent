import json

from training.build_dataset import build, question_variants


def test_question_variants_change_wording():
    variants = question_variants("Как загрузить снимок?")
    assert len(variants) == 3
    assert len(set(variants)) == 3
    assert variants[0] == "Как загрузить снимок?"
    assert variants[2].startswith("Каким образом")


def test_training_dataset_contains_paraphrases_and_distractors(tmp_path):
    train_count, validation_count = build(tmp_path)
    assert (train_count, validation_count) == (337, 38)

    rows = [
        json.loads(line)
        for path in (tmp_path / "train.jsonl", tmp_path / "validation.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    faq_rows = [row for row in rows if row["id"].startswith("faq-")]
    assert len(faq_rows) == 119 * 3
    assert any("Подскажите, пожалуйста" in row["messages"][1]["content"] for row in faq_rows)
    assert any(row["messages"][1]["content"].count("FAQ #") == 3 for row in faq_rows)
