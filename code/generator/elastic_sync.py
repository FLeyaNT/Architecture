# sync_to_elasticsearch.py
import psycopg2
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
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
# Создание индекса с маппингом (только нужные поля)
# ============================================================
def create_index_if_not_exists():
    """Создаёт индекс lectures с русским анализатором и минимальным маппингом"""
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
                "semester": {"type": "integer"}
            }
        }
    }

    es.indices.create(index=INDEX_NAME, body=settings)
    print(f"✓ Индекс {INDEX_NAME} создан с русским анализатором (ненужные поля удалены)")

# ============================================================
# Получение данных из PostgreSQL (без лишних полей)
# ============================================================
def fetch_lectures_data() -> List[Tuple[str, Dict]]:
    """
    Выбирает только необходимые данные: 
    id, название, аннотацию, текст материалов, название курса, описание курса, семестр.
    """
    query = """
        SELECT 
            l.id,
            l.title,
            l.annotation,
            lc.name AS course_name,
            lc.description AS course_description,
            lc.semester,
            COALESCE(
                (SELECT string_agg(content_text, ' ') 
                 FROM lecture_materials 
                 WHERE lecture_id = l.id AND content_type = 'text'),
                '' 
            ) AS content_text
        FROM lectures l
        JOIN lecture_courses lc ON l.course_id = lc.id
        ORDER BY l.id
    """
    pg_cur.execute(query)
    rows = pg_cur.fetchall()
    
    lectures_data = []
    for row in rows:
        lec_id = str(row[0])
        title = row[1] or "Без названия"
        annotation = row[2] or ""
        course_name = row[3] or "Не указан"
        course_description = row[4] or ""
        semester = row[5] if row[5] is not None else 1
        content_text = row[6] or ""

        doc = {
            "lecture_id": lec_id,
            "title": title,
            "annotation": annotation,
            "content_text": content_text,
            "course_name": course_name,
            "course_description": course_description,
            "semester": semester
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
    print("(удалены поля: is_specialty_discipline, lecture_type, duration_minutes, date, tags, created_at, updated_at)")
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