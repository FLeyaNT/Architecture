import psycopg2
from psycopg2 import sql
from faker import Faker
import random
from datetime import datetime, timedelta
from uuid import uuid4

import redis_sync
import neo4j_sync
import mongodb_sync
import elastic_sync

fake = Faker('ru_RU')

# Подключение к БД
conn = psycopg2.connect(
    host='localhost',
    port=5433,
    database='university_system',
    user='postgres',
    password='postgres'
)
cur = conn.cursor()


# ============================================================
# 1. Генерация университетов (1-3 записи)
# ============================================================


universities = []
for _ in range(3):
    universities.append({
        'id': str(uuid4()),
        'name': fake.company() + ' университет',
        'short_name': fake.company_suffix(),
        'address': fake.address(),
        'website': fake.url(),
        'founded_year': random.randint(1900, 2020)
    })

cur.executemany("""
    INSERT INTO universities (id, name, short_name, address, website, founded_year)
    VALUES (%(id)s, %(name)s, %(short_name)s, %(address)s, %(website)s, %(founded_year)s)
""", universities)
print(f"✓ Добавлено {len(universities)} университетов")


# ============================================================
# 2. Генерация институтов (10-20 на университет)
# ============================================================


institutes = []
for univ in universities:
    for _ in range(random.randint(5, 15)):
        institutes.append({
            'id': str(uuid4()),
            'university_id': univ['id'],
            'name': f"Институт {fake.word().capitalize()} и {fake.word().capitalize()}",
            'short_name': fake.bothify(text='???#', letters='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'),
            'dean': fake.name()
        })

cur.executemany("""
    INSERT INTO institutes (id, university_id, name, short_name, dean)
    VALUES (%(id)s, %(university_id)s, %(name)s, %(short_name)s, %(dean)s)
""", institutes)
print(f"✓ Добавлено {len(institutes)} институтов")


# ============================================================
# 3. Генерация кафедр (3-8 на институт)
# ============================================================


departments = []
for inst in institutes:
    for _ in range(random.randint(3, 8)):
        departments.append({
            'id': str(uuid4()),
            'institute_id': inst['id'],
            'name': f"Кафедра {fake.job()}",
            'short_name': fake.bothify(text='???#', letters='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'),
            'head': fake.name(),
            'room': f"{random.choice(['А', 'Б', 'В', 'Г', 'Д'])}-{random.randint(100, 500)}"
        })

cur.executemany("""
    INSERT INTO departments (id, institute_id, name, short_name, head, room)
    VALUES (%(id)s, %(institute_id)s, %(name)s, %(short_name)s, %(head)s, %(room)s)
""", departments[:1000])
print(f"✓ Добавлено {min(1000, len(departments))} кафедр")


# ============================================================
# 4. Генерация специальностей (30-50)
# ============================================================


specialties = []
degree_levels = ['bachelor', 'master', 'specialist']
for i in range(50):
    code = f"{random.randint(1, 99):02d}.{random.randint(1, 99):02d}.{random.randint(1, 9):02d}"
    specialties.append({
        'id': str(uuid4()),
        'name': fake.job(),
        'code': code,
        'degree_level': random.choice(degree_levels),
        'duration_years': random.choice([4, 4, 4, 5, 5, 6])
    })

cur.executemany("""
    INSERT INTO specialties (id, name, code, degree_level, duration_years)
    VALUES (%(id)s, %(name)s, %(code)s, %(degree_level)s, %(duration_years)s)
""", specialties)
print(f"✓ Добавлено {len(specialties)} специальностей")


# ============================================================
# 5. Связь кафедр и специальностей
# ============================================================


department_specialties = []
for dept in departments[:200]:
    for spec in random.sample(specialties, random.randint(1, 5)):
        department_specialties.append({
            'id': str(uuid4()),
            'department_id': dept['id'],
            'specialty_id': spec['id'],
            'is_primary': random.choice([True, False])
        })

cur.executemany("""
    INSERT INTO department_specialties (id, department_id, specialty_id, is_primary)
    VALUES (%(id)s, %(department_id)s, %(specialty_id)s, %(is_primary)s)
""", department_specialties[:2000])
print(f"✓ Добавлено {min(2000, len(department_specialties))} связей кафедра-специальность")


# ============================================================
# 6. Генерация курсов лекций (1000)
# ============================================================


lecture_courses = []
for i in range(1000):
    spec = random.choice(specialties)
    lecture_courses.append({
        'id': str(uuid4()),
        'specialty_id': spec['id'],
        'name': f"{fake.catch_phrase()}",
        'description': fake.text(max_nb_chars=500),
        'semester': random.randint(1, 8),
        'total_hours': random.randint(36, 144),
        'lecture_hours': random.randint(18, 72),
        'practice_hours': random.randint(0, 36),
        'lab_hours': random.randint(0, 36),
        'is_specialty_discipline': random.choice([True, False])
    })

