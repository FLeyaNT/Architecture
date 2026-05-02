import psycopg2
from neo4j import GraphDatabase
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# ============================================================
# Подключение к PostgreSQL
# ============================================================


pg_conn = psycopg2.connect(
    host='localhost',
    port=5433,
    database='university_system',
    user='postgres',
    password='postgres'
)
pg_cur = pg_conn.cursor()


# ============================================================
# Подключение к Neo4j
# ============================================================


class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def execute_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return list(result)

neo4j_conn = Neo4jConnection(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)


# ============================================================
# Функции-помощники
# ============================================================


def uuid_to_str(uuid_value):
    if isinstance(uuid_value, UUID):
        return str(uuid_value)
    return uuid_value

def convert_decimal(value):
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        else:
            return float(value)
    return value

def clear_neo4j():
    query = "MATCH (n) DETACH DELETE n"
    neo4j_conn.execute_query(query)
    print("✓ База данных Neo4j очищена")


# ============================================================
# 1. Синхронизация групп (student_groups)
# ============================================================


def sync_groups():
    query = """
        SELECT id, name, enrollment_year
        FROM student_groups
        ORDER BY name
    """
    pg_cur.execute(query)
    groups = pg_cur.fetchall()
    
    count = 0
    for group in groups:
        group_id = uuid_to_str(group[0])
        group_name = group[1]
        enrollment_year = convert_decimal(group[2])
        
        neo4j_query = """
            MERGE (g:Group {id: $id})
            SET g.name = $name,
                g.enrollment_year = $enrollment_year
        """
        neo4j_conn.execute_query(neo4j_query, {
            'id': group_id,
            'name': group_name,
            'enrollment_year': enrollment_year
        })
        count += 1
    
    print(f"  ✓ Синхронизировано {count} групп")
    return count


# ============================================================
# 2. Синхронизация студентов
# ============================================================


def sync_students():
    query = """
        SELECT 
            s.id,
            s.last_name,
            s.first_name,
            s.patronymic,
            s.student_card_number,
            s.email,
            s.enrollment_date,
            g.id as group_id
        FROM students s
        JOIN student_groups g ON s.group_id = g.id
        ORDER BY s.last_name
    """
    pg_cur.execute(query)
    students = pg_cur.fetchall()
    
    count = 0
    for student in students:
        student_id = uuid_to_str(student[0])
        last_name = student[1]
        first_name = student[2]
        patronymic = student[3] or ""
        student_card_number = student[4]
        email = student[5]
        
        full_name = f"{last_name} {first_name} {patronymic}".strip()
        
        neo4j_query = """
            MERGE (s:Student {id: $id})
            SET s.name = $name,
                s.student_card_number = $student_card_number,
                s.email = $email
        """
        neo4j_conn.execute_query(neo4j_query, {
            'id': student_id,
            'name': full_name,
            'student_card_number': student_card_number,
            'email': email
        })
        count += 1
    
    print(f"  ✓ Синхронизировано {count} студентов")
    return count


# ============================================================
# 3. Синхронизация лекций
# ============================================================


