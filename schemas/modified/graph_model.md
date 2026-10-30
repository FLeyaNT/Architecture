
<img width="5960" height="1155" alt="image" src="https://github.com/user-attachments/assets/0881348b-0151-4834-b913-e9527f2b573b" />


# Модель графа Neo4j

## Узлы

| Метка | Количество | Свойства | Источник |
|---|---:|---|---|
| `Specialty` | 6 | `id`, `code`, `name`, `degree_level`, `duration_years` | specialties |
| `Course` | 56 | `id`, `name`, `description`, `total_hours`, `lecture_hours`, `practice_hours`, `lab_hours`, `department_id` | lecture_courses |
| `Lecture` | 896 | `id`, `title`, `lecture_type` (`lecture`/`practice`/`lab`), `order_number`, `duration_minutes`, `requires_computers`, `course_id` | lectures |
| `StudentGroup` | 72 | `id`, `name`, `enrollment_year`, `curator`, `specialty_id` | student_groups |
| `Student` | 1 730 | `id`, `group_id` | students |
| `Schedule` | 8 208 | `id`, `scheduled_date` (Date), `start_time` / `end_time` (LocalTime), `status`, `teacher_name`, `group_id`, `lecture_id`, `classroom_id` | schedule |

## Связи

| Связь | Направление | Свойства | Источник |
|---|---|---|---|
| `HAS_COURSE` | `(Specialty)→(Course)` | `id`, `semester`, `is_special` | Строка specialty_courses — связь, а не узел |
| `BELONGS_TO` | `(Lecture)→(Course)` | — | lectures.course_id |
| `HAS_SPECIALTY` | `(StudentGroup)→(Specialty)` | — | student_groups.specialty_id |
| `HAS_STUDENT` | `(StudentGroup)→(Student)` | — | students.group_id |
| `HAS_SCHEDULE` | `(StudentGroup)→(Schedule)` | — | schedule.group_id |
| `PART_OF` | `(Schedule)→(Lecture)` | — | schedule.lecture_id |