cur.executemany("""
    INSERT INTO lecture_courses (id, specialty_id, name, description, semester, 
                                 total_hours, lecture_hours, practice_hours, lab_hours, is_specialty_discipline)
    VALUES (%(id)s, %(specialty_id)s, %(name)s, %(description)s, %(semester)s,
            %(total_hours)s, %(lecture_hours)s, %(practice_hours)s, %(lab_hours)s, %(is_specialty_discipline)s)
""", lecture_courses)
print(f"✓ Добавлено {len(lecture_courses)} курсов лекций")


# ============================================================
# 7. Генерация лекций (по 5-15 на курс → ~5000)
# ============================================================


lectures = []
lecture_types = ['lecture', 'practice', 'lab']
for course in lecture_courses[:500]:
    lecture_count = random.randint(5, 15)
    for order in range(1, lecture_count + 1):
        lectures.append({
            'id': str(uuid4()),
            'course_id': course['id'],
            'title': fake.sentence(nb_words=3)[:-1],
            'annotation': fake.text(max_nb_chars=200),
            'lecture_type': random.choice(lecture_types),
            'order_number': order,
            'duration_minutes': random.choice([45, 90, 90, 90, 120]),
            'requires_computers': random.choice([True, False, False])
        })

cur.executemany("""
    INSERT INTO lectures (id, course_id, title, annotation, lecture_type, 
                          order_number, duration_minutes, requires_computers)
    VALUES (%(id)s, %(course_id)s, %(title)s, %(annotation)s, %(lecture_type)s,
            %(order_number)s, %(duration_minutes)s, %(requires_computers)s)
""", lectures)
print(f"✓ Добавлено {len(lectures)} лекций")


# ============================================================
# 8. Генерация материалов лекций (по 0-3 на лекцию)
# ============================================================


import json

materials = []
content_types = ['text', 'text', 'presentation', 'pdf', 'video_link']
for lecture in lectures[:2000]:
    material_count = random.randint(0, 3)
    for _ in range(material_count):
        # Преобразуем словарь metadata в JSON-строку
        metadata_dict = {'author': fake.name(), 'created': fake.date_time().isoformat()}
        metadata_json = json.dumps(metadata_dict)
        
        materials.append({
            'id': str(uuid4()),
            'lecture_id': lecture['id'],
            'content_type': random.choice(content_types),
            'title': fake.sentence(nb_words=4)[:-1],
            'content_text': fake.text(max_nb_chars=2000) if random.choice([True, False]) else None,
            'file_url': fake.url() if random.choice([True, False]) else None,
            'metadata': metadata_json  # ← теперь это строка JSON
        })

cur.executemany("""
    INSERT INTO lecture_materials (id, lecture_id, content_type, title, content_text, file_url, metadata)
    VALUES (%(id)s, %(lecture_id)s, %(content_type)s, %(title)s, %(content_text)s, %(file_url)s, %(metadata)s::jsonb)
""", materials)
print(f"✓ Добавлено {len(materials)} материалов лекций")


# ============================================================
# 9. Генерация групп студентов (50-100)
# ============================================================


groups = []
enrollment_years = [2021, 2022, 2023, 2024, 2025]
used_names = set()

for spec in random.sample(specialties, min(80, len(specialties))):
    year = random.choice(enrollment_years)
    
    while True:
        group_name = f"{fake.bothify(text='??', letters='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')}-{year % 100}"
        if group_name not in used_names:
            used_names.add(group_name)
            break
    
    groups.append({
        'id': str(uuid4()),
        'specialty_id': spec['id'],
        'name': group_name,
        'enrollment_year': year,
        'curator': fake.name()
    })

if len(groups) > 100:
    groups = groups[:100]

cur.executemany("""
    INSERT INTO student_groups (id, specialty_id, name, enrollment_year, curator)
    VALUES (%(id)s, %(specialty_id)s, %(name)s, %(enrollment_year)s, %(curator)s)
""", groups)
print(f"✓ Добавлено {len(groups)} групп")


# ============================================================
# 10. Генерация студентов (1000)
# ============================================================


students = []
statuses = ['active', 'active', 'active', 'academic_leave', 'expelled', 'graduated']
used_emails = set()
used_card_numbers = set()

