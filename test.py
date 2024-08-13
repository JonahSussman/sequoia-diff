from typing import Generic, TypeVar

T = TypeVar("T")


class Fooer(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

    def __hash__(self):
        return 1337


x: Fooer = Fooer(42)
y: Fooer[str] = Fooer("hello")

q = x.value
r = y.value


s = set()
s.add(x)
s.add(y)

print(s)
