# Chapter 3: Functions

> **Learning Objective**: Write reusable, modular code with functions.

---

## 3.1 Defining Functions

```python
def greet(name):
    """Return a greeting for the given name."""
    return f"Hello, {name}!"

print(greet("Alice"))  # Hello, Alice!
```

---

## 3.2 Parameters and Arguments

### Positional and Keyword
```python
def add(a, b):
    return a + b

add(3, 5)       # 8
add(b=5, a=3)   # 8 - order doesn't matter
```

### Default Values
```python
def power(base, exponent=2):
    return base ** exponent

power(3)    # 9  (3 squared)
power(3, 3) # 27 (3 cubed)
```

### Variable Arguments
```python
def sum_all(*args):
    return sum(args)

sum_all(1, 2, 3, 4)  # 10

def describe(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")
```

---

## 3.3 Scope

```python
x = 10       # Global

def func():
    y = 5    # Local
    print(x) # Can read global
```

---

## 3.4 Lambda Functions

```python
square = lambda x: x ** 2
students.sort(key=lambda s: s[1])  # Sort by score
```

---

## Practice Exercises

1. Write `is_palindrome(s)` that returns True if the string reads the same forwards and backwards.

2. Write `fibonacci(n)` that returns the nth Fibonacci number.

3. Write `apply_to_all(func, items)` that applies a function to every item in a list.

4. Create a lambda that takes a string and returns its length. Sort a list of words by length.

---

## Key Takeaways

- Functions encapsulate logic with parameters and return values
- Default parameters make functions more flexible
- *args and **kwargs handle variable argument counts
- Lambdas are single-expression anonymous functions
