# lab1_report.py
import redis
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
import psycopg2
import psycopg2.extras

# ============================================================
# Конфигурация подключения
# ============================================================
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'decode_responses': True
}

ES_CONFIG = {
    'host': 'localhost',
    'port': 9200
}

NEO4J_CONFIG = {
    'uri': 'bolt://localhost:7687',
    'user': 'neo4j',
    'password': 'password'
}

PG_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'university_system',
    'user': 'postgres',
    'password': 'postgres'
}

redis_client = redis.Redis(**REDIS_CONFIG)


# ============================================================
# Вспомогательная функция: преобразование семестра в даты
# ============================================================
def semester_to_date_range(semester: int, year: int):
    """
    Преобразует семестр (1..8) и год начала обучения в диапазон дат.
    Для семестров 1,3,5,7 (осень): 01.09.YYYY – 31.12.YYYY
    Для семестров 2,4,6,8 (весна):  01.02.YYYY+1 – 30.06.YYYY+1
    """
    if semester % 2 == 1:  # нечётный (осенний)
        start_date = f"{year}-09-01"
        end_date = f"{year}-12-31"
    else:                 # чётный (весенний)
        start_date = f"{year + 1}-02-01"
        end_date = f"{year + 1}-06-30"
    return start_date, end_date


# ============================================================
# 1. Поиск лекций по термину в Elasticsearch
# ============================================================
def search_lectures_by_term(term: str, date_from: str = None, date_to: str = None,
                            semester: int = None, year: int = None) -> List[str]:
    """
    Возвращает список ID лекций, содержащих term в title/annotation/content_text,
    с датой проведения в указанном диапазоне.
    Если передан semester + year, даты вычисляются автоматически.
    Приоритет: явные date_from/date_to выше, чем semester+year.
    """
    es = Elasticsearch([f"http://{ES_CONFIG['host']}:{ES_CONFIG['port']}"])

    # Определяем даты
    if date_from and date_to:
        pass  # уже заданы
    elif semester is not None and year is not None:
        date_from, date_to = semester_to_date_range(semester, year)
    else:
        # Если ничего не задано – не фильтруем по дате
        date_from = date_to = None

    # Строим запрос
    must_query = {
        "multi_match": {
            "query": term,
            "fields": ["title^3", "annotation^2", "content_text"],
            "type": "best_fields",
            "operator": "and"
        }
    }

    filters = []
    if date_from and date_to:
        filters.append({"range": {"date": {"gte": date_from, "lte": date_to}}})

    query_body = {
        "query": {
            "bool": {
                "must": [must_query],
                "filter": filters
            }
        },
        "_source": ["lecture_id"],
        "size": 10000
    }

    response = es.search(index="lectures", body=query_body)
    lecture_ids = [hit["_source"]["lecture_id"] for hit in response["hits"]["hits"]]
    es.close()
    return lecture_ids


# ============================================================
# 2. Получение для каждого студента списка schedule_id (Neo4j)
# ============================================================
def get_student_schedules(lecture_ids: List[str]) -> Dict[str, List[str]]:
    """
    Для каждого студента возвращает список schedule_id,
    соответствующих переданным lecture_id.
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
        MATCH (l)<-[:PART_OF]-(sch:Schedule)
        MATCH (sch)<-[:HAS_SCHEDULE]-(sg:StudentGroup)
        MATCH (sg)-[:HAS_STUDENT]->(s:Student)
        RETURN s.id AS student_id, collect(sch.id) AS schedule_ids
    """

    with driver.session() as session:
        result = session.run(query, lecture_ids=lecture_ids)
        student_schedules = {}
        for record in result:
            student_id = record["student_id"]
            schedule_ids = record["schedule_ids"]
            if schedule_ids:
                student_schedules[student_id] = schedule_ids
    driver.close()
    return student_schedules


# ============================================================
# 3. Получение отметок посещаемости из PostgreSQL (ОПТИМИЗИРОВАННАЯ ВЕРСИЯ)
# ============================================================
def get_attendance_from_pg(student_schedules: Dict[str, List[str]]) -> Dict[tuple, bool]:
    if not student_schedules:
        return {}

    pairs_set = set()
    for student_id, sched_ids in student_schedules.items():
        for sched_id in sched_ids:
            pairs_set.add((student_id, sched_id))
    
    if not pairs_set:
        return {}
    
    # Формируем список кортежей для явного приведения к UUID
    # Используем параметризованный запрос с массивом
    import psycopg2
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    
    # Создаём временную таблицу или используем unnest с массивами
    # Вариант: передать два массива UUID
    student_ids = [str(p[0]) for p in pairs_set]
    schedule_ids = [str(p[1]) for p in pairs_set]
    
    # Используем unnest для создания виртуальной таблицы
    query = """
        SELECT student_id, schedule_id, is_present
        FROM attendance
        WHERE (student_id, schedule_id) IN (
            SELECT unnest(%s::uuid[]), unnest(%s::uuid[])
        )
    """
    cur.execute(query, (student_ids, schedule_ids))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    attendance_map = {}
    for row in rows:
        attendance_map[(row[0], row[1])] = row[2] if row[2] is not None else False
    
    return attendance_map


