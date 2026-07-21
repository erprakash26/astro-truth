import pytest

from app.main import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    # Every rate-limited endpoint shares one in-memory Limiter (main.py),
    # which persists across the whole pytest session. Without this, tests
    # that call a limited endpoint more than RATE_LIMIT times in aggregate
    # -- across a single file or across files, since TestClient requests
    # all share the same key_func(get_remote_address) value -- start
    # tripping 429s that have nothing to do with what each test is
    # actually checking. Reset before every test for a clean slate; tests
    # that specifically exercise the limit (test_rate_limit.py) still send
    # their own burst of requests within the test body, so this doesn't
    # interfere with that.
    limiter.reset()
