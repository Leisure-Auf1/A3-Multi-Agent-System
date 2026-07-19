# Chapter 7: File I/O

> **Learning Objective**: Read from and write to files for persistent data.

---

## 7.1 Reading Files

```python
with open("data.txt", "r") as f:
    content = f.read()

with open("data.txt", "r") as f:
    for line in f:
        print(line.strip())
```

---

## 7.2 Writing Files

```python
with open("output.txt", "w") as f:
    f.write("Hello, World!\n")
```

Modes: "r" read, "w" write (overwrite), "a" append, "b" binary

---

## 7.3 CSV Files

```python
import csv

with open("data.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row["name"], row["age"])
```

---

## 7.4 JSON Files

```python
import json

data = {"name": "Alice", "scores": [85, 92]}
with open("data.json", "w") as f:
    json.dump(data, f, indent=2)

with open("data.json", "r") as f:
    loaded = json.load(f)
```

---

## 7.5 pathlib

```python
from pathlib import Path

Path("data").mkdir(exist_ok=True)
(Path("data") / "output.txt").write_text("Hello!")
```

---

## Practice Exercises

1. Read a text file, count word frequencies, write top 10 words to a new file.

2. Read a CSV of student grades and compute the class average.

3. Convert a dict to JSON, save it, load it back, verify identity.

4. Use pathlib to create a directory tree and write files.

---

## Key Takeaways

- Always use with open() for automatic file cleanup
- csv.DictReader/DictWriter for structured CSV handling
- json.dump/load for structured data interchange
- pathlib.Path for modern, cross-platform path operations
