# Chapter 14: Neural Networks

> **Learning Objective**: Understand and implement basic neural networks.

---

## 14.1 What is a Neural Network?

A computational model inspired by biological neurons:
- **Input layer**: Receives features
- **Hidden layers**: Learn representations
- **Output layer**: Produces predictions
- **Activation functions**: Add non-linearity (ReLU, sigmoid, tanh)
- **Weights and biases**: Learned parameters

---

## 14.2 Training Loop

```
1. Forward pass: compute predictions
2. Compute loss: measure error
3. Backward pass: compute gradients
4. Update weights: gradient descent
5. Repeat until convergence
```

---

## 14.3 Simple NN with PyTorch

```python
import torch
import torch.nn as nn

class SimpleNN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x

model = SimpleNN(10, 64, 1)
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
```

---

## 14.4 Training Loop in PyTorch

```python
for epoch in range(100):
    # Forward
    outputs = model(X_train)
    loss = criterion(outputs, y_train)

    # Backward
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if epoch % 10 == 0:
        print(f"Epoch {epoch}: loss = {loss.item():.4f}")
```

---

## 14.5 Key Concepts

- **Epochs**: One full pass through the training data
- **Batch size**: Number of samples per gradient update
- **Learning rate**: Step size for weight updates
- **Overfitting**: Model memorizes training data, fails on new data
- **Regularization**: Dropout, weight decay to prevent overfitting

---

## Practice Exercises

1. Build a 2-layer NN for binary classification on synthetic data.

2. Train for 100 epochs, plot the loss curve.

3. Compare a 1-hidden-layer vs 3-hidden-layer model on the same task.

4. Add dropout (nn.Dropout(0.5)) and observe the effect on overfitting.

---

## Key Takeaways

- Neural networks learn hierarchical representations
- Forward pass → loss → backward pass → update
- PyTorch provides nn.Module, optimizers, and loss functions
- More layers = more capacity but more risk of overfitting
