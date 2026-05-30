import psycopg2
from typing import Dict, Tuple, List

class PostgresRepo:
    
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn

    def get_attendance_map(
        self,
        student_schedule_pairs: List[Tuple[str, str]]
    ) -> Dict[Tuple[str, str], bool]:
        """
        Принимает список пар (student_id, schedule_id) в виде строк.
        Возвращает словарь {(student_id, schedule_id): is_present}
        """
        if not student_schedule_pairs:
            return {}

        # Уникальные пары
        pairs_set = set(student_schedule_pairs)
        if not pairs_set:
            return {}

        # Разделяем на два списка строковых UUID
        student_ids = [p[0] for p in pairs_set]
        schedule_ids = [p[1] for p in pairs_set]

        query = """
            SELECT student_id, schedule_id, is_present
            FROM attendance
            WHERE (student_id, schedule_id) IN (
                SELECT unnest(%s::uuid[]), unnest(%s::uuid[])
            )
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (student_ids, schedule_ids))
            rows = cur.fetchall()

        attendance_map = {}
        for student_id, schedule_id, is_present in rows:
            attendance_map[(student_id, schedule_id)] = is_present if is_present is not None else False

        return attendance_map