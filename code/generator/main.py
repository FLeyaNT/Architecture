import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta
from uuid import uuid4
import json
from collections import defaultdict

# Импорт модулей синхронизации (предполагается, что они есть)
import redis_sync
import neo4j_sync
import mongodb_sync
import elastic_sync

fake = Faker('ru_RU')

# ============================================================
# Параметры генерации
# ============================================================
SPECIALTIES_COUNT = 10
GROUPS_PER_SPECIALTY = 3
STUDENTS_PER_GROUP = 20
SEMESTERS = [1, 2, 3, 4]
COURSES_PER_SPECIALTY_PER_SEMESTER = 3
LECTURES_PER_COURSE = 6

# ============================================================
# DDL создания таблиц (полный скрипт, как ранее)
# ============================================================
DDL_SCRIPT = """

-- Включение расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- 2. Основные справочники
-- ============================================================

-- Университет
CREATE TABLE universities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    short_name VARCHAR(100),
    address TEXT,
    website VARCHAR(255),
    founded_year INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Институт
CREATE TABLE institutes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    university_id UUID NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    short_name VARCHAR(100),
    dean VARCHAR(300),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_institutes_university ON institutes(university_id);

-- Кафедра
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institute_id UUID NOT NULL REFERENCES institutes(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    short_name VARCHAR(100),
    head VARCHAR(300),
    room VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_departments_institute ON departments(institute_id);

-- Специальность
CREATE TABLE specialties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    code VARCHAR(20) NOT NULL,
    degree_level VARCHAR(20) NOT NULL CHECK (degree_level IN ('bachelor', 'master', 'specialist')),
    duration_years INT NOT NULL DEFAULT 4,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_specialties_code ON specialties(code);

-- Связь кафедра <-> специальность (M:N)
CREATE TABLE department_specialties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    specialty_id UUID NOT NULL REFERENCES specialties(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (department_id, specialty_id)
);
CREATE INDEX idx_dept_spec_department ON department_specialties(department_id);
CREATE INDEX idx_dept_spec_specialty ON department_specialties(specialty_id);

-- ============================================================
-- 3. Учебные курсы и лекции
-- ============================================================

-- Курс лекций (учебная дисциплина)
CREATE TABLE lecture_courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specialty_id UUID NOT NULL REFERENCES specialties(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    semester INT NOT NULL CHECK (semester BETWEEN 1 AND 12),
    total_hours INT NOT NULL,
    lecture_hours INT DEFAULT 0,
    practice_hours INT DEFAULT 0,
    lab_hours INT DEFAULT 0,
    is_specialty_discipline BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_courses_specialty ON lecture_courses(specialty_id);

-- Лекция (отдельное занятие)
CREATE TABLE lectures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID NOT NULL REFERENCES lecture_courses(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    annotation TEXT,
    lecture_type VARCHAR(20) NOT NULL CHECK (lecture_type IN ('lecture', 'practice', 'lab')),
    order_number INT NOT NULL,
    duration_minutes INT DEFAULT 90,
    requires_computers BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_lectures_course ON lectures(course_id);
CREATE INDEX idx_lectures_type ON lectures(lecture_type);

-- Материалы лекций (с полнотекстовым поиском)
CREATE TABLE lecture_materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lecture_id UUID NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL CHECK (content_type IN ('text', 'presentation', 'pdf', 'video_link')),
    title VARCHAR(500),
    content_text TEXT,
    file_url VARCHAR(1000),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_materials_lecture ON lecture_materials(lecture_id);
CREATE INDEX idx_materials_type ON lecture_materials(content_type);
CREATE INDEX idx_materials_fts ON lecture_materials USING GIN (to_tsvector('russian', COALESCE(content_text, '')));

-- ============================================================
-- 4. Студенты и группы
-- ============================================================

-- Группа студентов
CREATE TABLE student_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specialty_id UUID NOT NULL REFERENCES specialties(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL UNIQUE,
    enrollment_year INT NOT NULL,
    curator VARCHAR(300),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_groups_specialty ON student_groups(specialty_id);

-- Студент
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID NOT NULL REFERENCES student_groups(id) ON DELETE CASCADE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    patronymic VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    student_card_number VARCHAR(20) UNIQUE,
    enrollment_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'academic_leave', 'expelled', 'graduated')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_students_group ON students(group_id);
CREATE INDEX idx_students_name ON students(last_name, first_name);
CREATE INDEX idx_students_status ON students(status);

-- ============================================================
-- 5. Расписание занятий
-- ============================================================

CREATE TABLE schedule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lecture_id UUID NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    group_id UUID NOT NULL REFERENCES student_groups(id) ON DELETE CASCADE,
    scheduled_date DATE NOT NULL,
    week_start_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    classroom VARCHAR(50),
    teacher_name VARCHAR(300),
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_schedule_date ON schedule(scheduled_date);
CREATE INDEX idx_schedule_week ON schedule(week_start_date);
CREATE INDEX idx_schedule_group ON schedule(group_id);
CREATE INDEX idx_schedule_lecture ON schedule(lecture_id);
CREATE INDEX idx_schedule_group_date ON schedule(group_id, scheduled_date);

-- ============================================================
-- 6. Журнал посещений (партицированная таблица)
-- ============================================================

CREATE TABLE attendance (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
    schedule_id UUID NOT NULL REFERENCES schedule(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    week_start_date DATE NOT NULL,
    is_present BOOLEAN NOT NULL DEFAULT FALSE,
    marked_at TIMESTAMP DEFAULT NOW(),
    marked_by VARCHAR(300),
    note VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (id, week_start_date)
) PARTITION BY RANGE (week_start_date);

-- Уникальное ограничение: один студент на одно занятие
CREATE UNIQUE INDEX uq_attendance_schedule_student ON attendance(schedule_id, student_id, week_start_date);

-- Индексы
CREATE INDEX idx_attendance_schedule ON attendance(schedule_id);
CREATE INDEX idx_attendance_student ON attendance(student_id);
CREATE INDEX idx_attendance_present ON attendance(is_present);
CREATE INDEX idx_attendance_week ON attendance(week_start_date);
CREATE INDEX IF NOT EXISTS idx_attendance_composite ON attendance (student_id, schedule_id);

-- ============================================================
-- 7. Партиции по семестрам (вместо недель)
-- ============================================================

-- 2024 год
CREATE TABLE attendance_2024_summer PARTITION OF attendance
    FOR VALUES FROM ('2024-06-01') TO ('2024-09-01');

CREATE TABLE attendance_2024_autumn PARTITION OF attendance
    FOR VALUES FROM ('2024-09-02') TO ('2025-01-01');

-- 2025 год
CREATE TABLE attendance_2025_spring PARTITION OF attendance
    FOR VALUES FROM ('2025-01-02') TO ('2025-07-01');

CREATE TABLE attendance_2025_autumn PARTITION OF attendance
    FOR VALUES FROM ('2025-07-02') TO ('2026-01-01');

-- 2026 год
CREATE TABLE attendance_2026_spring PARTITION OF attendance
    FOR VALUES FROM ('2026-01-02') TO ('2026-07-01');

CREATE TABLE attendance_2026_autumn PARTITION OF attendance
    FOR VALUES FROM ('2026-07-02') TO ('2027-01-01');

-- 2027 год
CREATE TABLE attendance_2027_spring PARTITION OF attendance
    FOR VALUES FROM ('2027-01-02') TO ('2027-07-01');

CREATE TABLE attendance_2027_summer PARTITION OF attendance
    FOR VALUES FROM ('2027-07-02') TO ('2027-09-01');

-- ============================================================
-- 8. Функция автоматического создания партиций
-- ============================================================

CREATE OR REPLACE FUNCTION create_weekly_partitions(
    start_date DATE,
    num_weeks INT
) RETURNS VOID AS $$
DECLARE
    week_start DATE := date_trunc('week', start_date)::DATE;
    week_end DATE;
    partition_name TEXT;
BEGIN
    FOR i IN 0..num_weeks-1 LOOP
        week_end := week_start + INTERVAL '7 days';
        partition_name := 'attendance_w' || to_char(week_start, 'YYYY_MM_DD');
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = partition_name) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF attendance FOR VALUES FROM (%L) TO (%L)',
                partition_name, week_start, week_end
            );
            RAISE NOTICE 'Created partition: %', partition_name;
        END IF;
        week_start := week_end;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 9. Комментарии к структуре
-- ============================================================

COMMENT ON TABLE attendance IS 'Журнал посещений, партицирован по week_start_date.';
COMMENT ON COLUMN lecture_courses.is_specialty_discipline IS 'Тег «специальная дисциплина кафедры» для лабораторной №3.';
COMMENT ON COLUMN lectures.requires_computers IS 'Флаг: нужны ли компьютеры на занятии. Для лабораторной №2.';
COMMENT ON INDEX idx_materials_fts IS 'GIN-индекс для полнотекстового поиска по текстам материалов лекций (лабораторная №1).';
"""

