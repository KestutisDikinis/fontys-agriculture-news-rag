from app.sources import get_sources


def test_source_ids_are_unique():
    sources = get_sources()
    ids = [s.id for s in sources]
    assert len(ids) == len(set(ids))


def test_sources_have_required_fields():
    for source in get_sources():
        assert source.id
        assert source.name
        assert source.url.startswith("http")
        assert source.region
