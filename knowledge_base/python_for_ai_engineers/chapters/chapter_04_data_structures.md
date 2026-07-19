# Chapter 4: Data Structures

> **Learning Objective**: Master Python's built-in data structures.

---

## 4.1 Lists (ordered, mutable)

```python
nums = [1, 2, 3, 4, 5]
nums.append(6)       # [1, 2, 3, 4, 5, 6]
nums.pop()           # removes 6
nums[1:3]            # [2, 3] (slice)
```

Methods: append, extend, insert, remove, pop, sort, reverse, index, count

---

## 4.2 Tuples (ordered, immutable)

```python
point = (3, 4)
x, y = point         # Unpacking
single = (42,)       # Single-element tuple needs comma
```

---

## 4.3 Dictionaries (key-value pairs)

```python
student = {"name": "Alice", "age": 25}
student["email"] = "alice@example.com"
student.get("phone", "N/A")  # Safe access with default

for key, value in student.items():
    print(f"{key}: {value}")
```

---

## 4.4 Sets (unique, unordered)

```python
primes = {2, 3, 5, 7, 11}
primes & {2, 4, 6}     # {2} - intersection
primes | {4, 6}        # {2,3,4,5,6,7,11} - union
primes - {2, 3}        # {5,7,11} - difference
```

---

## Practice Exercises

1. Create a list of 10 numbers. Sort it, reverse it, compute the sum.

2. Write a function that takes a list and returns (min, max, average) as a tuple.

3. Build a dictionary that maps each word in a sentence to its frequency count.

4. Find common elements between two lists using set intersection.

---

## Key Takeaways

- Lists: ordered, mutable — general-purpose collections
- Tuples: ordered, immutable — fixed data, dict keys
- Dicts: key-value — O(1) lookups
- Sets: unique, unordered — membership tests, deduplication
