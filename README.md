Python специализатор кода
====================

Как использовать:
```python
def h(a, b):
    c = 11
    a = a + c
    b = b + c
    print(a)
    print(b)
    return a * 2 + b * 3

h2 = specialize(5, UnknownValue())(h)
assert h2(7) == h(5, 7)
```
или как декоратор:
```python
def h_source(a, b):
    c = 11
    a = a + c
    b = b + c
    print(a)
    print(b)
    return a * 2 + b * 3

@specialize(UnknownValue(), 7)
def h_spec(a, b):
    c = 11
    a = a + c
    b = b + c
    print(a)
    print(b)
    return a * 2 + b * 3

assert h_spec(5) == h_source(5, 7)
```

Какие операции поддерживаются
===
Их пока немного:
* rot_two
* binary_multiply
* binary_add
* return_value
* load_const
* load_global
* load_fast
* call_function
* store_fast


В последствии, возможно, количество будет пополняться.

Проект сделан как проверка концепции, буду ли я его развивать дальше, чтобы получилось что-то вроде такого https://www.slideshare.net/TechTalksNSU/tech-talks-nsu-60906372 , но тема крутая