# ============================================================
# Подключение к PostgreSQL
# ============================================================
conn = psycopg2.connect(
    host='localhost',
    port=5433,
    database='university_system',
    user='postgres',
    password='postgres'
)
cur = conn.cursor()

# ============================================================
# Быстрая очистка (DROP SCHEMA)
# ============================================================
print("=" * 60)
print("ПЕРЕСОЗДАНИЕ СХЕМЫ public")
print("=" * 60)
cur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
cur.execute("CREATE SCHEMA public;")
cur.execute("GRANT ALL ON SCHEMA public TO postgres;")
cur.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
cur.execute("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\";")
conn.commit()
print("✓ Схема public пересоздана, расширения установлены")

# ============================================================
# Создание таблиц
# ============================================================
print("Создание таблиц...")
cur.execute(DDL_SCRIPT)
conn.commit()
print("✓ Таблицы созданы")

# ============================================================
# Список аудиторий
# ============================================================
classrooms = [
    'Г-217', 'Г-218', 'Г-301', 'Г-302', 'Г-401',
    'А-408', 'А-409', 'А-410', 'А-501', 'А-502',
    'Б-201', 'Б-202', 'Б-203', 'Б-204', 'Б-205',
    'В-301', 'В-302', 'В-303', 'В-304', 'В-305',
    'Д-101', 'Д-102', 'Д-103', 'Д-104', 'Д-105'
]

