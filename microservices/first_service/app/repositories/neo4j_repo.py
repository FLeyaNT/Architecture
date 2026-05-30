from neo4j import Session
from typing import List, Dict

class Neo4jRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_student_schedule_ids(
        self,
        lecture_ids: List[str],
        date_from: str,
        date_to: str
    ) -> Dict[str, List[str]]:
        if not lecture_ids:
            return {}

        query = """
            MATCH (l:Lecture)
            WHERE l.id IN $lecture_ids
            MATCH (l)<-[:PART_OF]-(sch:Schedule)
            WHERE sch.date >= $date_from AND sch.date <= $date_to
            MATCH (sch)<-[:HAS_SCHEDULE]-(sg:StudentGroup)
            MATCH (sg)-[:HAS_STUDENT]->(s:Student)
            RETURN s.id AS student_id, collect(sch.id) AS schedule_ids
        """
        result = self.session.run(
            query,
            lecture_ids=lecture_ids,
            date_from=date_from,
            date_to=date_to
        )
        student_schedules = {}
        for record in result:
            student_id = record["student_id"]
            schedule_ids = record["schedule_ids"]
            if schedule_ids:
                student_schedules[student_id] = schedule_ids
        return student_schedules