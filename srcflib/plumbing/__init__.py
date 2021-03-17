"""
Low-level APIs for fine-grained service management.

Each public function in this module should:

- perform a single action idempotently
- raise an exception on any failures

Each function also falls into one of two groups:

- getters (prefixed with `get_`, returns a value directly, does not modify state)
- actions (returns a `Result` object, may modify state)
"""
