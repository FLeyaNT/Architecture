from pydantic import BaseModel
from typing import List, Optional


class StudentInfo(BaseModel):
    id: str
    full_name: str
    student_card_number: str
    email: str
    phone: str
    enrollment_date: str
    group_name: str

class CourseHours(BaseModel):
    """Часы по курсу"""
    course_id: str             # ← добавили ID курса
    course_name: str
    planned_hours: float       # запланированные часы
    attended_hours: float      # прослушанные часы

class StudentReport(BaseModel):
    """Отчёт по студенту"""
    student_id: str
    full_name: str
    student_card_number: str
    email: str
    phone: str
    enrollment_date: str
    courses: List[CourseHours]   # список курсов с часами

class GroupReportResponse(BaseModel):
    """Ответ для лабораторной работы №3"""
    group_name: str
    enrollment_year: int
    curator: str
    specialty_name: str
    specialty_code: str
    degree_level: str
    duration_years: int
    students: List[StudentReport]