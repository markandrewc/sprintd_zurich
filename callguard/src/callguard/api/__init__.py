"""``callguard api``: one HTTP backend (FastAPI) for every frontend. Contract: docs/API.md.

``service`` holds the logic (stored results + live rule book + per-client settings -> JSON); ``app`` the routes.
No model is ever loaded: everything is re-decided from the stored per-call results."""
