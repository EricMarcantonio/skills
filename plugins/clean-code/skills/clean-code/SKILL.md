---
name: "ericmarcantonio:clean-code"
description: "Enforces the complete Clean Code framework (Robert C. Martin) and The Art of Clean Code (Christian Mayer): specific rules for naming, single-responsibility functions, command-query separation, fail-fast patterns, DRY, no-null returns, the Boy Scout Rule, and the 80/20 principle. Also provides a structured review format (Critical / Significant / Minor) for code reviews. Consult this skill any time you are writing a new function, class, or module; doing a code review or PR review; refactoring or cleaning up existing code; or when the user says code is hard to read, messy, or needs improvement — even if they just say 'write me a function to do X'. This skill has specific named principles and output formats that go beyond general coding advice, so always use it for code quality work."
accepts_conversation: true
tools:
  - Read
  - Grep
  - Glob
  - Edit
  - Write
---

# Clean Code

Apply principles from *Clean Code* (Robert C. Martin) and *The Art of Clean Code* (Christian Mayer) to all code you write or touch. The goal is code that communicates intent clearly, changes safely, and doesn't surprise the next reader — who is often the user six months from now.

Skip these principles for: auto-generated or vendored code, prototypes explicitly marked throwaway, or performance-critical hot paths where a readability tradeoff is intentional and documented.

---

## How to Apply

**When writing new code:** Apply the principles below from the start. Don't write code that violates them and "clean it up later" — the cleanup rarely happens.

**When reviewing or refactoring:** Read the code first. Identify violations prioritized by impact — naming issues compound everywhere; a god function is worse than a long one. Report findings grouped by severity (see Review Output below), then apply fixes or propose them depending on scope.

**When touching existing code:** Follow the Boy Scout Rule — leave it slightly better than you found it. A rename, an extraction, a removed dead comment. Don't rewrite everything; improve what you touch.

**On pragmatism:** These are principles, not laws. When the codebase has consistent existing patterns that differ (e.g., a specific error-handling convention, a `is_` prefix style), match the existing pattern. Consistency within a codebase beats theoretical purity. Flag the deviation if it matters, but don't fight the whole codebase.

---

## Naming

Names are the primary interface between code and the human reading it. A bad name forces the reader to trace execution to understand intent — that's time and trust lost.

- Names must reveal intent. If you need a comment to explain a name, rename it instead.
- Use pronounceable, searchable names. Single-letter variables are acceptable only as tight loop counters.
- Functions: verb phrases (`getUserById`, `processPayment`). Booleans: predicates (`isValid`, `hasPermission`).
- Classes: noun phrases (`UserAccount`, `PaymentProcessor`). Avoid generic suffixes that add no information (`Manager`, `Handler`, `Data`, `Info`).
- Avoid encodings, type prefixes, and Hungarian notation (`strName`, `iCount`, `IInterface`) — types are visible from declarations and tooling.
- Name length should be proportional to scope. A variable used in 3 lines can be short. A public API must be explicit.

---

## Functions

A function should do one thing, do it well, and do it only. This principle makes everything else easier: naming, testing, understanding, and changing.

- **Do one thing.** If you can extract a meaningful sub-function with a non-redundant name, the original does more than one thing.
- One level of abstraction per function. Don't mix high-level orchestration with low-level detail in the same body.
- No more than 3 parameters. More usually means the parameters form a concept — make it an object.
- No side effects hidden inside innocent-sounding functions. A function named `getUser` must not mutate state.
- Command-query separation: a function either does something (command) or answers something (query), not both.
- Fail fast. Validate inputs at the top, return or throw early, and keep the happy path at the lowest indentation level.

---

## Simplicity

Complexity is not a sign of intelligence — it's a maintenance liability. The best code is the code that doesn't exist.

- Write less code. Every line added is a line that can break, needs to be read, and must be maintained.
- Prefer 3 explicit lines over 1 clever line. Explicit beats clever every time.
- Don't abstract prematurely. Three similar lines of code is not a reason to create a helper. Wait until the pattern is real, stable, and has a name that earns its existence.
- YAGNI — You Aren't Gonna Need It. Don't build for hypothetical future requirements.
- Optimize last. Premature optimization produces complex code that solves the wrong problem. Profile first; optimize only what data confirms.

---

## Comments

Every comment is a signal that the code failed to communicate. Refactor first; comment as a last resort.

- Never commit commented-out code. It will not be uncommented. Delete it — version control remembers it.
- Never write comments that restate what the code says (`// increment i` above `i++`).
- Acceptable uses: legal headers; explaining *why* a non-obvious decision was made (not *what* the code does); warnings of known consequences; TODO markers with a ticket reference.
- If you feel compelled to explain what a block does, extract it into a named function instead.

---

## Classes and Structure

A class should have one reason to change. When a class changes for two different reasons, it has two responsibilities — and either change risks breaking the other.

- Small classes. If you need "and" to list a class's responsibilities, split it.
- Hide implementation. Expose behavior, not data. Prefer methods over public fields.
- Prefer composition over inheritance. Inheritance creates tight coupling that's hard to undo; compose behaviors instead.
- Inject dependencies rather than instantiating them inside the class. A class that creates its own dependencies is hard to test and hard to change.

---

## Error Handling

Error handling that obscures control flow is worse than no error handling.

- Use exceptions/errors for exceptional conditions, not for normal control flow.
- Don't return null — it forces every caller to check. Return an empty collection, a typed default, or throw. This applies to query methods too: a `findByEmail` that returns null forces null-checks everywhere it's called; prefer throwing a descriptive error or returning a typed empty result.
- Don't pass null as an argument. Make the caller handle the absence before calling.
- Wrap third-party errors at the boundary. Internal code should work with your own error types, not leak library internals.
- Error messages must be actionable. "Something went wrong" tells the reader nothing. State what failed, what input caused it, and where possible, what to do next.

---

## DRY — Don't Repeat Yourself

Every piece of knowledge must have a single, authoritative representation. When it changes — and it will — you change it in one place.

- Logic duplication is the most dangerous kind. Structural duplication (similar shape, different concept) is sometimes acceptable.
- Configuration, constants, and business rules must live in one place.
- When you catch yourself copying and pasting logic, stop. Extract and name the concept before continuing.

---

## The Boy Scout Rule

Leave every piece of code you touch slightly cleaner than you found it. Not a rewrite — a rename, an extraction, a dead comment removed. Small, consistent improvements compound over time. Never make a file measurably worse than it was when you opened it.

---

## The 80/20 Rule *(Mayer)*

20% of your code delivers 80% of the value and contains 80% of the bugs. Most code should be boring. Reserve your complexity budget for the parts that genuinely need it, and keep everything else simple enough to be obviously correct.

---

## Review Output Format

When performing a code review, structure findings as:

**Critical** — violates correctness or causes hidden bugs (null returns, side effects in query functions, leaked third-party exceptions)
**Significant** — meaningful readability or maintainability issues (god functions, misleading names, premature abstractions)
**Minor** — small improvements worth noting (rename suggestions, extractable named constants, leftover comments)

For each finding: state what it is, why it matters, and suggest the fix. Skip purely stylistic findings that don't affect understanding or safety.
