# lab2_report.py
import psycopg2
import redis
from neo4j import GraphDatabase
from datetime import datetime
from typing import List, Dict, Any

# ============================================================
# Конфигурация подключения
# ============================================================
PG_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "university_system",
    "user": "postgres",
    "password": "postgres"
}

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

NEO4J_CONFIG = {
    "uri": "bolt://localhost:7687",
    "user": "neo4j",
    "password": "password"
}


# ============================================================
# 1. Получение полной информации о курсе из PostgreSQL
# ============================================================
def get_course_info(course_name: str, semester: int) -> Dict:
    """
    Возвращает полную информацию о курсе.
    """
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    
    query = """
        SELECT 
            lc.name as course_name,
            lc.description,
            lc.semester,
            lc.total_hours,
            lc.lecture_hours,
            lc.practice_hours,
            lc.lab_hours,
            lc.is_specialty_discipline,
            s.name as specialty_name,
            s.code as specialty_code,
            s.degree_level
        FROM lecture_courses lc
        JOIN specialties s ON lc.specialty_id = s.id
        WHERE lc.name = %s AND lc.semester = %s
        LIMIT 1
    """
    
    cur.execute(query, (course_name, semester))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        return {
            "name": row[0],
            "description": row[1],
            "semester": row[2],
            "total_hours": row[3],
            "lecture_hours": row[4],
            "practice_hours": row[5],
            "lab_hours": row[6],
            "is_specialty_discipline": "Да" if row[7] else "Нет",
            "specialty_name": row[8],
            "specialty_code": row[9],
            "degree_level": row[10]
        }
    return None


# ============================================================
# 2. Поиск лекций по курсу, семестру и году в PostgreSQL
# ============================================================
def get_lectures_from_postgres(course_name: str, semester: int, year: int) -> List[Dict]:
    """
    Возвращает список лекций по названию курса, семестру и году.
    """
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    
    query = """
        SELECT DISTINCT
            l.id,
            l.title,
            l.requires_computers,
            l.duration_minutes,
            lc.name as course_name,
            lc.semester
        FROM lectures l
        JOIN lecture_courses lc ON l.course_id = lc.id
        JOIN schedule sched ON sched.lecture_id = l.id
        WHERE lc.name = %s
          AND lc.semester = %s
          AND EXTRACT(YEAR FROM sched.scheduled_date) = %s
    """
    
    cur.execute(query, (course_name, semester, year))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    lectures = []
    for row in rows:
        lectures.append({
            "lecture_id": row[0],
            "title": row[1],
            "requires_computers": row[2],
            "duration_minutes": row[3],
            "course_name": row[4],
            "semester": row[5]
        })
    
    return lectures


# ============================================================
# 3. Получение количества слушателей с группировкой в Neo4j
# ============================================================
def get_listeners_by_time_slot(lecture_ids: List[str]) -> Dict[str, List[Dict]]:
    """
    Для каждой лекции возвращает список временных слотов с количеством слушателей.
    """
    if not lecture_ids:
        return {}
    
    driver = GraphDatabase.driver(
        NEO4J_CONFIG["uri"], 
        auth=(NEO4J_CONFIG["user"], NEO4J_CONFIG["password"])
    )

    query = """
        MATCH (l:Lecture)
        WHERE l.id IN $lecture_ids
        MATCH (g:Group)-[r:HAS_LECTURE]->(l)
        MATCH (g)<-[:ENROLLED_IN]-(s:Student)
        WITH l, 
             r.date as scheduled_date,
             r.start_time as start_time,
             r.classroom as classroom,
             COUNT(DISTINCT s) as listeners_count
        RETURN l.id as lecture_id,
               l.title as lecture_title,
               l.requires_computers as requires_computers,
               scheduled_date,
               start_time,
               classroom,
               listeners_count
    """

    with driver.session() as session:
        result = session.run(query, lecture_ids=lecture_ids)
        
        listeners_by_lecture = {}
        for record in result:
            lec_id = record["lecture_id"]
            
            slot_info = {
                "scheduled_date": record["scheduled_date"],
                "start_time": record["start_time"],
                "classroom": record["classroom"],
                "listeners": record["listeners_count"]
            }
            
            if lec_id not in listeners_by_lecture:
                listeners_by_lecture[lec_id] = {
                    "title": record["lecture_title"],
                    "requires_computers": record["requires_computers"],
                    "slots": []
                }
            listeners_by_lecture[lec_id]["slots"].append(slot_info)
    
    driver.close()
    return listeners_by_lecture


