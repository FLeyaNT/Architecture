# services/group_report_service.py
from repositories import Neo4jRepo, PostgresRepo, RedisRepo
from schemas.schemas import GroupReportResponse, StudentReport, CourseHours
from collections import defaultdict
from typing import Dict, Any


class GroupReportService:
    def __init__(
        self,
        neo4j_repo: Neo4jRepo,
        pg_repo: PostgresRepo,
        redis_repo: RedisRepo
    ):
        self.neo4j_repo = neo4j_repo
        self.pg_repo = pg_repo
        self.redis_repo = redis_repo

    # services/group_report_service.py
    def get_group_report(self, group_name: str) -> GroupReportResponse:
        # 1. Получаем данные из Neo4j
        neo4j_data = self.neo4j_repo.get_group_report_data(group_name)
        if not neo4j_data:
            raise ValueError(f"Группа '{group_name}' не найдена")
        
        group_info = neo4j_data["group_info"]
        student_courses = neo4j_data["student_courses"]
        all_pairs = neo4j_data["all_pairs"]
        student_ids = neo4j_data["student_ids"]
        
        # 2. Получаем посещаемость из PostgreSQL
        attendance_map = self.pg_repo.get_attendance_map(all_pairs)
        
        # 3. Рассчитываем посещённые часы
        for student_id, courses in student_courses.items():
            for course_name, data in courses.items():
                attended_count = 0
                for sched_id in data["schedule_ids"]:
                    if attendance_map.get((student_id, sched_id), False):
                        attended_count += 1
                data["attended_hours"] = attended_count * 2
        
        # 4. Получаем детальную информацию о студентах из Redis
        students_info_list = self.redis_repo.get_students_info(list(student_ids))
        students_info_dict = {s.id: s for s in students_info_list}
        
        # 5. Формируем отчёт
        students_reports = []
        for student_id in student_ids:
            sdata = students_info_dict.get(student_id)
            
            courses_list = []
            for course_name, data in student_courses[student_id].items():
                courses_list.append(
                    CourseHours(
                        course_id=data["course_id"],           # ← добавили course_id
                        course_name=course_name,
                        planned_hours=float(data["planned_hours"]),
                        attended_hours=float(data["attended_hours"])
                    )
                )
            
            students_reports.append(
                StudentReport(
                    student_id=student_id,
                    full_name=getattr(sdata, 'full_name', '') if sdata else '',
                    student_card_number=getattr(sdata, 'student_card_number', '') if sdata else '',
                    email=getattr(sdata, 'email', '') if sdata else '',
                    phone=getattr(sdata, 'phone', '') if sdata else '',
                    enrollment_date=getattr(sdata, 'enrollment_date', '') if sdata else '',
                    courses=courses_list
                )
            )
        
        return GroupReportResponse(
            group_name=group_info["name"],
            enrollment_year=group_info["enrollment_year"],
            curator=group_info["curator"],
            specialty_name=group_info["specialty_name"],
            specialty_code=group_info["specialty_code"],
            degree_level=group_info["degree_level"],
            duration_years=group_info["duration_years"],
            students=students_reports
        )