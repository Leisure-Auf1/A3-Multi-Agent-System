# Chapter 5: Object-Oriented Programming Basics

> **Learning Objective**: Classes, objects, inheritance, and encapsulation.

---

## 5.1 Classes and Objects

```python
class Dog:
    """A simple Dog class."""

    def __init__(self, name, breed):
        self.name = name
        self.breed = breed

    def bark(self):
        print(f"{self.name} says Woof!")

buddy = Dog("Buddy", "Golden Retriever")
buddy.bark()  # Buddy says Woof!
```

__init__ is the constructor — called when creating an object.
self refers to the instance.

---

## 5.2 Inheritance

```python
class Animal:
    def speak(self):
        return "Some sound"

class Cat(Animal):
    def speak(self):      # Override parent method
        return "Meow!"

class Dog(Animal):
    def speak(self):
        return "Woof!"
```

### super() — call parent methods
```python
class Vehicle:
    def __init__(self, brand):
        self.brand = brand

class Car(Vehicle):
    def __init__(self, brand, model):
        super().__init__(brand)
        self.model = model
```

---

## 5.3 Encapsulation

```python
class BankAccount:
    def __init__(self, owner, balance=0):
        self.owner = owner         # public
        self._balance = balance    # protected (convention)

    def deposit(self, amount):
        if amount > 0:
            self._balance += amount

    def get_balance(self):
        return self._balance
```

---

## Practice Exercises

1. Create a Rectangle class with width, height, and an area() method.

2. Create a BankAccount class with deposit(), withdraw(), and get_balance().

3. Create a Student class inheriting from Person, with a courses list.

4. Design Shape -> Circle, Rectangle, Triangle hierarchy with area() methods.

---

## Key Takeaways

- Class = blueprint; object = instance
- __init__ is the constructor; self is the instance reference
- Inheritance enables code reuse; override methods to specialize
- Encapsulation uses naming conventions (_protected, __private)
