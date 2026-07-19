# Chapter 8: Error Handling

> **Learning Objective**: Write robust code that handles unexpected situations.

---

## 8.1 try/except

```python
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Cannot divide by zero!")
```

Catch specific exceptions:
```python
try:
    num = int(input("Enter a number: "))
except ValueError:
    print("That is not a valid number!")
except ZeroDivisionError:
    print("Cannot divide by zero!")
```

---

## 8.2 else and finally

```python
try:
    file = open("data.txt")
except FileNotFoundError:
    print("File not found!")
else:
    content = file.read()  # Runs only if no exception
finally:
    print("Cleanup complete")  # Always runs
```

---

## 8.3 Raising Exceptions

```python
def validate_age(age):
    if age < 0:
        raise ValueError("Age cannot be negative")
    return age

# Custom exceptions
class InsufficientFundsError(Exception):
    pass
```

---

## 8.4 Common Exception Types

ValueError, TypeError, KeyError, IndexError, FileNotFoundError, ZeroDivisionError, AttributeError

---

## Practice Exercises

1. Write safe_divide(a, b) that returns the result or None on failure.

2. Create custom InvalidEmailError and a validator that raises it.

3. Write a file reader handling FileNotFoundError and PermissionError.

4. Implement a retry decorator that catches exceptions and retries up to 3 times.

---

## Key Takeaways

- try/except catches expected errors
- Catch specific exceptions, never bare except
- finally always runs (use for cleanup)
- Raise custom exceptions for domain-specific errors
