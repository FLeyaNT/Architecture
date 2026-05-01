
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

-- ============================================================
-- 7. Партиции на весенний семестр 2026
-- ============================================================

CREATE TABLE attendance_w2026_02_09 PARTITION OF attendance
    FOR VALUES FROM ('2026-02-09') TO ('2026-02-16');

CREATE TABLE attendance_w2026_02_16 PARTITION OF attendance
    FOR VALUES FROM ('2026-02-16') TO ('2026-02-23');

CREATE TABLE attendance_w2026_02_23 PARTITION OF attendance
    FOR VALUES FROM ('2026-02-23') TO ('2026-03-02');

CREATE TABLE attendance_w2026_03_02 PARTITION OF attendance
    FOR VALUES FROM ('2026-03-02') TO ('2026-03-09');

CREATE TABLE attendance_w2026_03_09 PARTITION OF attendance
    FOR VALUES FROM ('2026-03-09') TO ('2026-03-16');

CREATE TABLE attendance_w2026_03_16 PARTITION OF attendance
    FOR VALUES FROM ('2026-03-16') TO ('2026-03-23');

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