from repositories import Neo4jRepo
from schemas.schemas import CourseInfoResponse, LectureInfo, ClassInfo


class CourseService:
    
    def __init__(self, neo4j_repo: Neo4jRepo):
        self.neo4j_repo = neo4j_repo

    def get_course_info(self, course_name: str, semester: int, year: int) -> CourseInfoResponse:
        data = self.neo4j_repo.get_course_full_info(course_name, semester, year)
        if not data:
            raise ValueError(f"Курс '{course_name}' (семестр {semester}) не найден")

        # Преобразуем лекции в Pydantic модели
        lectures = []
        for lec in data["lectures"]:
            classes = [
                ClassInfo(
                    scheduled_date=c["scheduled_date"],
                    start_time=c["start_time"],
                    classroom=c["classroom"],
                    listeners=c["listeners"]
                )
                for c in lec["classes"]
            ]
            lectures.append(
                LectureInfo(
                    lecture_id=lec["lecture_id"],
                    title=lec["title"],
                    requires_computers=lec["requires_computers"],
                    duration_minutes=lec["duration_minutes"],
                    listeners_count=lec["listeners_count"],
                    classes=classes
                )
            )

        return CourseInfoResponse(
            id=data["course"]["id"],
            name=data["course"]["name"],
            description=data["course"]["description"],
            semester=data["course"]["semester"],
            total_hours=data["course"]["total_hours"],
            lecture_hours=data["course"]["lecture_hours"],
            practice_hours=data["course"]["practice_hours"],
            lab_hours=data["course"]["lab_hours"],
            is_specialty_discipline=data["course"]["is_specialty_discipline"],
            lectures=lectures
        )
