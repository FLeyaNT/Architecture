# repositories/neo4j_repo.py
from neo4j import Session
from typing import Dict, Any
from collections import defaultdict

class Neo4jRepo:
    def __init__(self, session: Session):
        self.session = session

    # repositories/neo4j_repo.py
    def get_group_report_data(self, group_name: str) -> Dict[str, Any]:
        query = """
            MATCH (sg:StudentGroup {name: $group_name})
            MATCH (sg)-[:HAS_SPECIALTY]->(sp:Specialty)
            MATCH (sg)-[:HAS_STUDENT]->(s:Student)
            MATCH (sg)-[:HAS_SCHEDULE]->(sch:Schedule)
            MATCH (sch)-[:PART_OF]->(l:Lecture)
            MATCH (l)-[:BELONGS_TO]->(c:Course)
            WHERE c.is_specialty_discipline = true
            RETURN sg.name AS group_name,
                sg.enrollment_year AS enrollment_year,
                sg.curator AS curator,
                sp.id AS specialty_id,
                sp.name AS specialty_name,
                sp.code AS specialty_code,
                sp.degree_level AS degree_level,
                sp.duration_years AS duration_years,
                s.id AS student_id,
                c.id AS course_id,
                c.name AS course_name,
                c.lecture_hours AS planned_hours,
                sch.id AS schedule_id
        """
        result = self.session.run(query, group_name=group_name)
        records = list(result)

        if not records:
            return None

        # Извлекаем информацию о группе (из первой записи)
        group_info = {
            "name": records[0]["group_name"],
            "enrollment_year": records[0]["enrollment_year"],
            "curator": records[0]["curator"],
            "specialty_id": records[0]["specialty_id"],
            "specialty_name": records[0]["specialty_name"],
            "specialty_code": records[0]["specialty_code"],
            "degree_level": records[0]["degree_level"],
            "duration_years": records[0]["duration_years"]
        }

        # Группируем по студентам и курсам
        student_courses = defaultdict(lambda: defaultdict(lambda: {"schedule_ids": [], "planned_hours": 0, "course_id": None}))
        all_pairs = []
        student_ids = set()

        for record in records:
            student_id = record["student_id"]
            student_ids.add(student_id)
            course_id = record["course_id"]
            course_name = record["course_name"]
            planned_hours = record["planned_hours"]
            schedule_id = record["schedule_id"]

            student_courses[student_id][course_name]["schedule_ids"].append(schedule_id)
            student_courses[student_id][course_name]["planned_hours"] = planned_hours
            student_courses[student_id][course_name]["course_id"] = course_id
            all_pairs.append((student_id, schedule_id))

        return {
            "group_info": group_info,
            "student_courses": student_courses,
            "all_pairs": all_pairs,
            "student_ids": student_ids
        }