for i in range(1000):
    group = random.choice(groups)
    
    while True:
        email = fake.email()
        if email not in used_emails:
            used_emails.add(email)
            break
    
    while True:
        card_number = f"{fake.random_number(digits=7)}"
        if card_number not in used_card_numbers:
            used_card_numbers.add(card_number)
            break
    
    students.append({
        'id': str(uuid4()),
        'group_id': group['id'],
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'patronymic': fake.middle_name(),
        'email': email,
        'phone': fake.phone_number(),
        'student_card_number': card_number,
        'enrollment_date': fake.date_between(start_date='-5y', end_date='today'),
        'status': random.choice(statuses)
    })

cur.executemany("""
    INSERT INTO students (id, group_id, first_name, last_name, patronymic, 
                          email, phone, student_card_number, enrollment_date, status)
    VALUES (%(id)s, %(group_id)s, %(first_name)s, %(last_name)s, %(patronymic)s,
            %(email)s, %(phone)s, %(student_card_number)s, %(enrollment_date)s, %(status)s)
""", students)
print(f"✓ Добавлено {len(students)} студентов")


# ============================================================
# 11. Генерация расписания (1000 записей)
# ============================================================


print("Создание партиций на семестр...")

cur.execute("SELECT create_weekly_partitions('2026-02-09', 20);")
conn.commit()
print("✓ Партиции созданы")

schedules = []
start_date = datetime(2026, 2, 9)
max_week = 16

for i in range(1000):
    group = random.choice(groups)
    lecture = random.choice(lectures[:3000])
    week = random.randint(0, max_week)
    schedule_date = start_date + timedelta(days=week * 7 + random.randint(0, 6))
    week_start = schedule_date - timedelta(days=schedule_date.weekday())
    
    schedules.append({
        'id': str(uuid4()),
        'lecture_id': lecture['id'],
        'group_id': group['id'],
        'scheduled_date': schedule_date.date(),
        'week_start_date': week_start.date(),
        'start_time': '10:00:00',
        'end_time': '11:30:00',
        'teacher_name': fake.name(),
        'status': random.choice(['scheduled', 'completed', 'cancelled'])
    })

cur.executemany("""
    INSERT INTO schedule (id, lecture_id, group_id, scheduled_date, week_start_date, 
                          start_time, end_time, teacher_name, status)
    VALUES (%(id)s, %(lecture_id)s, %(group_id)s, %(scheduled_date)s, %(week_start_date)s,
            %(start_time)s, %(end_time)s, %(teacher_name)s, %(status)s)
""", schedules)
print(f"✓ Добавлено {len(schedules)} записей расписания")


# ============================================================
# 12. Генерация посещаемости
# ============================================================


attendances = []
for schedule in schedules:
    group_students = [s for s in students if s['group_id'] == schedule['group_id']]
    if group_students:
        sample_size = random.randint(int(len(group_students) * 0.5), len(group_students))
        for student in random.sample(group_students, sample_size):
            attendances.append({
                'id': str(uuid4()),
                'schedule_id': schedule['id'],
                'student_id': student['id'],
                'week_start_date': schedule['week_start_date'],
                'is_present': random.choice([True, True, True, False]),
                'marked_at': datetime.now(),
                'marked_by': fake.name(),
                'note': fake.sentence() if random.random() < 0.1 else None
            })

cur.executemany("""
    INSERT INTO attendance (id, schedule_id, student_id, week_start_date, is_present, marked_at, marked_by, note)
    VALUES (%(id)s, %(schedule_id)s, %(student_id)s, %(week_start_date)s, %(is_present)s, 
            %(marked_at)s, %(marked_by)s, %(note)s)
""", attendances)
print(f"✓ Добавлено {len(attendances)} записей посещаемости")


# ============================================================
# Фиксация изменений и закрытие соединения
# ============================================================


conn.commit()
cur.close()
conn.close()

print("\n" + "=" * 60)
print("ГЕНЕРАЦИЯ ДАННЫХ ЗАВЕРШЕНА УСПЕШНО!")
print("=" * 60)

print("\n📊 СТАТИСТИКА СГЕНЕРИРОВАННЫХ ДАННЫХ:")
print(f"  • Университетов: {len(universities)}")
print(f"  • Институтов: {len(institutes)}")
print(f"  • Кафедр: {len(departments[:1000])}")
print(f"  • Специальностей: {len(specialties)}")
print(f"  • Связей кафедра-специальность: {len(department_specialties[:2000])}")
print(f"  • Курсов лекций: {len(lecture_courses)}")
print(f"  • Лекций: {len(lectures)}")
print(f"  • Материалов лекций: {len(materials)}")
print(f"  • Групп: {len(groups)}")
print(f"  • Студентов: {len(students)}")
print(f"  • Записей расписания: {len(schedules)}")
print(f"  • Записей посещаемости: {len(attendances)}")


redis_sync.main()


mongodb_sync.main()


neo4j_sync.main()


elastic_sync.main()
