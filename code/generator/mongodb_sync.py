import psycopg2
import pymongo
from uuid import UUID


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
# Подключение к MongoDB
# ============================================================


mongo_client = pymongo.MongoClient(
    host='localhost',
    port=27017,
    username='admin',
    password='password'
)
mongo_db = mongo_client['university_db']
mongo_collection = mongo_db['universities']


# ============================================================
# Функция для очистки MongoDB (опционально)
# ============================================================


def clear_mongodb():
    """Очистить коллекцию universities в MongoDB"""
    result = mongo_collection.delete_many({})
    print(f"✓ Удалено {result.deleted_count} старых документов из MongoDB")


# ============================================================
# Функция для преобразования UUID в строку
# ============================================================


def uuid_to_str(uuid_value):
    """Преобразует UUID в строку, если нужно"""
    if isinstance(uuid_value, UUID):
        return str(uuid_value)
    return uuid_value


# ============================================================
# Основная функция синхронизации
# ============================================================


def sync_universities_to_mongodb():
    """Синхронизировать иерархию университетов из PostgreSQL в MongoDB"""
    
    # 1. Получаем все университеты
    pg_cur.execute("""
        SELECT id, name, short_name, address, website, founded_year
        FROM universities
        ORDER BY name
    """)
    universities = pg_cur.fetchall()
    
    if not universities:
        print("⚠️ В PostgreSQL нет университетов")
        return 0
    
    clear_mongodb()
    
    synced_count = 0
    
    for univ in universities:
        univ_id = uuid_to_str(univ[0])
        univ_name = univ[1]
        univ_short_name = univ[2]
        univ_address = univ[3]
        univ_website = univ[4]
        univ_founded_year = univ[5]
        
        pg_cur.execute("""
            SELECT id, name, short_name, dean
            FROM institutes
            WHERE university_id = %s
            ORDER BY name
        """, (univ[0],))
        institutes = pg_cur.fetchall()
        
        institutes_list = []
        
        for inst in institutes:
            inst_id = uuid_to_str(inst[0])
            inst_name = inst[1]
            inst_short_name = inst[2]
            inst_dean = inst[3]
            
            pg_cur.execute("""
                SELECT id, name, short_name, head, room
                FROM departments
                WHERE institute_id = %s
                ORDER BY name
            """, (inst[0],))
            departments = pg_cur.fetchall()
            
            departments_list = []
            
            for dept in departments:
                dept_id = uuid_to_str(dept[0])
                dept_name = dept[1]
                dept_short_name = dept[2]
                dept_head = dept[3]
                dept_room = dept[4]
                
                departments_list.append({
                    "id": dept_id,
                    "name": dept_name,
                    "short_name": dept_short_name,
                    "head": dept_head,
                    "room": dept_room
                })
            
            institutes_list.append({
                "id": inst_id,
                "name": inst_name,
                "short_name": inst_short_name,
                "dean": inst_dean,
                "departments": departments_list
            })
        
        university_doc = {
            "_id": univ_id,
            "name": univ_name,
            "short_name": univ_short_name,
            "address": univ_address,
            "website": univ_website,
            "founded_year": univ_founded_year,
            "institutes": institutes_list,
            "created_at": "2026-05-01T00:00:00",
            "updated_at": "2026-05-01T00:00:00"
        }
        
        mongo_collection.update_one(
            {"_id": univ_id},
            {"$set": university_doc},
            upsert=True
        )
        
        synced_count += 1
        print(f"  ✓ Синхронизирован университет: {univ_name}")
    
    return synced_count


# ============================================================
# Функция для проверки данных в MongoDB
# ============================================================


def check_mongodb_data():
    """Проверить, что данные успешно сохранены в MongoDB"""
    count = mongo_collection.count_documents({})
    print(f"\n📊 Статистика MongoDB:")
    print(f"  • Всего документов университетов: {count}")


# ============================================================
# Функция для получения университета из MongoDB (пример)
# ============================================================


def get_university_from_mongodb(univ_id):
    """Получить университет из MongoDB по ID"""
    return mongo_collection.find_one({"_id": univ_id})


# ============================================================
# Основная функция
# ============================================================


def main():
    print("=" * 60)
    print("СИНХРОНИЗАЦИЯ ДАННЫХ ИЗ POSTGRESQL В MONGODB")
    print("=" * 60)
    
    try:
        # Проверка подключения к PostgreSQL
        print("\n1. Проверка подключения к PostgreSQL...")
        pg_cur.execute("SELECT 1")
        print("   ✓ PostgreSQL доступен")
        
        # Проверка подключения к MongoDB
        print("\n2. Проверка подключения к MongoDB...")
        mongo_client.admin.command('ping')
        print("   ✓ MongoDB доступен")
        
        # Синхронизация
        print("\n3. Синхронизация университетов...")
        count = sync_universities_to_mongodb()
        print(f"\n   ✓ Синхронизировано {count} университетов в MongoDB")
        
        # Проверка
        print("\n4. Проверка данных в MongoDB...")
        check_mongodb_data()
        
        print("\n" + "=" * 60)
        print("✓ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        
        # Вывод статистики по кафедрам
        print("\n📊 Детальная статистика:")
        total_departments = 0
        for univ in mongo_collection.find({}):
            for inst in univ.get('institutes', []):
                total_departments += len(inst.get('departments', []))
        
        print(f"  • Всего кафедр в MongoDB: {total_departments}")
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        pg_cur.close()
        pg_conn.close()
        mongo_client.close()


# ============================================================
# Запуск
# ============================================================


if __name__ == "__main__":
    main()