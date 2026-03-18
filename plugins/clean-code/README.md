# clean-code

Applies principles from *Clean Code* (Robert C. Martin) and *The Art of Clean Code* (Christian Mayer) when writing, reviewing, or refactoring code.

## Overview

This plugin loads clean code standards as active guidance for Claude — covering naming, function design, error handling, comments policy, DRY, and the 80/20 rule from Mayer. It is intended to work across any language or stack.

Claude will apply these principles automatically when writing new code or when asked to review or improve existing code. You can also invoke it directly with `/clean-code`.

## Installation

```
/plugin install EricMarcantonio/skills/plugins/clean-code
```

## Core Capabilities

- **Naming:** Enforces intent-revealing, pronounceable names at the right scope
- **Functions:** Single responsibility, ≤3 params, command-query separation, fail fast
- **Simplicity:** YAGNI, no premature abstraction, no premature optimization
- **Comments:** Last resort only — code should be self-documenting
- **Error handling:** No null returns, actionable error messages, wrapped third-party errors
- **DRY:** Single source of truth for logic, configuration, and constants
- **Boy Scout Rule:** Leave code cleaner than you found it

## When to Use

- Starting a new feature or module
- Refactoring existing code
- Before opening a PR
- When code is hard to explain to another engineer

## When NOT to Use

- Auto-generated or third-party code
- Prototypes explicitly marked as throwaway
- Performance hot paths where readability tradeoffs are intentional

## Related Plugins

Check the [marketplace](../../README.md) for other available plugins.
