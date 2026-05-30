from repositories import RedisRepo, ElasticRepo, Neo4jRepo, PostgresRepo
from schemas.schemas import (
    AttendanceReportResponse,
    StudentAttendanceFull,
    ReportPeriod,
    StudentAttendanceStats,
    StudentInfo
)

class StudentService:
    
    def __init__(
        self,
        redis_repo: RedisRepo,
        elastic_repo: ElasticRepo,
        neo4j_repo: Neo4jRepo,
        postgres_repo: PostgresRepo
    ):
        self.redis_repo = redis_repo
        self.elastic_repo = elastic_repo
        self.neo4j_repo = neo4j_repo
        self.postgres_repo = postgres_repo

    def get_attendance_report(
        self,
        term: str,
        date_from: str,
        date_to: str,
        limit: int
    ) -> AttendanceReportResponse:
        # 1. Получаем lecture_id из Elasticsearch
        lecture_ids = self.elastic_repo.get_lectures_id_by_term_and_date(
            term, date_from, date_to
        )
        if not lecture_ids:
            return AttendanceReportResponse(
                students=[],
                report_period=ReportPeriod(date_from=date_from, date_to=date_to),
                search_term=term
            )

        # 2. Получаем для каждого студента список schedule_id (Neo4j)
        student_schedule_map = self.neo4j_repo.get_student_schedule_ids(lecture_ids)
        if not student_schedule_map:
            return AttendanceReportResponse(
                students=[],
                report_period=ReportPeriod(date_from=date_from, date_to=date_to),
                search_term=term
            )

        # 3. Получаем отметки посещаемости из PostgreSQL
        # Собираем все пары (student_id, schedule_id)
        pairs = []
        for student_id, sched_ids in student_schedule_map.items():
            for sched_id in sched_ids:
                pairs.append((student_id, sched_id))
        attendance_map = self.postgres_repo.get_attendance_map(pairs)

        # 4. Рассчитываем процент для каждого студента
        student_stats = []
        for student_id, schedule_ids in student_schedule_map.items():
            total = len(schedule_ids)
            if total == 0:
                continue
            attended = sum(
                1 for sched_id in schedule_ids
                if attendance_map.get((student_id, sched_id), False)
            )
            percent = (attended / total) * 100
            student_stats.append(StudentAttendanceStats(
                student_id=student_id,
                total_lectures=total,
                attended_lectures=attended,
                percent=round(percent, 2)
            ))

        # 5. Сортируем по проценту и берем топ-N
        student_stats.sort(key=lambda x: x.percent)
        top_stats = student_stats[:limit]

        # 6. Получаем информацию о студентах из Redis
        student_ids = [s.student_id for s in top_stats]
        students_info = self.redis_repo.get_students_info(student_ids)

        # 7. Объединяем статистику и информацию
        students_full = []
        for info, stats in zip(students_info, top_stats):
            students_full.append(StudentAttendanceFull(
                **info.model_dump(),
                attendance_stats=stats
            ))

        return AttendanceReportResponse(
            students=students_full,
            report_period=ReportPeriod(date_from=date_from, date_to=date_to),
            search_term=term
        )