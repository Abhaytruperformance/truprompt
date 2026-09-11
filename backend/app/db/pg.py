"""Direct Postgres access for org-scoped tables (organizations,
organization_members, invitations, prompts) -- these have real Row Level
Security enforced by the database, unlike app/db/supabase.py's client, which
uses SUPABASE_SERVICE_ROLE_KEY and therefore bypasses RLS unconditionally.

Connects as the restricted `tru_app` role (NOBYPASSRLS). Every request sets
`app.org_id` (and optionally `app.user_id`) as session-local variables that
the RLS policies check via `current_setting('app.org_id', true)` -- forgetting
to set it fails closed (zero rows), it does not fail open.
"""

import contextlib

import psycopg2
import psycopg2.extensions
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from app.core.config import settings

# Return uuid columns as plain str, not uuid.UUID -- avoids a class of "UUID
# object != string from the other client" bugs when comparing ids that came
# from this connection vs. the existing supabase-py client.
psycopg2.extensions.register_type(
    psycopg2.extensions.new_type((2950,), "UUID_AS_STR", lambda value, curs: value)
)

_pool = pool.ThreadedConnectionPool(
    1,
    10,
    host=settings.APP_DB_HOST,
    port=settings.APP_DB_PORT,
    dbname=settings.APP_DB_NAME,
    user=settings.APP_DB_USER,
    password=settings.APP_DB_PASSWORD,
)


def _set_scope(conn, org_id: str, user_id: str | None):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SET LOCAL app.org_id = %s", (org_id,))
    if user_id:
        cur.execute("SET LOCAL app.user_id = %s", (user_id,))
    return cur


@contextlib.contextmanager
def org_scoped_cursor(org_id: str, user_id: str | None = None):
    conn = _pool.getconn()
    try:
        try:
            cur = _set_scope(conn, org_id, user_id)
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            # Supabase's pooler drops idle connections server-side; the pool
            # doesn't notice until the first query on a stale one fails.
            # Discard it and retry once against a fresh connection instead of
            # 500ing on every request unlucky enough to grab a dead one.
            _pool.putconn(conn, close=True)
            conn = _pool.getconn()
            cur = _set_scope(conn, org_id, user_id)

        with conn:  # commits on clean exit, rolls back on exception
            yield cur
    finally:
        _pool.putconn(conn)
