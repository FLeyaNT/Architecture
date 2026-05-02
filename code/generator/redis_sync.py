# sync_to_redis.py
import psycopg2
import redis
import json

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
# Подключение к Redis
# ============================================================


redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)


# ============================================================
# Функция для очистки Redis (опционально)
# ============================================================


def clear_redis():
    """Очистить все ключи Redis, связанные со студентами"""
    keys = redis_client.keys("student:*:data")
    if keys:
        redis_client.delete(*keys)
        print(f"✓ Удалено {len(keys)} старых ключей из Redis")
    else:
        print("✓ Redis пуст, очистка не требуется")


# ============================================================
# Основная функция синхронизации
# ============================================================


def sync_students_to_redis():
    """Синхронизировать студентов из PostgreSQL в Redis"""
    
    query = """
        SELECT 
            s.id,
            s.last_name,
            s.first_name,
            s.patronymic,
            s.student_card_number,
            g.name as group_name
        FROM students s
        JOIN student_groups g ON s.group_id = g.id
        ORDER BY s.id
    """
    
    pg_cur.execute(query)
    students = pg_cur.fetchall()
    
    if not students:
        print("⚠️ В PostgreSQL нет активных студентов")
        return 0
    
    clear_redis()
    
    synced_count = 0
    pipeline = redis_client.pipeline()
    
    for student in students:
        student_id = student[0]
        last_name = student[1]
        first_name = student[2]
        patronymic = student[3] or ""
        student_card_number = student[4]
        group_name = student[5]
        
        full_name = f"{last_name} {first_name} {patronymic}".strip()
        
        redis_key = f"student:{student_id}:data"
        
        student_data = {
            "id": str(student_id),
            "name": full_name,
            "student_card_number": student_card_number,
            "group": group_name
        }
        
        pipeline.hset(redis_key, mapping=student_data)
        pipeline.expire(redis_key, 3600)
        synced_count += 1
    
    pipeline.execute()
    
    return synced_count


# ============================================================
# Функция для проверки данных в Redis
# ============================================================


def check_redis_data():
    """Проверить, что данные успешно сохранены в Redis"""
    keys = redis_client.keys("student:*:data")
    print(f"\n📊 Статистика Redis:")
    print(f"  • Всего ключей студентов: {len(keys)}")
    
    if keys:
        print("\n  Примеры данных в Redis:")
        for key in keys[:3]:
            data = redis_client.hgetall(key)
            print(f"    {key}: {data}")


# ============================================================
# Функция для получения студента из Redis (пример использования)
# ============================================================


def get_student_from_redis(student_id):
    """Получить студента из Redis по ID"""
    key = f"student:{student_id}:data"
    data = redis_client.hgetall(key)
    if data:
        return data
    return None


# ============================================================
# Основная функция
# ============================================================


def main():
    print("=" * 60)
    print("СИНХРОНИЗАЦИЯ ДАННЫХ ИЗ POSTGRESQL В REDIS")
    print("=" * 60)
    
    try:
        # Проверка подключения к PostgreSQL
        print("\n1. Проверка подключения к PostgreSQL...")
        pg_cur.execute("SELECT 1")
        print("   ✓ PostgreSQL доступен")
        
        # Проверка подключения к Redis
        print("\n2. Проверка подключения к Redis...")
        redis_client.ping()
        print("   ✓ Redis доступен")
        
        # Синхронизация
        print("\n3. Синхронизация студентов...")
        count = sync_students_to_redis()
        print(f"   ✓ Синхронизировано {count} студентов в Redis")
        
        # Проверка
        print("\n4. Проверка данных в Redis...")
        check_redis_data()
        
        # Пример получения студента
        if count > 0:
            print("\n5. Пример получения студента из Redis:")
            first_key = redis_client.keys("student:*:data")[0]
            student_id = first_key.replace("student:", "").replace(":data", "")
            student = get_student_from_redis(student_id)
            if student:
                print(f"   Студент найден: {student}")
        
        print("\n" + "=" * 60)
        print("✓ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
    
    finally:
        pg_cur.close()
        pg_conn.close()
        redis_client.close()


# ============================================================
# Запуск
# ============================================================


if __name__ == "__main__":
    main()
