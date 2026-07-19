# Chapter 13: Machine Learning Fundamentals

> **Learning Objective**: Understand the ML workflow and apply basic algorithms.

---

## 13.1 The ML Workflow

```
Data Collection → Cleaning → Feature Engineering → Model Training → Evaluation → Deployment
```

### Types of ML
- **Supervised**: Learn from labeled data (classification, regression)
- **Unsupervised**: Find patterns in unlabeled data (clustering, dimensionality reduction)
- **Reinforcement**: Learn through trial and error (game playing, robotics)

---

## 13.2 Train/Test Split

```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
```

---

## 13.3 Linear Regression

```python
from sklearn.linear_model import LinearRegression

model = LinearRegression()
model.fit(X_train, y_train)
predictions = model.predict(X_test)

# Evaluate
from sklearn.metrics import mean_squared_error, r2_score
mse = mean_squared_error(y_test, predictions)
r2 = r2_score(y_test, predictions)
```

---

## 13.4 Classification (Logistic Regression)

```python
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

model = LogisticRegression()
model.fit(X_train, y_train)
preds = model.predict(X_test)

accuracy = accuracy_score(y_test, preds)
print(classification_report(y_test, preds))
```

---

## 13.5 Decision Trees and Random Forests

```python
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(n_estimators=100)
rf.fit(X_train, y_train)
preds = rf.predict(X_test)
```

---

## 13.6 Preprocessing

```python
from sklearn.preprocessing import StandardScaler, LabelEncoder

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)
```

---

## Practice Exercises

1. Load a dataset, split into train/test, train a LinearRegression model.

2. Build a classifier: logistic regression on iris or wine dataset.

3. Compare Decision Tree vs Random Forest accuracy on the same dataset.

4. Apply StandardScaler and observe the effect on model performance.

---

## Key Takeaways

- Always split data into train/test before modeling
- LinearRegression for continuous targets; LogisticRegression for classification
- RandomForest often outperforms single DecisionTree
- Scale features for distance-sensitive algorithms
