from neo4j import Session
from collections import defaultdict
from schemas.schemas import LectureInfo, ClassInfo

class Neo4jRepo:
    
    def __init__(self, session: Session):
        self.session = session

    def get_course_lectures_info(self, course_name: str, semester: int, year: int) -> list[LectureInfo]:
        query = """
            MATCH (c:Course {name: $course_name, semester: $semester})
            MATCH (c)<-[:BELONGS_TO]-(l:Lecture)
            OPTIONAL MATCH (l)<-[:PART_OF]-(sch:Schedule)
            WHERE sch.date STARTS WITH $year_str
            OPTIONAL MATCH (sch)<-[:HAS_SCHEDULE]-(sg:StudentGroup)
            OPTIONAL MATCH (sg)-[:HAS_STUDENT]->(s:Student)
            RETURN l.id AS lecture_id,
                   l.title AS lecture_title,
                   l.requires_computers AS requires_computers,
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

        lectures_dict = {}
        for record in records:
            lec_id = record['lecture_id']
            if lec_id not in lectures_dict:
                lectures_dict[lec_id] = {
                    "title": record['lecture_title'],
                    "requires_computers": bool(record['requires_computers']),
                    "classes_map": defaultdict(lambda: {"listeners": 0})
                }

            if record['scheduled_date']:
                slot_key = (record['scheduled_date'], record['start_time'], record['classroom'])
                lectures_dict[lec_id]["classes_map"][slot_key]["listeners"] += record['listeners_count']
                if "scheduled_date" not in lectures_dict[lec_id]["classes_map"][slot_key]:
                    lectures_dict[lec_id]["classes_map"][slot_key]["scheduled_date"] = record['scheduled_date']
                    lectures_dict[lec_id]["classes_map"][slot_key]["start_time"] = record['start_time']
                    lectures_dict[lec_id]["classes_map"][slot_key]["classroom"] = record['classroom']

        lectures = []
        for lec_id, data in lectures_dict.items():
            classes = [
                ClassInfo(
                    schedule_date=slot_data["scheduled_date"],
                    start_time=slot_data["start_time"],
                    classroom=slot_data["classroom"],
                    listeners=slot_data["listeners"]
                )
                for slot_data in data["classes_map"].values()
            ]
            total_listeners = sum(c.listeners for c in classes)
            lectures.append(
                LectureInfo(
                    lecture_id=lec_id,
                    title=data["title"],
                    requires_computers=data["requires_computers"],
                    listeners_count=total_listeners,
                    classes=classes
                )
            )
        return lectures