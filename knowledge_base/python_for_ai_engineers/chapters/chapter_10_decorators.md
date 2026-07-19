# Chapter 10: Decorators

> **Learning Objective**: Modify function behavior without changing their code.

---

## 10.1 Functions as First-Class Objects

```python
def greet(name):
    return f"Hello, {name}"

say_hello = greet        # Assign to variable
print(say_hello("Bob"))  # Hello, Bob

def apply(func, value):
    return func(value)
```

---

## 10.2 Simple Decorator

```python
def logger(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with {args}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper

@logger
def add(a, b):
    return a + b

add(3, 5)
# Calling add with (3, 5)
# add returned 8
```

@logger is equivalent to: add = logger(add)

---

## 10.3 Decorators with Arguments

```python
def repeat(times):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def say_hello():
    print("Hello!")
```

---

## 10.4 functools.wraps

```python
from functools import wraps

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time()-start:.3f}s")
        return result
    return wrapper
```

---

## Practice Exercises

1. Write @retry(max_attempts=3) that retries on exception.

2. Create @validate_types checking argument types against type hints.

3. Implement @count_calls tracking how many times a function is called.

4. Build @deprecated that prints a warning on use.

---

## Key Takeaways

- Decorators wrap functions: func = decorator(func)
- @decorator syntax is syntactic sugar
- wraps() preserves the original function's metadata
- Decorators with arguments require triple nesting
