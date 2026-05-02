<img width="521" height="451" alt="image" src="https://github.com/user-attachments/assets/93d70356-4fed-41cd-90ca-5c0de5043c2f" />

# Описание схемы

<img width="1148" height="900" alt="image" src="https://github.com/user-attachments/assets/ed4c9587-8a07-4062-b0e5-2a6915757d75" />


```json
{
    "_comment_rel": "Связи (Relationship)",
    "items_rel": [
        {
            "_relationship": "ENROLLED_IN",
            "_description": "Является ли студент зачисленным в группу",
            "_properties": {
                "enrollment_year": "Дата зачисления"
            }
        },
        {
            "_relationship": "HAS_LECTURE",
            "_description": "Есть ли занятие по расписанию",
            "_properties": {
                "scheduled_date": "Дата проведения занятия",
                "classroom": "Номер кабинета",
                "teacher": "Имя преподавателя"
            }
        },
        {
            "_relationship": "ATTENDED",
            "_description": "Отмечен ли студент на занятии",
            "_properties": {
                "present": "bool",
                "marked_at": "Отмечен когда",
                "marked_by": "Отмечен кем"
            }
        }
    ],
    "_comment_node": "Узлы (Nodes)",
    "items_node": [
        {
            "_node": "Student",
            "_description": "Описание студента",
            "_properties": {
                "id": "Id студента",
                "name": "ФИО студента",
                "student_card_number": "Номер студенческого билета",
                "email": "Email"
            }
        },
        {
            "_node": "Group",
            "_description": "Описание группы",
            "_properties": {
                "id": "Id группы",
                "name": "Название группы",
                "enrollment_year": "Год зачисления"
            }
        },
        {
            "_node": "Lecture",
            "_description": "Описание лекции",
            "_properties": {
                "id": "Id лекции",
                "title": "Название лекции",
                "course_name": "Название курса",
                "date": "Дата проведения",
                "duration_minutes": "продолжительность в минутах",
                "is_speciality": "Является ли спец. дисциплиной"
            }
        }
    ]
}
```
