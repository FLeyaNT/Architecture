import psycopg2
from neo4j import GraphDatabase
from uuid import UUID
from decimal import Decimal
from datetime import date, time

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
# Вспомогательные функции
# ============================================================
def uuid_to_str(uuid_value):
    return str(uuid_value) if isinstance(uuid_value, UUID) else uuid_value

def convert_decimal(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    return value

def clear_neo4j():
    neo4j_conn.execute_query("MATCH (n) DETACH DELETE n")
    print("✓ Neo4j очищена")

def format_date(d):
    return d.isoformat() if isinstance(d, date) else d

def format_time(t):
    return t.isoformat() if isinstance(t, time) else t

# ============================================================
# 1. Синхронизация узлов Specialty
# ============================================================
def sync_specialties():
    print("  Синхронизация специальностей...")
    pg_cur.execute("""
        SELECT id, name, code, degree_level, duration_years
        FROM specialties
    """)
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        neo4j_conn.execute_query("""
            MERGE (sp:Specialty {id: $id})
            SET sp.name = $name,
                sp.code = $code,
                sp.degree_level = $degree_level,
                sp.duration_years = $duration_years
        """, {
            'id': uuid_to_str(row[0]),
            'name': row[1],
            'code': row[2],
            'degree_level': row[3],
            'duration_years': convert_decimal(row[4])
        })
        count += 1
    print(f"    ✓ {count} специальностей")

# ============================================================
# 2. Синхронизация узлов StudentGroup (только поля группы, без дублирования специальности)
# ============================================================
def sync_student_groups():
    print("  Синхронизация групп...")
    query = """
        SELECT id, name, enrollment_year, curator, specialty_id
        FROM student_groups
    """
    pg_cur.execute(query)
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        neo4j_conn.execute_query("""
            MERGE (sg:StudentGroup {id: $id})
            SET sg.name = $name,
                sg.enrollment_year = $enrollment_year,
                sg.curator = $curator,
                sg.specialty_id = $specialty_id
        """, {
            'id': uuid_to_str(row[0]),
            'name': row[1],
            'enrollment_year': convert_decimal(row[2]),
            'curator': row[3] or "",
            'specialty_id': uuid_to_str(row[4])
        })
        count += 1
    print(f"    ✓ {count} групп")

# ============================================================
# 3. Синхронизация узлов Student
# ============================================================
def sync_students():
    print("  Синхронизация студентов...")
    pg_cur.execute("SELECT id, student_card_number FROM students")
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        neo4j_conn.execute_query("""
            MERGE (s:Student {id: $id})
            SET s.student_card_number = $student_card_number
        """, {
            'id': uuid_to_str(row[0]),
            'student_card_number': row[1]
        })
        count += 1
    print(f"    ✓ {count} студентов")

# ============================================================
# 4. Синхронизация узлов Schedule
# ============================================================
def sync_schedules():
    print("  Синхронизация расписания...")
    pg_cur.execute("SELECT id, scheduled_date, classroom, start_time FROM schedule")
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        neo4j_conn.execute_query("""
            MERGE (sch:Schedule {id: $id})
            SET sch.date = $date,
                sch.classroom = $classroom,
                sch.time = $time
        """, {
            'id': uuid_to_str(row[0]),
            'date': format_date(row[1]),
            'classroom': row[2] or "Не указана",
            'time': format_time(row[3])
        })
        count += 1
    print(f"    ✓ {count} записей расписания")

# ============================================================
# 5. Синхронизация узлов Lecture (полная информация)
# ============================================================
def sync_lectures():
    print("  Синхронизация лекций...")
    pg_cur.execute("""
        SELECT 
            l.id,
            l.title,
            l.annotation,
            l.lecture_type,
            l.order_number,
            l.duration_minutes,
            l.requires_computers,
            lc.semester,
            lc.name AS course_name
        FROM lectures l
        JOIN lecture_courses lc ON l.course_id = lc.id
    """)
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        neo4j_conn.execute_query("""
            MERGE (lec:Lecture {id: $id})
            SET lec.title = $title,
                lec.annotation = $annotation,
                lec.type = $type,
                lec.order_number = $order_number,
                lec.duration_minutes = $duration,
                lec.requires_computers = $requires_computers,
                lec.semester = $semester,
                lec.course_name = $course_name
        """, {
            'id': uuid_to_str(row[0]),
            'title': row[1] or "Без названия",
            'annotation': row[2] or "",
            'type': row[3],
            'order_number': convert_decimal(row[4]),
            'duration': convert_decimal(row[5]) if row[5] else 90,
            'requires_computers': row[6] if row[6] is not None else False,
            'semester': convert_decimal(row[7]),
            'course_name': row[8]
        })
        count += 1
    print(f"    ✓ {count} лекций")

# ============================================================
# 6. Синхронизация узлов Course
# ============================================================
def sync_courses():
    print("  Синхронизация курсов...")
    pg_cur.execute("""
        SELECT 
            id,
            name,
            description,
            semester,
            total_hours,
            lecture_hours,
            practice_hours,
            lab_hours,
            is_specialty_discipline
        FROM lecture_courses
    """)
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        neo4j_conn.execute_query("""
            MERGE (c:Course {id: $id})
            SET c.name = $name,
                c.description = $description,
                c.semester = $semester,
                c.total_hours = $total_hours,
                c.lecture_hours = $lecture_hours,
                c.practice_hours = $practice_hours,
                c.lab_hours = $lab_hours,
                c.is_specialty_discipline = $is_specialty
        """, {
            'id': uuid_to_str(row[0]),
            'name': row[1],
            'description': row[2] or "",
            'semester': convert_decimal(row[3]),
            'total_hours': convert_decimal(row[4]),
            'lecture_hours': convert_decimal(row[5]),
            'practice_hours': convert_decimal(row[6]),
            'lab_hours': convert_decimal(row[7]),
            'is_specialty': row[8] or False
        })
        count += 1
    print(f"    ✓ {count} курсов")

# ============================================================
# 7. Создание связей
# ============================================================
def create_relationships():
    # 1. StudentGroup -> HAS_SPECIALTY -> Specialty
    print("  Создание связей HAS_SPECIALTY...")
    pg_cur.execute("SELECT id, specialty_id FROM student_groups")
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        group_id = uuid_to_str(row[0])
        specialty_id = uuid_to_str(row[1])
        neo4j_conn.execute_query("""
            MATCH (sg:StudentGroup {id: $group_id})
            MATCH (sp:Specialty {id: $specialty_id})
            MERGE (sg)-[:HAS_SPECIALTY]->(sp)
        """, {'group_id': group_id, 'specialty_id': specialty_id})
        count += 1
    print(f"    ✓ {count} связей HAS_SPECIALTY")

    # 2. StudentGroup -> HAS_STUDENT -> Student
    print("  Создание связей HAS_STUDENT...")
    pg_cur.execute("SELECT id, group_id FROM students")
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        student_id = uuid_to_str(row[0])
        group_id = uuid_to_str(row[1])
        neo4j_conn.execute_query("""
            MATCH (sg:StudentGroup {id: $group_id})
            MATCH (s:Student {id: $student_id})
            MERGE (sg)-[:HAS_STUDENT]->(s)
        """, {'group_id': group_id, 'student_id': student_id})
        count += 1
    print(f"    ✓ {count} связей HAS_STUDENT")

    # 3. StudentGroup -> HAS_SCHEDULE -> Schedule
    print("  Создание связей HAS_SCHEDULE...")
    pg_cur.execute("SELECT id, group_id FROM schedule")
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        schedule_id = uuid_to_str(row[0])
        group_id = uuid_to_str(row[1])
        neo4j_conn.execute_query("""
            MATCH (sg:StudentGroup {id: $group_id})
            MATCH (sch:Schedule {id: $schedule_id})
            MERGE (sg)-[:HAS_SCHEDULE]->(sch)
        """, {'group_id': group_id, 'schedule_id': schedule_id})
        count += 1
    print(f"    ✓ {count} связей HAS_SCHEDULE")

    # 4. Schedule -> PART_OF -> Lecture
    print("  Создание связей PART_OF...")
    pg_cur.execute("SELECT id, lecture_id FROM schedule")
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        schedule_id = uuid_to_str(row[0])
        lecture_id = uuid_to_str(row[1])
        neo4j_conn.execute_query("""
            MATCH (sch:Schedule {id: $schedule_id})
            MATCH (lec:Lecture {id: $lecture_id})
            MERGE (sch)-[:PART_OF]->(lec)
        """, {'schedule_id': schedule_id, 'lecture_id': lecture_id})
        count += 1
    print(f"    ✓ {count} связей PART_OF")

    # 5. Lecture -> BELONGS_TO -> Course
    print("  Создание связей BELONGS_TO...")
    pg_cur.execute("SELECT id, course_id FROM lectures")
    rows = pg_cur.fetchall()
    count = 0
    for row in rows:
        lecture_id = uuid_to_str(row[0])
        course_id = uuid_to_str(row[1])
        neo4j_conn.execute_query("""
            MATCH (lec:Lecture {id: $lecture_id})
            MATCH (c:Course {id: $course_id})
            MERGE (lec)-[:BELONGS_TO]->(c)
        """, {'lecture_id': lecture_id, 'course_id': course_id})
        count += 1
    print(f"    ✓ {count} связей BELONGS_TO")

# ============================================================
# 8. Проверка статистики
# ============================================================
def check_neo4j_data():
    labels = ['Specialty', 'StudentGroup', 'Student', 'Schedule', 'Lecture', 'Course']
    print("\n📊 Статистика Neo4j (с узлами Specialty):")
    for label in labels:
        res = neo4j_conn.execute_query(f"MATCH (n:{label}) RETURN count(n) as cnt")
        cnt = res[0]['cnt'] if res else 0
        print(f"  • {label}: {cnt}")
    rels = ['HAS_SPECIALTY', 'HAS_STUDENT', 'HAS_SCHEDULE', 'PART_OF', 'BELONGS_TO']
    for rel in rels:
        res = neo4j_conn.execute_query(f"MATCH ()-[r:{rel}]->() RETURN count(r) as cnt")
        cnt = res[0]['cnt'] if res else 0
        print(f"  • {rel}: {cnt}")

# ============================================================
# Основная функция
# ============================================================
def main():
    print("=" * 60)
    print("СИНХРОНИЗАЦИЯ POSTGRESQL -> NEO4J (С УЗЛАМИ SPECIALTY)")
    print("=" * 60)

    try:
        print("\n0. Очистка Neo4j...")
        clear_neo4j()

        print("\n1. Создание узлов...")
        sync_specialties()
        sync_student_groups()
        sync_students()
        sync_schedules()
        sync_lectures()
        sync_courses()

        print("\n2. Создание связей...")
        create_relationships()

        print("\n3. Проверка данных...")
        check_neo4j_data()

        print("\n" + "=" * 60)
        print("✓ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pg_cur.close()
        pg_conn.close()
        neo4j_conn.close()

if __name__ == "__main__":
    main()