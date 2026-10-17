"""E2E fixtures (PS-212) — fixtures only, no blanket skip gate.

End-to-end tests are mandatory on every PR: a bare `pytest` MUST
collect and run them. The only legitimate skip is per-test, keyed to
a missing subsystem — never a blanket `RUN_E2E`-style env gate.
"""
