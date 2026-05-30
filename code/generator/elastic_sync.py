# sync_to_elasticsearch.py
import psycopg2
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple

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
# Подключение к Elasticsearch
# ============================================================
es = Elasticsearch(
    ['http://localhost:9200'],
    verify_certs=False,
    request_timeout=30
)

INDEX_NAME = 'lectures'

# ============================================================
# Создание индекса с маппингом (добавлено поле date)
# ============================================================
def create_index_if_not_exists():
    """Создаёт индекс lectures с русским анализатором и маппингом"""
    if es.indices.exists(index=INDEX_NAME):
        print(f"✓ Индекс {INDEX_NAME} уже существует, удаляем...")
        es.indices.delete(index=INDEX_NAME)
        print(f"✓ Индекс {INDEX_NAME} удалён")

    settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "russian_analyzer": {
                        "type": "russian"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "lecture_id": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "analyzer": "russian_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "annotation": {
                    "type": "text",
                    "analyzer": "russian_analyzer"
                },
                "content_text": {
                    "type": "text",
                    "analyzer": "russian_analyzer"
                },
                "course_name": {
                    "type": "text",
                    "analyzer": "russian_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "course_description": {
                    "type": "text",
                    "analyzer": "russian_analyzer"
                },
                "is_specialty_discipline": {"type": "boolean"},
                "lecture_type": {"type": "keyword"},
                "duration_minutes": {"type": "integer"},
                "semester": {"type": "integer"},
                "date": {"type": "date"},                      # ← ДОБАВЛЕНО
                "tags": {"type": "keyword"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"}
            }
        }
    }

    es.indices.create(index=INDEX_NAME, body=settings)
    print(f"✓ Индекс {INDEX_NAME} создан с русским анализатором и полем date")

# ============================================================
# Вспомогательные функции
# ============================================================
def extract_tags(title: str, course_name: str) -> List[str]:
    """Извлекает простые теги из названия лекции и курса"""
    text = (title + " " + course_name).lower()
    words = re.findall(r'\b\w+\b', text)
    tags = list(set([w for w in words if len(w) > 3]))
    return tags[:10]

