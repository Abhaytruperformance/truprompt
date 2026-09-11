from app.db.pg import org_scoped_cursor


def list_departments(org_id: str) -> list[dict]:
    with org_scoped_cursor(org_id) as cur:
        cur.execute("select * from departments where org_id = %s order by name", (org_id,))
        return cur.fetchall()


def create_department(org_id: str, name: str) -> dict:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "insert into departments (org_id, name) values (%s, %s) returning *",
            (org_id, name),
        )
        return cur.fetchone()


def delete_department(org_id: str, department_id: str) -> dict | None:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "delete from departments where id = %s and org_id = %s returning *",
            (department_id, org_id),
        )
        return cur.fetchone()
