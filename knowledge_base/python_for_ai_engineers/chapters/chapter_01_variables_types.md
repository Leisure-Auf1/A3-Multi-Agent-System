# Chapter 1: Variables and Data Types

> **Learning Objective**: Master Python's fundamental data types and variable assignment mechanisms.

---

## 1.1 Variables in Python

Python variables are dynamically typed — you don't declare types, Python infers them at runtime.

### Variable Assignment
```python
name = "Alice"           # str
age = 25                 # int
height = 1.75            # float
is_student = True        # bool
```

### Naming Conventions
- Use `snake_case` for variables: `user_name`, `total_count`
- Names are case-sensitive: `age` and `Age` are different
- Cannot start with a digit: `1st_place` is invalid

### Key Insight
> Python variables are references to objects, not containers. When you write `x = 5`, Python creates an integer object and binds the name `x` to it.

---

## 1.2 Primitive Data Types

### Integers (`int`)
```python
x = 42
y = -10
big = 1_000_000     # Underscores for readability
```

### Floating Point (`float`)
```python
pi = 3.14159
scientific = 1.5e-3  # 0.0015
```

### Strings (`str`)
```python
single = 'Hello'
double = "World"
multi = """This spans
multiple lines"""
```

### Booleans (`bool`)
```python
is_valid = True
is_empty = False
```

### NoneType
```python
result = None    # Represents absence of value
```

---

## 1.3 Type Checking and Conversion

```python
# Check type
print(type(42))        # <class 'int'>
print(type("hello"))   # <class 'str'>

# Type conversion
int("42")              # 42
str(3.14)              # "3.14"
float("3.14")          # 3.14
bool(1)                # True
bool(0)                # False
```

### Common Pitfalls
- `int("3.14")` raises ValueError — convert to float first
- `bool("False")` is `True` — any non-empty string is truthy

---

## 1.4 String Operations

```python
# Concatenation
greeting = "Hello" + " " + "World"

# Repetition
line = "-" * 40

# f-strings (Python 3.6+)
name = "Alice"
print(f"Hello, {name}!")  # Hello, Alice!

# String methods
"  hello  ".strip()        # "hello"
"HELLO".lower()            # "hello"
"hello world".title()      # "Hello World"
```

---

## Practice Exercises

1. Create variables for your name, age, and whether you know Python. Print them in a sentence using f-strings.

2. Convert the string `"100"` to an integer and multiply by 2. What is the result?

3. What does `type(3.0)` return? What about `type("3")`?

4. Write code that checks if a string `s = "Python"` starts with "Py" and ends with "on".

---

## Key Takeaways

- Python has 4 primitive types: int, float, str, bool
- Variables are dynamically typed references to objects
- Use `type()` to check types and constructor functions to convert them
- f-strings are the modern way to format strings with embedded expressions
