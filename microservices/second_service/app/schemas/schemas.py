from pydantic import BaseModel


class ClassInfo(BaseModel):
    scheduled_date: str
    start_time: str
    classroom: str
    listeners: int


class LectureInfo(BaseModel):
    lecture_id: str
    title: str
    requires_computers: bool
    duration_minutes: int
    listeners_count: int
    classes: list[ClassInfo]


class CourseInfoResponse(BaseModel):
    id: str
    name: str
    description: str
    semester: int
    total_hours: int
    lecture_hours: int
    practice_hours: int
    lab_hours: int
    is_specialty_discipline: bool
    lectures: list[LectureInfo]
