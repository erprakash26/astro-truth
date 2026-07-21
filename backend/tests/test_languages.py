from app.languages import LANGUAGES, search_languages


def test_dataset_has_around_184_languages():
    assert 180 <= len(LANGUAGES) <= 190


def test_dataset_codes_are_unique():
    codes = [lang.code for lang in LANGUAGES]
    assert len(codes) == len(set(codes))


def test_dataset_includes_english_and_nepali():
    names = {lang.name for lang in LANGUAGES}
    assert "English" in names
    assert "Nepali" in names


def test_search_finds_spanish():
    results = search_languages("span")
    assert any(lang.name == "Spanish" for lang in results)


def test_search_is_case_insensitive():
    assert search_languages("SPANISH") == search_languages("spanish")


def test_search_empty_query_returns_results():
    assert len(search_languages("")) > 0


def test_search_unknown_query_returns_empty():
    assert search_languages("zzznotalanguage") == []
