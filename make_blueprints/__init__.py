"""Make.com scenario blueprint builders.

Each module here generates a Make.com scenario blueprint (JSON) and POSTs/PATCHes
it via Make REST API. Run any of them as a CLI:

    python -m make_blueprints.03_writer
    python -m make_blueprints.06_publisher_telegram
    python -m make_blueprints.00_factory_overview

All modules read connection IDs, tokens, and database IDs from app.config (env vars).
"""
