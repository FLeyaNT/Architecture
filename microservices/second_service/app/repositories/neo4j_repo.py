from neo4j import Session
from typing import List, Dict, Any
from collections import defaultdict


class Neo4jRepo:
    
    def __init__(self, session: Session):
        self.session = session

    def get_course_full_info(self, course_name: str, semester: int, year: int) -> Dict[str, Any]:
        query = """
            MATCH (c:Course {name: $course_name, semester: $semester})
            OPTIONAL MATCH (c)<-[:BELONGS_TO]-(l:Lecture)
            OPTIONAL MATCH (l)<-[:PART_OF]-(sch:Schedule)
            WHERE sch.date STARTS WITH $year_str
            OPTIONAL MATCH (sch)<-[:HAS_SCHEDULE]-(sg:StudentGroup)
            OPTIONAL MATCH (sg)-[:HAS_STUDENT]->(s:Student)
            RETURN c.id AS course_id,
                   c.name AS course_name,
                   c.description AS course_description,
                   c.semester AS course_semester,
                   c.total_hours AS total_hours,
                   c.lecture_hours AS lecture_hours,
                   c.practice_hours AS practice_hours,
                   c.lab_hours AS lab_hours,
                   c.is_specialty_discipline AS is_specialty_discipline,
                   l.id AS lecture_id,
                   l.title AS lecture_title,
                   l.requires_computers AS requires_computers,
                   l.duration_minutes AS duration_minutes,
                   sch.date AS scheduled_date,
                   sch.time AS start_time,
                   sch.classroom AS classroom,
                   COUNT(DISTINCT s) AS listeners_count
        """
        params = {
            "course_name": course_name,
            "semester": semester,
            "year_str": str(year)
        }
        result = self.session.run(query, params)
        records = list(result)

        if not records:
            return None

        # Извлекаем информацию о курсе (из первой записи)
        course_info = {
            "id": records[0]["course_id"],
            "name": records[0]["course_name"],
            "description": records[0]["course_description"] or "",
            "semester": records[0]["course_semester"],
            "total_hours": records[0]["total_hours"],
            "lecture_hours": records[0]["lecture_hours"],
            "practice_hours": records[0]["practice_hours"],
            "lab_hours": records[0]["lab_hours"],
            "is_specialty_discipline": records[0]["is_specialty_discipline"]
        }

        # Группируем лекции
        lectures_dict = {}
        for record in records:
            lec_id = record["lecture_id"]
            if not lec_id:
                continue

            if lec_id not in lectures_dict:
                lectures_dict[lec_id] = {
                    "lecture_id": lec_id,
                    "title": record["lecture_title"],
                    "requires_computers": bool(record["requires_computers"]),
                    "duration_minutes": record["duration_minutes"],
                    "listeners_count": 0,
                    "classes": []
                }

            if record["scheduled_date"]:
                # Добавляем информацию о занятии
                lectures_dict[lec_id]["classes"].append({
                    "scheduled_date": record["scheduled_date"],
                    "start_time": record["start_time"],
                    "classroom": record["classroom"],
                    "listeners": record["listeners_count"]
                })
                # Суммируем слушателей по всем занятиям лекции
                lectures_dict[lec_id]["listeners_count"] += record["listeners_count"]

        lectures = list(lectures_dict.values())

        return {
            "course": course_info,
            "lectures": lectures
        }