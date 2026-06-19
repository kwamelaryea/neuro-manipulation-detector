from cache import make_key


def test_make_key_is_sha256_hex():
    key = make_key("Buy now!")
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)


def test_make_key_is_deterministic():
    assert make_key("same text") == make_key("same text")


def test_make_key_differs_on_different_text():
    assert make_key("a") != make_key("b")


def test_make_key_normalizes_whitespace():
    # Leading/trailing whitespace must not produce distinct keys.
    assert make_key("  hello  ") == make_key("hello")
