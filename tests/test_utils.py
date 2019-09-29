import pytest

from doc_generator.utils import get_int_or_zero, get_str_or_empty, lazy_property


def test_get_int_or_zero():
    assert get_int_or_zero(1) == 1
    assert get_int_or_zero(None) == 0
    assert get_int_or_zero(-1) == -1


def test_get_str_or_empty():
    assert get_str_or_empty("test") == "test"
    assert get_str_or_empty(None) == ""
    assert get_str_or_empty("") == ""


@pytest.fixture()
def klass():
    class Klass:
        _values = (i for i in range(1000))

        @lazy_property
        def lazy_something(self):
            return next(self._values)

        @property
        def something(self):
            return next(self._values)

    return Klass


def test_lazy_property(klass):
    objekt = klass()

    assert objekt.something != objekt.something
    assert objekt.lazy_something == objekt.lazy_something
