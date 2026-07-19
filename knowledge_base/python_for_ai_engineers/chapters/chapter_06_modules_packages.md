# Chapter 6: Modules and Packages

> **Learning Objective**: Organize Python code into reusable modules and packages.

---

## 6.1 Importing Modules

```python
import math
print(math.sqrt(16))    # 4.0

from math import sqrt, pi
print(sqrt(25))         # 5.0

import numpy as np
arr = np.array([1, 2, 3])
```

Key stdlib modules: math, random, datetime, os, json, re, collections

---

## 6.2 Creating Modules

Any .py file is a module:
```python
# my_utils.py
def double(x):
    return x * 2

# In another file:
from my_utils import double
```

---

## 6.3 Packages

A directory with __init__.py:
```
my_package/
├── __init__.py
├── core.py
└── utils.py
```

```python
from my_package.core import main_function
```

---

## 6.4 if __name__ == "__main__"

```python
def main():
    print("Running as script")

if __name__ == "__main__":
    main()
```

---

## Practice Exercises

1. Create a calculator.py module with add, subtract, multiply, divide functions.

2. Create a package structure: models.py, views.py, utils.py.

3. Use random + statistics modules: generate 100 numbers, compute mean/median/mode.

4. Write a script with if __name__ == "__main__" guard.

---

## Key Takeaways

- import module or from module import name
- Packages are directories with __init__.py
- Use absolute imports for clarity
- __name__ guard prevents code from running on import
