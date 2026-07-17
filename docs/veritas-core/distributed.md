# Distributed Runtime

> **Phase 5.9** | Multi-node runtime orchestration.

## Design Goal

Enable Veritas to run across multiple nodes — register workers, dispatch
tasks by capability, propagate events, and collect traces — all without
modifying RuntimeEngine.

## Architecture

```
NodeRegistry ←── RuntimeNode × N
     │               │ heartbeat, capabilities
     │
     ├─ find_by_capability → RemoteExecutionManager
     │                          │ submit → assign → execute → collect
     │
     └─ health → check_health / health_summary

DistributedEventBus(RuntimeEventBus)
     │
     ├─ emit(event) → local subscribers + remote transports
     └─ InMemoryTransport (for testing)

DistributedTraceCollector
     └─ add_node_traces(node, data) → aggregate_summary / timeline
```

## RuntimeNode

```python
from src.runtime.distributed import RuntimeNode, NodeCapability

node = RuntimeNode(
    name="worker-1",
    address="localhost:8001",
    capabilities=[
        NodeCapability(name="evaluation", max_concurrency=2),
        NodeCapability(name="profile_extraction"),
    ],
    labels={"region": "us-east"},
)

node.heartbeat()         # mark as alive
node.mark_degraded()     # report issues
node.mark_offline()      # take offline
print(node.is_available) # True if healthy or degraded
```

## NodeRegistry

```python
from src.runtime.distributed import NodeRegistry

registry = NodeRegistry()
registry.register_node(node1)
registry.register_node(node2)

# Discovery
evaluators = registry.find_by_capability("evaluation")
best = registry.find_best_for("evaluation")  # HEALTHY preferred

# Health
print(registry.health_summary())
# {total: 2, healthy: 1, degraded: 0, offline: 1, available: 1}

changes = registry.check_health()
```

## DistributedEventBus

```python
from src.runtime.distributed import DistributedEventBus

bus = DistributedEventBus()

# Local subscriptions (identical to RuntimeEventBus)
bus.subscribe("evaluation", my_handler)

# Remote nodes
bus.register_node("worker-1", transport=send_to_worker_1,
                  event_filter=["evaluation", "transition"])

# Emit → local + remote
bus.emit(RuntimeEvent(event_type="evaluation"))

# Broadcast with per-node delivery status
results = bus.broadcast(event)
# {"worker-1": True, "worker-2": False}
```

## RemoteExecutionManager

```python
from src.runtime.distributed import RemoteExecutionManager

rem = RemoteExecutionManager(registry)

# Register capability executors
rem.register_executor("evaluation", lambda payload: evaluate(payload))

# Submit task
task = rem.submit("evaluation", {"goal": "learn Python"})
print(task.status)        # ASSIGNED (if node found) or PENDING

# Execute
result = rem.execute(task.id)
print(task.status)        # COMPLETED

# Or wait
result = rem.wait_for(task.id, timeout=5.0)
```

## DistributedTraceCollector

```python
from src.runtime.distributed import DistributedTraceCollector

collector = DistributedTraceCollector()
collector.add_node_traces("worker-1", recorder.to_dict())
collector.add_node_traces("worker-2", recorder.to_dict())

# Cross-node queries
print(collector.by_node("worker-1"))
print(collector.by_action("RETRY"))
print(collector.aggregate_summary())
print(collector.timeline())  # chronologically sorted
```

## Limitations

- No real network transport included — `InMemoryTransport` for testing
- `RemoteExecutionManager` assumes synchronous execution
- Node health is heartbeat-based, no active probing
