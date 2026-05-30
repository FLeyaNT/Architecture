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

class StudentAttendanceStats(BaseModel):
    student_id: str
    total_lectures: int
    attended_lectures: int
    percent: float

class StudentAttendanceFull(StudentInfo):
    attendance_stats: StudentAttendanceStats

class ReportPeriod(BaseModel):
    date_from: str
    date_to: str

class AttendanceReportResponse(BaseModel):
    students: List[StudentAttendanceFull]
    report_period: ReportPeriod
    search_term: str