# ============================================================
# 1. Университеты (3)
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
# 2. Институты (~20)
# ============================================================
institutes = []
for univ in universities:
    for _ in range(random.randint(5, 10)):
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
# 3. Кафедры (до 200)
# ============================================================
departments = []
for inst in institutes[:20]:
    for _ in range(random.randint(3, 6)):
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
""", departments[:200])
print(f"✓ Добавлено {len(departments[:200])} кафедр")

# ============================================================
# 4. Специальности (SPECIALTIES_COUNT)
# ============================================================
specialties = []
degree_levels = ['bachelor', 'master', 'specialist']
for i in range(SPECIALTIES_COUNT):
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
# 5. Связь кафедр и специальностей (упрощённо)
# ============================================================
department_specialties = []
for dept in departments[:150]:
    for spec in random.sample(specialties, random.randint(1, 4)):
        department_specialties.append({
            'id': str(uuid4()),
            'department_id': dept['id'],
            'specialty_id': spec['id'],
            'is_primary': random.choice([True, False])
        })
cur.executemany("""
    INSERT INTO department_specialties (id, department_id, specialty_id, is_primary)
    VALUES (%(id)s, %(department_id)s, %(specialty_id)s, %(is_primary)s)
""", department_specialties[:1000])
print(f"✓ Добавлено {min(1000, len(department_specialties))} связей")

# ============================================================
# 6. Генерация курсов лекций (для всех семестров)
# ============================================================
# ============================================================
# 6. Генерация курсов лекций (для всех семестров) с реальными часами
# ============================================================
lecture_courses = []
for sem in SEMESTERS:
    for spec in specialties:
        for _ in range(COURSES_PER_SPECIALTY_PER_SEMESTER):
            # Количество лекций фиксировано = LECTURES_PER_COURSE
            lecture_count = LECTURES_PER_COURSE
            # 1 лекция = 2 академических часа
            lecture_hours_total = lecture_count * 2
            # Практические и лабораторные часы – случайные, но не более половины от лекционных
            practice_hours_total = random.randint(0, lecture_hours_total // 2)
            lab_hours_total = random.randint(0, lecture_hours_total // 2)
            total_hours = lecture_hours_total + practice_hours_total + lab_hours_total
            
            lecture_courses.append({
                'id': str(uuid4()),
                'specialty_id': spec['id'],
                'name': f"{fake.catch_phrase()}",
                'description': fake.text(max_nb_chars=500),
                'semester': sem,
                'total_hours': total_hours,
                'lecture_hours': lecture_hours_total,
                'practice_hours': practice_hours_total,
                'lab_hours': lab_hours_total,
                'is_specialty_discipline': random.choice([True, False])
            })
cur.executemany("""
    INSERT INTO lecture_courses (id, specialty_id, name, description, semester, 
                                 total_hours, lecture_hours, practice_hours, lab_hours, is_specialty_discipline)
    VALUES (%(id)s, %(specialty_id)s, %(name)s, %(description)s, %(semester)s,
            %(total_hours)s, %(lecture_hours)s, %(practice_hours)s, %(lab_hours)s, %(is_specialty_discipline)s)
