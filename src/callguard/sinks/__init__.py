"""Sink plugins: where a finished CallResult goes (result files for the UI, Outcept triggers, ...).

Sinks run after the decision and must never break a call: the pipeline logs and skips failures.
"""
