# sync_to_redis.py
import psycopg2
import redis
import json
from datetime import date, datetime

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
# Функция для преобразования date в строку
# ============================================================
def convert_date(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj

# ============================================================
# Функция для очистки Redis
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
# Основная функция синхронизации (только full_name)
# ============================================================
def sync_students_to_redis():
    """Синхронизировать полную информацию о студентах из PostgreSQL в Redis"""
    
    query = """
        SELECT 
            s.id,
            s.last_name,
            s.first_name,
            s.patronymic,
            s.student_card_number,
            s.email,
            s.phone,
            s.enrollment_date,
            g.name as group_name
        FROM students s
        JOIN student_groups g ON s.group_id = g.id
        ORDER BY s.id
    """
    
    pg_cur.execute(query)
    students = pg_cur.fetchall()
    
    if not students:
        print("⚠️ В PostgreSQL нет студентов")
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
        email = student[5]
        phone = student[6]
        enrollment_date = student[7]
        group_name = student[8]
        
        # Формируем полное имя
        full_name = f"{last_name} {first_name} {patronymic}".strip()
        
        # Преобразуем дату в строку
        enrollment_date_str = enrollment_date.isoformat() if enrollment_date else None
        
        redis_key = f"student:{student_id}:data"
        
        # Полные данные о студенте (без разделения имени на части)
        student_data = {
            "id": str(student_id),
            "full_name": full_name,
            "student_card_number": student_card_number,
            "email": email,
            "phone": phone,
            "enrollment_date": enrollment_date_str,
            "group_name": group_name
        }
        
        pipeline.hset(redis_key, mapping=student_data)
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
            ttl = redis_client.ttl(key)
            print(f"    {key}:")
            print(f"      id: {data.get('id')}")
            print(f"      full_name: {data.get('full_name')}")
            print(f"      group_name: {data.get('group_name')}")
            print(f"      email: {data.get('email')}")
            print(f"      TTL: {ttl} (постоянное хранение)")

# ============================================================
# Функция для получения студента из Redis
# ============================================================
def get_student_from_redis(student_id):
    """Получить студента из Redis по ID"""
    key = f"student:{student_id}:data"
    data = redis_client.hgetall(key)
    if data:
        return data
    return None

# ============================================================
# Функция для получения всех студентов группы
# ============================================================
def get_students_by_group(group_name):
    """Получить всех студентов группы из Redis"""
    students = []
    for key in redis_client.keys("student:*:data"):
        student = redis_client.hgetall(key)
        if student.get('group_name') == group_name:
            students.append(student)
    return students

# ============================================================
# Основная функция
# ============================================================
def main():
    print("=" * 60)
    print("СИНХРОНИЗАЦИЯ ДАННЫХ ИЗ POSTGRESQL В REDIS")
    print("=" * 60)
    
    try:
        # Проверка подключения
        print("\n1. Проверка подключения к PostgreSQL...")
        pg_cur.execute("SELECT 1")
        print("   ✓ PostgreSQL доступен")
        
        print("\n2. Проверка подключения к Redis...")
        redis_client.ping()
        print("   ✓ Redis доступен")
        
        # Синхронизация
        print("\n3. Синхронизация студентов...")
        count = sync_students_to_redis()
        print(f"   ✓ Синхронизировано {count} студентов в Redis (постоянное хранение)")
        
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
                print(f"   Студент найден: {student.get('full_name')}")
                print(f"   Группа: {student.get('group_name')}")
                print(f"   Email: {student.get('email')}")
                print(f"   Телефон: {student.get('phone')}")
        
        print("\n" + "=" * 60)
        print("✓ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
    
    finally:
        pg_cur.close()
        pg_conn.close()
        redis_client.close()

if __name__ == "__main__":
    main()