""", lecture_courses)
print(f"✓ Добавлено {len(lecture_courses)} курсов лекций (с реальными часами)")

# ============================================================
# 7. Генерация лекций (ровно LECTURES_PER_COURSE на курс)
# ============================================================
lectures = []
lecture_types = ['lecture', 'practice', 'lab']
for course in lecture_courses:
    for order in range(1, LECTURES_PER_COURSE + 1):
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
print(f"✓ Добавлено {len(lectures)} лекций (по {LECTURES_PER_COURSE} на курс)")

# ============================================================
# 8. Генерация материалов лекций (каждая лекция имеет 1 материал)
# ============================================================
popular_terms = ['реклама', 'нейронные сети', 'SQL']
materials = []
content_types = ['text', 'text', 'presentation', 'pdf', 'video_link']
for lecture in lectures:
    base_text = fake.text(max_nb_chars=2000)
    if random.random() < 0.8:
        term = random.choice(popular_terms)
        words = base_text.split()
        if len(words) > 10:
            pos = random.randint(0, len(words)-1)
            words.insert(pos, term)
            base_text = ' '.join(words)
    metadata_json = json.dumps({'author': fake.name(), 'created': fake.date_time().isoformat()})
    materials.append({
        'id': str(uuid4()),
        'lecture_id': lecture['id'],
        'content_type': random.choice(content_types),
        'title': fake.sentence(nb_words=4)[:-1],
        'content_text': base_text,
        'file_url': fake.url() if random.random() > 0.5 else None,
        'metadata': metadata_json
    })
cur.executemany("""
    INSERT INTO lecture_materials (id, lecture_id, content_type, title, content_text, file_url, metadata)
    VALUES (%(id)s, %(lecture_id)s, %(content_type)s, %(title)s, %(content_text)s, %(file_url)s, %(metadata)s::jsonb)
