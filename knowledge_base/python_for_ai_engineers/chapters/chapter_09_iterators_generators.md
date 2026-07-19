# Chapter 9: Iterators and Generators

> **Learning Objective**: Lazy evaluation for memory-efficient data processing.

---

## 9.1 The Iterator Protocol

```python
class CountDown:
    def __init__(self, start):
        self.current = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.current < 0:
            raise StopIteration
        value = self.current
        self.current -= 1
        return value

for num in CountDown(3):
    print(num)  # 3, 2, 1, 0
```

---

## 9.2 Generators (yield)

```python
def fibonacci(n):
    """Generate first n Fibonacci numbers."""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

for num in fibonacci(10):
    print(num)  # 0, 1, 1, 2, 3, 5, 8, 13, 21, 34
```

Benefits: memory efficient, lazy evaluation, can represent infinite sequences.

---

## 9.3 Generator Expressions

```python
# List comprehension (eager, all in memory)
squares_list = [x**2 for x in range(1000000)]

# Generator expression (lazy, one at a time)
squares_gen = (x**2 for x in range(1000000))

total = sum(x**2 for x in range(1000000))
```

---

## 9.4 yield from

```python
def chain(*iterables):
    for it in iterables:
        yield from it

for item in chain([1, 2], [3, 4], [5, 6]):
    print(item)  # 1, 2, 3, 4, 5, 6
```

---

## Practice Exercises

1. Write even_numbers(n) that yields the first n even numbers.

2. Create a generator that reads a large CSV file line by line.

3. Implement take(n, iterable) that yields the first n items.

4. Use yield from to flatten a nested list: [[1,2],[3,4],[5]] -> [1,2,3,4,5]

---

## Key Takeaways

- Iterators: __iter__() + __next__() + StopIteration
- Generators use yield for lazy, memory-efficient sequences
- Generator expressions are lazy list comprehensions
- yield from delegates to sub-generators
