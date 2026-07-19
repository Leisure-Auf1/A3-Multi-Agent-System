# Chapter 12: Pandas Basics

> **Learning Objective**: Manipulate tabular data with DataFrames and Series.

---

## 12.1 Core Data Structures

```python
import pandas as pd

# Series (1D labeled array)
s = pd.Series([10, 20, 30], index=['a', 'b', 'c'])

# DataFrame (2D labeled table)
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'score': [85, 92, 78]
})
```

---

## 12.2 Reading and Writing Data

```python
df = pd.read_csv('data.csv')
df = pd.read_excel('data.xlsx')
df = pd.read_json('data.json')

df.to_csv('output.csv', index=False)
df.to_excel('output.xlsx')
```

---

## 12.3 Data Exploration

```python
df.head()         # First 5 rows
df.info()         # Column types, non-null counts
df.describe()     # Statistical summary
df.shape          # (rows, columns)
df.columns        # Column names
df['score'].value_counts()  # Frequency counts
```

---

## 12.4 Filtering and Selection

```python
# Column selection
df['name']              # Single column → Series
df[['name', 'score']]   # Multiple columns → DataFrame

# Row filtering
df[df['score'] > 80]
df[(df['age'] > 25) & (df['score'] < 90)]

# loc (label-based) and iloc (position-based)
df.loc[0, 'name']       # 'Alice'
df.iloc[0, 0]           # 'Alice'
df.iloc[:2, 1:]         # First 2 rows, columns 1+
```

---

## 12.5 Data Manipulation

```python
# Add column
df['passed'] = df['score'] >= 80

# Group by and aggregate
df.groupby('passed')['score'].mean()

# Sort
df.sort_values('score', ascending=False)

# Handle missing values
df.dropna()
df.fillna(0)
```

---

## Practice Exercises

1. Load a CSV file, display summary statistics, and filter rows by a condition.

2. Create a DataFrame from a dictionary. Add a computed column. Group by a category.

3. Merge two DataFrames on a common key column.

4. Handle missing values: drop rows with NaN, fill NaNs with column means.

---

## Key Takeaways

- Series = 1D labeled array; DataFrame = 2D labeled table
- Use head(), info(), describe() for exploration
- loc for label-based, iloc for position-based access
- groupby() + aggregate() for grouped analysis