# ============================================================
# 4. Основная функция для формирования отчета
# ============================================================
def generate_report(course_name: str, semester: int, year: int):
    print("=" * 80)
    print(f"ЛАБОРАТОРНАЯ РАБОТА №2")
    print(f"Год: {year}")
    print("=" * 80)

    # Шаг 1: получение полной информации о курсе
    print("\n1. Получение информации о курсе...")
    course_info = get_course_info(course_name, semester)
    
    if not course_info:
        print(f"\n⚠️ Курс '{course_name}' (семестр {semester}) не найден.")
        return
    
    # Вывод информации о курсе
    print(f"\n📚 ИНФОРМАЦИЯ О КУРСЕ:")
    print(f"   Название: {course_info['name']}")
    print(f"   Описание: {course_info['description'][:200]}..." if course_info['description'] else "   Описание: отсутствует")
    print(f"   Семестр: {course_info['semester']}")
    print(f"   Всего часов: {course_info['total_hours']}")
    print(f"   Лекционных часов: {course_info['lecture_hours']}")
    print(f"   Практических часов: {course_info['practice_hours']}")
    print(f"   Лабораторных часов: {course_info['lab_hours']}")
    print(f"   Специальная дисциплина: {course_info['is_specialty_discipline']}")
    print(f"   Специальность: {course_info['specialty_name']} ({course_info['specialty_code']})")
    print(f"   Уровень: {course_info['degree_level']}")

    # Шаг 2: поиск лекций в PostgreSQL
    print("\n2. Поиск лекций по курсу...")
    lectures = get_lectures_from_postgres(course_name, semester, year)
    print(f"   Найдено лекций: {len(lectures)}")

    if not lectures:
        print("\n⚠️ Лекции по указанному курсу не найдены.")
        return

    # Шаг 3: получение ID лекций
    lecture_ids = [lec["lecture_id"] for lec in lectures if lec["lecture_id"]]

    # Шаг 4: получение количества слушателей из Neo4j
    print("\n3. Расчет количества слушателей...")
    listeners_by_lecture = get_listeners_by_time_slot(lecture_ids)
    print(f"   Получено данных по {len(listeners_by_lecture)} лекциям")

    # Шаг 5: формирование отчета
    print("\n" + "=" * 80)
    print(f"ОТЧЕТ: Необходимый объем аудитории для курса '{course_name}'")
    print("=" * 80)
    
    # Таблица с информацией о лекциях
    print(f"\n{'№':<3} {'Лекция':<40} {'Длит.':<6} {'Требует ПК':<12} {'Дата':<12} {'Время':<10} {'Аудитория':<12} {'Слушателей':<10}")
    print("-" * 115)
    
    slot_counter = 1
    for lec_id, lec_info in listeners_by_lecture.items():
        for slot in lec_info["slots"]:
            duration = f"{slot.get('duration_minutes', 90)} мин"
            requires = "Да" if lec_info["requires_computers"] else "Нет"
            print(f"{slot_counter:<3} {lec_info['title']:<40} {duration:<6} {requires:<12} "
                  f"{slot['scheduled_date']:<12} {slot['start_time']:<10} {slot['classroom']:<12} {slot['listeners']:<10}")
            slot_counter += 1
    
    print("=" * 80)
    
    # Итоговая статистика
    total_lectures = len(listeners_by_lecture)
    total_slots = sum(len(lec["slots"]) for lec in listeners_by_lecture.values())
    total_listeners_all = sum(
        sum(slot["listeners"] for slot in lec["slots"]) 
        for lec in listeners_by_lecture.values()
    )
    
    print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА ПО КУРСУ:")
    print(f"  • Всего лекций в курсе: {total_lectures}")
    print(f"  • Всего занятий (слотов): {total_slots}")
    print(f"  • Общее количество слушателей (суммарно): {total_listeners_all}")
    print("=" * 80)


# ============================================================
# 5. Точка входа
# ============================================================
if __name__ == "__main__":
    course_name = "Стратегическое и широкое интернет-решение"
    semester = 3
    year = 2026
    
    generate_report(course_name, semester, year)