""", materials)
print(f"✓ Добавлено {len(materials)} материалов лекций (каждая лекция имеет материал)")

# ============================================================
# 9. Генерация групп студентов (с разными годами поступления)
# ============================================================
enrollment_years = [2025, 2024]
groups = []
used_names = set()
for spec in specialties:
    for year in enrollment_years:
        for group_idx in range(GROUPS_PER_SPECIALTY):
            while True:
                group_name = f"{fake.bothify(text='??', letters='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')}-{year % 100}-{group_idx}"
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
cur.executemany("""
    INSERT INTO student_groups (id, specialty_id, name, enrollment_year, curator)
    VALUES (%(id)s, %(specialty_id)s, %(name)s, %(enrollment_year)s, %(curator)s)
""", groups)
print(f"✓ Добавлено {len(groups)} групп (по {GROUPS_PER_SPECIALTY} на специальность)")

# ============================================================
# 10. Генерация студентов (по STUDENTS_PER_GROUP на группу)
# ============================================================
students = []
statuses = ['active', 'active', 'active', 'academic_leave', 'expelled', 'graduated']
used_emails = set()
used_card_numbers = set()

for group in groups:
    for _ in range(STUDENTS_PER_GROUP):
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
            'enrollment_date': datetime(group['enrollment_year'], 9, 1).date(),
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
# 11. Генерация расписания (с учётом года поступления группы)
# ============================================================
# Функция для получения дат семестра в зависимости от года поступления
def get_semester_dates_for_group(enrollment_year, semester):
    """
    Возвращает (start_date, end_date) для заданного семестра (1..4)
    и года поступления группы.
    Для enrollment_year = 2025:
        семестр 1: осень 2025 (2025-09-01 – 2025-12-31)
        семестр 2: весна 2026 (2026-02-01 – 2026-06-30)
        семестр 3: осень 2026 (2026-09-01 – 2026-12-31)
        семестр 4: весна 2027 (2027-02-01 – 2027-06-30)
    Для enrollment_year = 2024:
        семестр 1: осень 2024 (2024-09-01 – 2024-12-31)
        семестр 2: весна 2025 (2025-02-01 – 2025-06-30)
        семестр 3: осень 2025 (2025-09-01 – 2025-12-31)
        семестр 4: весна 2026 (2026-02-01 – 2026-06-30)
    """
    if semester == 1:
        start = datetime(enrollment_year, 9, 1).date()
        end = datetime(enrollment_year, 12, 31).date()
    elif semester == 2:
        start = datetime(enrollment_year + 1, 2, 1).date()
        end = datetime(enrollment_year + 1, 6, 30).date()
    elif semester == 3:
        start = datetime(enrollment_year + 1, 9, 1).date()
        end = datetime(enrollment_year + 1, 12, 31).date()
    elif semester == 4:
        start = datetime(enrollment_year + 2, 2, 1).date()
        end = datetime(enrollment_year + 2, 6, 30).date()
    else:
        raise ValueError("Semester must be 1-4")
    return start, end

# Индексы для быстрого поиска
courses_by_specialty_and_semester = defaultdict(list)
for course in lecture_courses:
    courses_by_specialty_and_semester[(course['specialty_id'], course['semester'])].append(course)

lectures_by_course = defaultdict(list)
for lect in lectures:
    lectures_by_course[lect['course_id']].append(lect)

all_schedules = []

for group in groups:
    for sem in SEMESTERS:
        # Курсы для специальности группы и данного семестра
        group_courses = courses_by_specialty_and_semester.get((group['specialty_id'], sem), [])
        if not group_courses:
            continue
        start_date, end_date = get_semester_dates_for_group(group['enrollment_year'], sem)
        for course in group_courses:
            course_lectures = lectures_by_course.get(course['id'], [])
            for lecture in course_lectures:
                delta = (end_date - start_date).days
                if delta <= 0:
                    continue
                random_days = random.randint(0, delta)
                scheduled_date = start_date + timedelta(days=random_days)
                week_start = scheduled_date - timedelta(days=scheduled_date.weekday())
                all_schedules.append({
                    'id': str(uuid4()),
                    'lecture_id': lecture['id'],
                    'group_id': group['id'],
                    'scheduled_date': scheduled_date,
                    'week_start_date': week_start,
                    'start_time': f"{random.randint(9, 17)}:{random.choice(['00', '30'])}:00",
                    'end_time': f"{random.randint(10, 18)}:{random.choice(['00', '30'])}:00",
                    'classroom': random.choice(classrooms),
                    'teacher_name': fake.name(),
                    'status': random.choice(['scheduled', 'completed', 'cancelled'])
                })

print(f"Сгенерировано записей расписания: {len(all_schedules)}")
if all_schedules:
    cur.executemany("""
        INSERT INTO schedule (id, lecture_id, group_id, scheduled_date, week_start_date, 
                              start_time, end_time, classroom, teacher_name, status)
        VALUES (%(id)s, %(lecture_id)s, %(group_id)s, %(scheduled_date)s, %(week_start_date)s,
                %(start_time)s, %(end_time)s, %(classroom)s, %(teacher_name)s, %(status)s)
    """, all_schedules)
    print(f"✓ Добавлено {len(all_schedules)} записей расписания")

# ============================================================
# 12. Генерация посещаемости (пакетами)
# ============================================================
print("Начинаем генерацию посещаемости...")
total_attendance = 0
batch_size = 5000
batch = []

for schedule in all_schedules:
    group_students = [s for s in students if s['group_id'] == schedule['group_id']]
    if group_students:
        for student in group_students:
            is_present = random.choice([True, True, True, False])   # 75%
            batch.append({
                'id': str(uuid4()),
                'schedule_id': schedule['id'],
                'student_id': student['id'],
                'week_start_date': schedule['week_start_date'],
                'is_present': is_present,
                'marked_at': datetime.now(),
                'marked_by': fake.name(),
                'note': fake.sentence() if random.random() < 0.1 else None
            })
            total_attendance += 1
            if len(batch) >= batch_size:
                cur.executemany("""
                    INSERT INTO attendance (id, schedule_id, student_id, week_start_date, is_present, marked_at, marked_by, note)
                    VALUES (%(id)s, %(schedule_id)s, %(student_id)s, %(week_start_date)s, %(is_present)s, 
                            %(marked_at)s, %(marked_by)s, %(note)s)
                """, batch)
                conn.commit()
                print(f"  Вставлено {total_attendance} записей...")
                batch.clear()

if batch:
    cur.executemany("""
        INSERT INTO attendance (id, schedule_id, student_id, week_start_date, is_present, marked_at, marked_by, note)
        VALUES (%(id)s, %(schedule_id)s, %(student_id)s, %(week_start_date)s, %(is_present)s, 
                %(marked_at)s, %(marked_by)s, %(note)s)
    """, batch)
    conn.commit()

print(f"✓ Добавлено {total_attendance} записей посещаемости")

# ============================================================
# Фиксация и синхронизация
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
print(f"  • Кафедр: {len(departments[:200])}")
print(f"  • Специальностей: {len(specialties)}")
print(f"  • Курсов лекций: {len(lecture_courses)}")
print(f"  • Лекций: {len(lectures)}")
print(f"  • Материалов лекций: {len(materials)}")
print(f"  • Групп: {len(groups)}")
print(f"  • Студентов: {len(students)}")
print(f"  • Записей расписания: {len(all_schedules)}")
print(f"  • Записей посещаемости: {total_attendance}")

# Синхронизация с другими хранилищами
print("\n" + "=" * 60)
print("СИНХРОНИЗАЦИЯ С ДРУГИМИ ХРАНИЛИЩАМИ")
print("=" * 60)

redis_sync.main()
mongodb_sync.main()
neo4j_sync.main()
elastic_sync.main()