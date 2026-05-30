from pydantic import BaseModel


class CourseInfo(BaseModel):
    id: str
    name: str
    description: str
    semester: int
    lecture_hours: int
    practice_hours: int
    lab_hours: int
    is_specialy_discipline: bool
    speciality_name: str
    speciality_code: str
    degree_level: str


class ClassInfo(BaseModel):
    schedule_date: str
    start_time: str
    classroom: str
    listeners: int


class LectureInfo(BaseModel):
    lecture_id: str
    title: str
    requires_computers: bool
    listeners_count: int
    classes: list[ClassInfo]


class CourseInfoResponse(CourseInfo):
    lectures: list[LectureInfo]
