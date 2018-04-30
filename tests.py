from random import randint

import pytest

from special import specialize, UnknownValue


def h(a, b):
    c = 11
    a = a + c
    b = b + c
    print(a)
    print(b)
    return a * 2 + b * 3


def test_h0():
    h0 = specialize(UnknownValue(), UnknownValue())(h)
    assert h(5, 7) == h0(5, 7)

    for i in range(100):
        a = randint(0, 10000)
        b = randint(0, 10000)
        assert h0(a, b) == h(a, b), f"Test failed on ({a}, {b})"

def test_h1():
    h1 = specialize(UnknownValue(), 7)(h)
    assert h1(5) == h(5, 7)

    for i in range(100):
        a, b = randint(0, 10000), randint(0, 10000)
        h1 = specialize(UnknownValue(), b)(h)
        assert h1(a) == h(a, b)

def test_h2():
    h2 = specialize(5, UnknownValue())(h)
    assert h2(7) == h(5, 7)

    for i in range(100):
        a, b = randint(0, 10000), randint(0, 10000)
        h2 = specialize(a, UnknownValue())(h)
        assert h2(b) == h(a, b)

def test_h3():
    h3 = specialize(5, 7)(h)
    assert h3() == h(5, 7)

    for i in range(100):
        a, b = randint(0, 10000), randint(0, 10000)
        h3 = specialize(a, b)(h)
        assert h3() == h(a, b)



