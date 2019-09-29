from typing import Optional, Callable


def get_int_or_zero(value: Optional[int]) -> int:
    return value or 0


def get_str_or_empty(value: Optional[str]) -> str:
    return value or ""


def lazy_property(method: Callable) -> Callable:
    lazy_name = f"__lazy_{method.__name__}"

    @property
    def lazy_property_wrapper(self) -> property:
        if not hasattr(self, lazy_name):
            setattr(self, lazy_name, method(self))
        return getattr(self, lazy_name)

    return lazy_property_wrapper
