from repositories import PgRepo, Neo4jRepo
from schemas.schemas import CourseInfoResponse


class CourseService:
    
    def __init__(self, pg_repo: PgRepo, neo4j_repo: Neo4jRepo):
        self.pg_repo = pg_repo
        self.neo4j_repo = neo4j_repo

    def get_course_info(self, course_name: str, semester: int, year: int) -> CourseInfoResponse:
        # 1. Получаем информацию о курсе из PostgreSQL
        course_info = self.pg_repo.get_course_info(course_name, semester)
        if course_info is None:
            raise ValueError("Course not found")

        # 2. Получаем лекции и расписание из Neo4j (без дополнительного запроса ID)
        lectures_info = self.neo4j_repo.get_course_lectures_info(course_name, semester, year)

        return CourseInfoResponse(
            **course_info.model_dump(),
            lectures=lectures_info
        )
