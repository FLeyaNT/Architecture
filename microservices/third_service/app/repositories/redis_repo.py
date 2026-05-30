from redis import Redis

from schemas.schemas import StudentInfo


class RedisRepo:

    def __init__(
        self,
        redis_client: Redis
    ) -> None:
        self.redis_client = redis_client

    def get_students_info(
        self,
        student_ids: list[str]
    ) -> list[StudentInfo]:
        if not student_ids:
            return []
        
        pipeline = self.redis_client.pipeline()
        
        for student_id in student_ids:
            key = f"student:{student_id}:data"
            pipeline.hgetall(key)
        
        results: list[dict] = pipeline.execute()
        
        students_info = []
        for data in results:
            if data:
                students_info.append(StudentInfo(**data))
        
        return students_info