# ============================================================
# Получение данных из PostgreSQL (с датой лекции)
# ============================================================
def fetch_lectures_data() -> List[Tuple[str, Dict]]:
    """
    Выбирает данные о лекциях, курсах, материалах и дате проведения.
    Для одной лекции может быть несколько дат (разные группы).
    Берём MIN дату как основную (или можно ANY).
    """
    query = """
        SELECT 
            l.id,
            l.title,
            l.annotation,
            l.lecture_type,
            l.duration_minutes,
            lc.name AS course_name,
            lc.description AS course_description,
            lc.is_specialty_discipline,
            lc.semester,
            COALESCE(
                (SELECT string_agg(content_text, ' ') 
                 FROM lecture_materials 
                 WHERE lecture_id = l.id AND content_type = 'text'),
                '' 
            ) AS content_text,
            MIN(sch.scheduled_date) AS lecture_date   -- ← берём первую дату лекции
        FROM lectures l
        JOIN lecture_courses lc ON l.course_id = lc.id
        LEFT JOIN schedule sch ON sch.lecture_id = l.id
        GROUP BY l.id, l.title, l.annotation, l.lecture_type, l.duration_minutes,
                 lc.name, lc.description, lc.is_specialty_discipline, lc.semester
        ORDER BY l.id
    """
    pg_cur.execute(query)
    rows = pg_cur.fetchall()
    
    lectures_data = []
    for row in rows:
        lec_id = str(row[0])
        title = row[1] or "Без названия"
        annotation = row[2] or ""
        lecture_type = row[3] or "lecture"
        duration_minutes = row[4] if row[4] else 90
        course_name = row[5] or "Не указан"
        course_description = row[6] or ""
        is_specialty = row[7] if row[7] is not None else False
        semester = row[8] if row[8] else 1
        content_text = row[9] or ""
        lecture_date = row[10].isoformat() if row[10] else "2026-01-01"

        doc = {
            "lecture_id": lec_id,
            "title": title,
            "annotation": annotation,
            "content_text": content_text,
            "course_name": course_name,
            "course_description": course_description,
            "is_specialty_discipline": is_specialty,
            "lecture_type": lecture_type,
            "duration_minutes": duration_minutes,
            "semester": semester,
            "date": lecture_date,                           # ← ДОБАВЛЕНО
            "tags": extract_tags(title, course_name),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        lectures_data.append((lec_id, doc))
    
    return lectures_data

# ============================================================
# Массовая индексация в Elasticsearch
# ============================================================
def bulk_index(lectures_data: List[Tuple[str, Dict]]):
    """Загружает документы в Elasticsearch пачками"""
    if not lectures_data:
        print("Нет данных для индексации.")
        return 0

    actions = [
        {
            "_index": INDEX_NAME,
            "_id": lec_id,
            "_source": doc
        }
        for lec_id, doc in lectures_data
    ]

    success, failed = bulk(es, actions, stats_only=True, raise_on_error=False)
    print(f"✓ Успешно индексировано: {success} документов")
    if failed:
        print(f"✗ Ошибок: {failed}")
    return success

# ============================================================
# Проверка данных в Elasticsearch
# ============================================================
def check_elasticsearch():
    """Выводит статистику по индексу"""
    try:
        stats = es.indices.stats(index=INDEX_NAME)
        doc_count = stats['indices'][INDEX_NAME]['total']['docs']['count']
        print(f"\n📊 Статистика Elasticsearch:")
        print(f"  • Индекс: {INDEX_NAME}")
        print(f"  • Количество документов: {doc_count}")
        
        # Пример одного документа
        res = es.search(index=INDEX_NAME, body={"query": {"match_all": {}}}, size=1)
        if res['hits']['hits']:
            sample = res['hits']['hits'][0]['_source']
            print(f"\n  Пример документа:")
            print(f"    ID: {res['hits']['hits'][0]['_id']}")
            print(f"    Название: {sample.get('title')}")
            print(f"    Дата: {sample.get('date')}")
            print(f"    Курс: {sample.get('course_name')}")
    except Exception as e:
        print(f"Ошибка при проверке: {e}")

# ============================================================
# Очистка Elasticsearch (удаление индекса)
# ============================================================
def clear_elasticsearch():
    """Полностью удаляет индекс lectures, если он существует"""
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        print(f"✓ Индекс {INDEX_NAME} удалён (полная очистка данных)")
    else:
        print(f"✓ Индекс {INDEX_NAME} не существовал, очистка не требуется")

# ============================================================
# Основная функция
# ============================================================
def main():
    print("=" * 60)
    print("СИНХРОНИЗАЦИЯ POSTGRESQL -> ELASTICSEARCH")
    print("=" * 60)

    try:
        # 1. Проверка подключения
        print("\n1. Проверка подключения к PostgreSQL...")
        pg_cur.execute("SELECT 1")
        print("   ✓ PostgreSQL доступен")

        print("\n2. Проверка подключения к Elasticsearch...")
        if not es.ping():
            raise ConnectionError("Не удалось подключиться к Elasticsearch")
        print("   ✓ Elasticsearch доступен")

        # 2. Очистка старых данных
        print("\n3. Очистка данных Elasticsearch...")
        clear_elasticsearch()

        # 3. Создание индекса
        print("\n4. Создание индекса...")
        create_index_if_not_exists()

        # 4. Выборка данных из PostgreSQL
        print("\n5. Загрузка данных из PostgreSQL...")
        lectures_data = fetch_lectures_data()
        print(f"   ✓ Получено {len(lectures_data)} лекций для индексации")

        # 5. Индексация
        print("\n6. Индексация в Elasticsearch...")
        indexed = bulk_index(lectures_data)

        # 6. Проверка
        print("\n7. Проверка данных в Elasticsearch...")
        check_elasticsearch()

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
        es.close()

if __name__ == "__main__":
    main()