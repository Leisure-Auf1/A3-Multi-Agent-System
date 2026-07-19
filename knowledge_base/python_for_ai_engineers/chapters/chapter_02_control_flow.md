# Chapter 2: Control Flow

> **Learning Objective**: Master conditional logic and iteration to control program execution.

---

## 2.1 Conditional Statements

### if / elif / else
```python
score = 85

if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
else:
    grade = "F"
```

### Comparison Operators
==, !=, <, >, <=, >=

### Logical Operators
and, or, not

---

## 2.2 Loops

### for Loop
```python
for i in range(5):
    print(i)

fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(f"I like {fruit}")
```

### while Loop
```python
count = 0
while count < 5:
    print(count)
    count += 1
```

### break / continue
```python
for i in range(10):
    if i == 5:
        break
    print(i)  # Prints 0-4
```

---

## 2.3 List Comprehensions

```python
squares = [i**2 for i in range(10)]
evens = [i for i in range(20) if i % 2 == 0]
```

---

## Practice Exercises

1. Write FizzBuzz: print 1-100. Multiples of 3 -> "Fizz", 5 -> "Buzz", both -> "FizzBuzz".

2. Sum all numbers from 1 to 100 using a for loop.

3. Use a while loop that asks for input until the user types "quit".

4. Create a list comprehension generating squares of even numbers from 0 to 20.

---

## Key Takeaways

- if/elif/else for branching logic
- for iterates over sequences; while repeats while condition holds
- break exits a loop; continue skips to next iteration
- List comprehensions are concise, Pythonic, and often faster