def sync_lectures():
    query = """
        SELECT 
            l.id,
            l.title,
            l.duration_minutes,
            lc.name as course_name,
            lc.is_specialty_discipline,
            sch.scheduled_date
        FROM lectures l
        JOIN lecture_courses lc ON l.course_id = lc.id
        LEFT JOIN schedule sch ON sch.lecture_id = l.id
        WHERE sch.scheduled_date IS NOT NULL
    """
    pg_cur.execute(query)
    lectures = pg_cur.fetchall()
    
    count = 0
    processed = set()
    
    for lecture in lectures:
        lecture_id = uuid_to_str(lecture[0])
        
        if lecture_id in processed:
            continue
        processed.add(lecture_id)
        
        title = lecture[1] or "Без названия"
        duration_minutes = convert_decimal(lecture[2]) if lecture[2] else 90
        course_name = lecture[3]
        is_specialty_discipline = lecture[4] or False
        scheduled_date = lecture[5]
        
        if scheduled_date:
            date_str = scheduled_date.isoformat()
            start_date = datetime(2026, 2, 9).date()
            delta_days = (scheduled_date - start_date).days
            week_number = (delta_days // 7) + 1 if delta_days >= 0 else 1
            week_number = min(week_number, 16)
        else:
            date_str = "2026-02-09"
            week_number = 1
        
        neo4j_query = """
            MERGE (l:Lecture {id: $id})
            SET l.title = $title,
                l.course_name = $course_name,
                l.date = $date,
                l.week_number = $week_number,
                l.duration_minutes = $duration,
                l.is_specialty_discipline = $is_specialty
        """
        neo4j_conn.execute_query(neo4j_query, {
            'id': lecture_id,
            'title': title,
            'course_name': course_name,
            'date': date_str,
            'week_number': week_number,
            'duration': duration_minutes,
            'is_specialty': is_specialty_discipline
        })
        count += 1
        
        if count % 500 == 0:
            print(f"     Прогресс: {count} лекций синхронизировано...")
    
    print(f"  ✓ Синхронизировано {count} лекций")
    return count


# ============================================================
# 4. Создание связей ENROLLED_IN (Student → Group)
# ============================================================


def create_enrolled_in_relationships():
    query = """
        SELECT 
            s.id as student_id,
            g.id as group_id,
            s.enrollment_date
        FROM students s
        JOIN student_groups g ON s.group_id = g.id
        WHERE s.status = 'active'
    """
    pg_cur.execute(query)
    relationships = pg_cur.fetchall()
    
    count = 0
    for rel in relationships:
        student_id = uuid_to_str(rel[0])
        group_id = uuid_to_str(rel[1])
        enrollment_date = rel[2]
        enrollment_year = enrollment_date.year if enrollment_date else 2023
        
        neo4j_query = """
            MATCH (s:Student {id: $student_id})
            MATCH (g:Group {id: $group_id})
            MERGE (s)-[r:ENROLLED_IN]->(g)
            SET r.enrollment_year = $enrollment_year
        """
        neo4j_conn.execute_query(neo4j_query, {
            'student_id': student_id,
            'group_id': group_id,
            'enrollment_year': enrollment_year
        })
        count += 1
        
        if count % 500 == 0:
            print(f"     Прогресс: {count} связей ENROLLED_IN создано...")
    
    print(f"  ✓ Создано {count} связей ENROLLED_IN")
    return count


# ============================================================
# 5. Создание связей HAS_LECTURE (Group → Lecture) - расписание
# ============================================================


def create_has_lecture_relationships():
    query = """
        SELECT 
            sch.group_id,
            sch.lecture_id,
            sch.teacher_name
        FROM schedule sch
        WHERE sch.status != 'cancelled'
    """
    pg_cur.execute(query)
    schedules = pg_cur.fetchall()
    
    count = 0
    for schedule in schedules:
        group_id = uuid_to_str(schedule[0])
        lecture_id = uuid_to_str(schedule[1])
        teacher_name = schedule[2] or "Не указан"
        
        neo4j_query = """
            MATCH (g:Group {id: $group_id})
            MATCH (l:Lecture {id: $lecture_id})
            MERGE (g)-[r:HAS_LECTURE]->(l)
            SET r.teacher = $teacher,
                r.classroom = "Не указана"
        """
        neo4j_conn.execute_query(neo4j_query, {
            'group_id': group_id,
            'lecture_id': lecture_id,
            'teacher': teacher_name
        })
        count += 1
        
        if count % 500 == 0:
            print(f"     Прогресс: {count} связей HAS_LECTURE создано...")
    
    print(f"  ✓ Создано {count} связей HAS_LECTURE")
    return count


# ============================================================
# 6. Создание связей ATTENDED (Student → Lecture) - посещаемость
# ============================================================


def create_attended_relationships():
    query = """
        SELECT 
            att.student_id,
            sch.lecture_id,
            att.is_present,
            att.marked_at,
            att.marked_by
        FROM attendance att
        JOIN schedule sch ON att.schedule_id = sch.id
        WHERE att.is_present IS NOT NULL
    """
    pg_cur.execute(query)
    attendances = pg_cur.fetchall()
    
    count = 0
    for att in attendances:
        student_id = uuid_to_str(att[0])
        lecture_id = uuid_to_str(att[1])
        is_present = att[2]
        marked_at = att[3].isoformat() if att[3] else datetime.now().isoformat()
        marked_by = att[4] or "Система"
        
        neo4j_query = """
            MATCH (s:Student {id: $student_id})
            MATCH (l:Lecture {id: $lecture_id})
            MERGE (s)-[r:ATTENDED]->(l)
            SET r.present = $present,
                r.marked_at = $marked_at,
                r.marked_by = $marked_by
        """
        neo4j_conn.execute_query(neo4j_query, {
            'student_id': student_id,
            'lecture_id': lecture_id,
            'present': is_present,
            'marked_at': marked_at,
            'marked_by': marked_by
        })
        count += 1
        
        if count % 2000 == 0:
            print(f"     Прогресс: {count} связей ATTENDED создано...")
    
    print(f"  ✓ Создано {count} связей ATTENDED")
    return count


# ============================================================
# Проверка данных в Neo4j
# ============================================================


def check_neo4j_data():
    result = neo4j_conn.execute_query("MATCH (s:Student) RETURN count(s) as count")
    student_count = result[0]['count'] if result else 0
    
    result = neo4j_conn.execute_query("MATCH (g:Group) RETURN count(g) as count")
    group_count = result[0]['count'] if result else 0
    
    result = neo4j_conn.execute_query("MATCH (l:Lecture) RETURN count(l) as count")
    lecture_count = result[0]['count'] if result else 0
    
    result = neo4j_conn.execute_query("MATCH ()-[r:ENROLLED_IN]->() RETURN count(r) as count")
    enrolled_count = result[0]['count'] if result else 0
    
    result = neo4j_conn.execute_query("MATCH ()-[r:HAS_LECTURE]->() RETURN count(r) as count")
    has_lecture_count = result[0]['count'] if result else 0
    
    result = neo4j_conn.execute_query("MATCH ()-[r:ATTENDED]->() RETURN count(r) as count")
    attended_count = result[0]['count'] if result else 0
    
    print(f"\n📊 Статистика Neo4j:")
    print(f"  • Узлов Student: {student_count}")
    print(f"  • Узлов Group: {group_count}")
    print(f"  • Узлов Lecture: {lecture_count}")
    print(f"  • Связей ENROLLED_IN: {enrolled_count}")
    print(f"  • Связей HAS_LECTURE: {has_lecture_count}")
    print(f"  • Связей ATTENDED: {attended_count}")


# ============================================================
# Основная функция
# ============================================================


def main():
    print("=" * 60)
    print("СИНХРОНИЗАЦИЯ ДАННЫХ ИЗ POSTGRESQL В NEO4J")
    print("=" * 60)

    print("\n0. Полная очистка Neo4j...")
    clear_neo4j()
    
    try:
        # Проверка подключения к PostgreSQL
        print("\n1. Проверка подключения к PostgreSQL...")
        pg_cur.execute("SELECT 1")
        print("   ✓ PostgreSQL доступен")
        
        # Проверка подключения к Neo4j
        print("\n2. Проверка подключения к Neo4j...")
        neo4j_conn.execute_query("RETURN 1 as test")
        print("   ✓ Neo4j доступен")
        
        # Очистка Neo4j
        print("\n3. Очистка Neo4j...")
        clear_neo4j()
        
        # Синхронизация узлов
        print("\n4. Синхронизация узлов...")
        sync_groups()
        sync_students()
        sync_lectures()
        
        # Создание связей
        print("\n5. Создание связей...")
        create_enrolled_in_relationships()
        create_has_lecture_relationships()
        create_attended_relationships()
        
        # Проверка данных
        print("\n6. Проверка данных...")
        check_neo4j_data()
        
        print("\n" + "=" * 60)
        print("✓ СИНХРОНИЗАЦИЯ В NEO4J ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        pg_cur.close()
        pg_conn.close()
        neo4j_conn.close()


# ============================================================
# Запуск
# ============================================================


if __name__ == "__main__":
    main()