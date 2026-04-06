---
description: Karpathy-style code simplification — delete code, not add it
---

# Karpathy Simplification Skill

Inspired by Andrej Karpathy's philosophy: **the best code is the code you don't write**. Use this skill before and during implementation to ruthlessly simplify.

## Core Principles

### 1. Delete First, Add Never
Before adding a new abstraction, class, wrapper, or helper — ask:  
> "Can I solve this by *removing* existing complexity instead?"

The ideal diff has more red lines than green.

### 2. The Staging Areas Are Deadly
Every intermediate layer (wrapper widget, state enum, adapter, mapper) adds:
- One more thing to get wrong
- One more thing to debug
- One more thing future you won't understand

**Default to flat code.** Introduce layers only when duplication is actually painful.

### 3. State Is the Enemy
Every `bool`, `enum`, `Timer`, and field in a `State` class is a bug waiting to happen. Ask:
- Does this field need to exist at all?
- Can the widget derive this value from its parent/stream instead of storing it?
- Can `setState` be replaced by just re-reading a service synchronously?

### 4. The Checklist Before Adding Any Code

Before writing new code, verify these in order:

- [ ] Can I delete something instead?
- [ ] Is this complexity caused by working around another piece of bad code?
- [ ] Does this new abstraction replace ≥3 existing things, or am I adding a 4th thing?
- [ ] Will a junior dev understand this in 6 months without docs?
- [ ] Am I solving the actual problem or a symptom of it?

### 5. Toy Implementation First
Always write the **dumbest possible version** that could work before reaching for a clever one. Then only add complexity when the dumb version demonstrably fails.

Bad → Good examples:

| Over-engineered | Simple |  
|---|---|
| `AnimationController` + `Tween` + `CurvedAnimation` + `AnimatedBuilder` | `AnimatedContainer` with `duration` |
| Custom `StatefulWidget` with `StreamSubscription` + `setState` | `StreamBuilder` |
| Enum with 6 states + switch everywhere | `bool isLoading` + `String? error` |
| `Timer` for debounce + cancel logic | `Stream.debounceTime()` |

### 6. When Applying This Skill

When asked to "use the karpathy skill" on a piece of code:

1. **Read the code fully first**
2. **List everything that could be deleted** — fields, methods, wrappers, conditionals
3. **Count the states** — how many `bool`s and `enum`s exist? Each one is a combinatorial explosion
4. **Propose the simplified version** before implementing
5. **Implement** — the result should have fewer lines than before

## Application to Flutter Specifically

- Prefer `ValueListenableBuilder` / `StreamBuilder` over manual stream subscriptions + setState
- Prefer `AnimatedSwitcher` / `AnimatedContainer` over `AnimationController`
- Prefer `FutureBuilder` over manual `isLoading` + `data` + `error` state fields
- One source of truth: if a value is available from a service synchronously, don't cache it in widget state
- `const` constructors everywhere possible — if it can't be const, ask why