# ============================================================
# 4. Получение полной информации о студентах из Redis
# ============================================================
def get_students_info_from_redis(student_ids: List[str]) -> Dict[str, Dict]:
    """
    Возвращает данные студентов из Redis.
    Ключ: student:{id}:data
    """
    if not student_ids:
        return {}

    pipeline = redis_client.pipeline()
    for sid in student_ids:
        key = f"student:{sid}:data"
        pipeline.hgetall(key)
    results = pipeline.execute()

    students_info = {}
    for sid, data in zip(student_ids, results):
        if data:
            students_info[sid] = {
                "id": data.get("id"),
                "full_name": data.get("full_name"),
                "student_card_number": data.get("student_card_number"),
                "email": data.get("email"),
                "phone": data.get("phone"),
                "enrollment_date": data.get("enrollment_date"),
                "group_name": data.get("group_name"),
            }
    return students_info


# ============================================================
# 5. Расчёт процента посещаемости
# ============================================================
def calculate_attendance_percent(student_schedules: Dict[str, List[str]],
                                 attendance_map: Dict[tuple, bool]) -> List[Dict]:
    """
    Для каждого студента вычисляет процент посещения.
    Возвращает список {student_id, percent, total, attended}.
    """
    results = []
    for student_id, sched_ids in student_schedules.items():
        total = len(sched_ids)
        if total == 0:
            continue
        attended = sum(1 for sched_id in sched_ids if attendance_map.get((student_id, sched_id), False))
        percent = (attended / total) * 100
        results.append({
            "student_id": student_id,
            "percent": round(percent, 2),
            "total_lectures": total,
            "attended_lectures": attended
        })
    # Сортируем по возрастанию процента
    results.sort(key=lambda x: x["percent"])
    return results


# ============================================================
# 6. Основная функция отчёта
# ============================================================
def generate_report(term: str,
                    date_from: str = None,
                    date_to: str = None,
                    semester: int = None,
                    year: int = None,
                    limit: int = 10):
    """
    Формирует отчёт: топ-N студентов с минимальным процентом посещения
    лекций, содержащих заданный термин, за указанный период.
    """
    print("=" * 80)
    print(f"ЛАБОРАТОРНАЯ РАБОТА №1")
    print(f"Термин: '{term}'")
    if date_from and date_to:
        print(f"Период: с {date_from} по {date_to}")
    elif semester is not None and year is not None:
        print(f"Семестр: {semester}, год: {year}")
    else:
        print("Период: не ограничен")
    print(f"Лимит студентов: {limit}")
    print("=" * 80)

    # Шаг 1: поиск лекций в Elasticsearch
    print("\n1. Поиск лекций, содержащих термин...")
    lecture_ids = search_lectures_by_term(term, date_from, date_to, semester, year)
    print(f"   Найдено лекций: {len(lecture_ids)}")

    if not lecture_ids:
        print("\n⚠️ Лекции с таким термином не найдены.")
        return

    # Шаг 2: получение student_id → schedule_ids из Neo4j
    print("\n2. Получение расписания студентов из Neo4j...")
    student_schedules = get_student_schedules(lecture_ids)
    print(f"   Получено студентов: {len(student_schedules)}")

    if not student_schedules:
        print("\n⚠️ Нет студентов, у которых были эти лекции в расписании.")
        return

    # Шаг 3: получение отметок посещаемости из PostgreSQL
    print("\n3. Получение отметок посещаемости из PostgreSQL...")
    attendance_map = get_attendance_from_pg(student_schedules)
    print(f"   Получено отметок: {len(attendance_map)}")

    # Шаг 4: расчёт процентов
    print("\n4. Расчёт процента посещаемости...")
    student_percents = calculate_attendance_percent(student_schedules, attendance_map)
    print(f"   Рассчитано студентов: {len(student_percents)}")

    if not student_percents:
        print("\n⚠️ Нет студентов с ненулевым количеством лекций.")
        return

    # Шаг 5: топ-N
    top_students = student_percents[:limit]
    student_ids = [s["student_id"] for s in top_students]

    # Шаг 6: получение детальной информации из Redis
    print("\n5. Получение информации о студентах из Redis...")
    students_info = get_students_info_from_redis(student_ids)
    print(f"   Получено записей: {len(students_info)}")

    # Шаг 7: объединение и вывод отчёта
    print("\n" + "=" * 80)
    print(f"ОТЧЕТ: {len(top_students)} студентов с минимальным процентом посещения")
    print(f"Термин: '{term}'")
    if date_from and date_to:
        print(f"Период: {date_from} - {date_to}")
    elif semester is not None and year is not None:
        print(f"Семестр: {semester}, год: {year}")
    print("=" * 80)
    print(f"{'№':<4} {'ФИО':<35} {'Группа':<12} {'Студ. билет':<12} {'Процент':<8} {'Посещено/Всего':<15}")
    print("-" * 95)

    for idx, student in enumerate(top_students, 1):
        info = students_info.get(student["student_id"], {})
        full_name = info.get("full_name", "Неизвестно")
        group_name = info.get("group_name", "---")
        card_number = info.get("student_card_number", "---")
        percent = student["percent"]
        attended = student["attended_lectures"]
        total = student["total_lectures"]
        print(f"{idx:<4} {full_name:<35} {group_name:<12} {card_number:<12} {percent:<8}% {attended}/{total:<12}")

    print("=" * 80)


# ============================================================
# 7. Точка входа
# ============================================================
if __name__ == "__main__":
    # Пример 1: поиск по датам
    # generate_report(term="реклама", date_from="2025-09-01", date_to="2026-06-30", limit=10)

    # Пример 2: поиск по семестру
    generate_report(term="реклама", semester=1, year=2025, limit=10)

    # Пример 3: поиск по семестру с большим лимитом
    # generate_report(term="нейронные сети", semester=2, year=2025, limit=100)