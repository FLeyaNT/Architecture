from psycopg2.extensions import connection

from schemas.schemas import CourseInfo


class PgRepo:

    def __init__(
        self,
        connection: connection
    ) -> None:
        self.connection = connection

    def get_course_info(
        self,
        course_name: str,
        semester: int
    ) -> CourseInfo | None:
        cur = self.connection.cursor()

        query = """
            SELECT 
                lc.name as course_name,
                lc.description,
                lc.semester,
                lc.total_hours,
                lc.lecture_hours,
                lc.practice_hours,
                lc.lab_hours,
                lc.is_specialty_discipline,
                s.name as specialty_name,
                s.code as specialty_code,
                s.degree_level,
                lc.id
            FROM lecture_courses lc
            JOIN specialties s ON lc.specialty_id = s.id
            WHERE lc.name = %s AND lc.semester = %s
            LIMIT 1
        """
        
        cur.execute(query, (course_name, semester))
        row = cur.fetchone()
        cur.close()
        
        if row:
            return CourseInfo(
                id = row[11],
                name = row[0],
                description = row[1],
                semester = row[2],
                total_hours = row[3],
                lecture_hours = row[4],
                practice_hours = row[5],
                lab_hours = row[6],
                is_specialy_discipline = row[7],
                speciality_name = row[8],
                speciality_code = row[9],
                degree_level = row[10]
            )
        
        return None
    
    def get_lecture_ids(
        self,
        course_name: str,
        semester: int,
        year: int
    ) -> list[str]:
        cur = self.connection.cursor()

        query = """
            SELECT DISTINCT
                l.id
            FROM lectures l
            JOIN lecture_courses lc ON l.course_id = lc.id
            JOIN schedule sched ON sched.lecture_id = l.id
            WHERE lc.name = %s
            AND lc.semester = %s
            AND EXTRACT(YEAR FROM sched.scheduled_date) = %s
        """
        
        cur.execute(query, (course_name, semester, year))
        rows = cur.fetchall()
        cur.close()

        return [row[0] for row in rows]