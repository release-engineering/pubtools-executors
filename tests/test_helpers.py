import pytest

from pubtools._executors.helpers import run_with_retries


@pytest.fixture
def fix_flaky_func():
    """Provide A flaky function fixture function that fails twice before succeeding."""

    def flaky_func():
        if flaky_func.counter < 2:
            flaky_func.counter += 1
            raise Exception("Flaky function")
        return "Success"

    flaky_func.counter = 0
    yield flaky_func


@pytest.fixture
def fix_broken_func():
    """Provide Broken function fixture which raising exception every time called."""

    def broken_func():
        raise Exception("Flaky function")

    yield broken_func


def test_run_with_retries_recoverable(fix_flaky_func):
    """Test retries on recoverable function."""
    run_with_retries(fix_flaky_func, "flaky func test", tries=3, wait_time_increase=0)


def test_run_with_retries_nonrecoverable(fix_broken_func):
    """Tets retries on non-recoverable function."""
    with pytest.raises(Exception):
        run_with_retries(fix_broken_func, "flaky func test", tries=3, wait_time_increase=0)
