# Chapter 11: NumPy Basics

> **Learning Objective**: Master NumPy arrays for efficient numerical computing.

---

## 11.1 Why NumPy?

NumPy provides the `ndarray` — a fast, memory-efficient N-dimensional array.
- 10-100x faster than Python lists for numerical ops
- Foundation of Python's data science stack
- Used by Pandas, Scikit-learn, TensorFlow, and PyTorch

---

## 11.2 Creating Arrays

```python
import numpy as np

# From lists
a = np.array([1, 2, 3, 4, 5])

# Pre-filled arrays
np.zeros(5)          # [0. 0. 0. 0. 0.]
np.ones((2, 3))      # 2x3 matrix of ones
np.arange(0, 10, 2)  # [0 2 4 6 8]
np.linspace(0, 1, 5) # [0. 0.25 0.5 0.75 1.]

# Random arrays
np.random.rand(3, 2)       # Uniform [0,1)
np.random.randn(3, 2)      # Standard normal
```

---

## 11.3 Array Operations

```python
a = np.array([1, 2, 3])
b = np.array([4, 5, 6])

a + b         # [5 7 9]  element-wise
a * b         # [4 10 18]
a @ b         # 32  dot product
np.sqrt(a)    # [1. 1.414 1.732]

# Broadcasting
a + 10        # [11 12 13]
```

---

## 11.4 Indexing and Slicing

```python
arr = np.arange(12).reshape(3, 4)
# [[ 0  1  2  3]
#  [ 4  5  6  7]
#  [ 8  9 10 11]]

arr[1, 2]       # 6
arr[:, 1]       # [1 5 9]  all rows, column 1
arr[1:, :2]     # [[4 5] [8 9]]

# Boolean indexing
arr[arr > 5]    # [6 7 8 9 10 11]
```

---

## 11.5 Useful Functions

```python
arr = np.array([1, 2, 3, 4, 5])
arr.sum()       # 15
arr.mean()      # 3.0
arr.std()       # 1.414
arr.min()       # 1
arr.max()       # 5
np.median(arr)  # 3.0
```

---

## Practice Exercises

1. Create a 5x5 identity matrix. Multiply it by a random 5x5 matrix.

2. Generate 1000 random numbers and compute mean, std, and histogram bins.

3. Create a 10x10 grid of values and extract the border elements.

4. Use boolean indexing to find all values > 0.5 in a random array.

---

## Key Takeaways

- ndarray is the core NumPy data structure — fast, memory-efficient
- Vectorized operations eliminate Python loops
- Broadcasting enables operations between arrays of different shapes
- Boolean indexing enables powerful filtering
