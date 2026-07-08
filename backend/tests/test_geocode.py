from app.geocode import CITIES, get_city, search_cities


def test_dataset_has_around_two_hundred_cities():
    assert 150 <= len(CITIES) <= 250


def test_dataset_has_all_77_nepal_districts():
    nepal_cities = [c for c in CITIES if c.country == "Nepal"]
    assert len(nepal_cities) == 77


def test_dataset_ids_are_unique():
    ids = [c.id for c in CITIES]
    assert len(ids) == len(set(ids))


def test_london_reference_city():
    london = get_city("united-kingdom-london")
    assert london is not None
    assert london.lat == 51.5074
    assert london.lon == -0.1278
    assert london.timezone == "Europe/London"


def test_search_finds_kathmandu():
    results = search_cities("kathmandu")
    assert any(c.name == "Kathmandu" for c in results)


def test_search_is_case_insensitive():
    assert search_cities("LONDON") == search_cities("london")


def test_search_empty_query_returns_results():
    assert len(search_cities("")) > 0


def test_search_unknown_query_returns_empty():
    assert search_cities("zzznotacity") == []


def test_get_city_unknown_id_returns_none():
    assert get_city("does-not-exist") is None
