-- Отключаем проверку внешних ключей для безопасного удаления
SET session_replication_role = replica;

-- Удаляем партицированные таблицы
DROP TABLE IF EXISTS attendance_w2026_02_09 CASCADE;
DROP TABLE IF EXISTS attendance_w2026_02_16 CASCADE;
DROP TABLE IF EXISTS attendance_w2026_02_23 CASCADE;
DROP TABLE IF EXISTS attendance_w2026_03_02 CASCADE;
DROP TABLE IF EXISTS attendance_w2026_03_09 CASCADE;
DROP TABLE IF EXISTS attendance_w2026_03_16 CASCADE;

-- Удаляем основную партицированную таблицу
DROP TABLE IF EXISTS attendance CASCADE;

-- Удаляем все таблицы в правильном порядке
DROP TABLE IF EXISTS schedule CASCADE;
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS lecture_materials CASCADE;
DROP TABLE IF EXISTS lectures CASCADE;
DROP TABLE IF EXISTS lecture_courses CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS student_groups CASCADE;
DROP TABLE IF EXISTS department_specialties CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
DROP TABLE IF EXISTS institutes CASCADE;
DROP TABLE IF EXISTS universities CASCADE;
DROP TABLE IF EXISTS specialties CASCADE;

-- Включаем обратно проверку внешних ключей
SET session_replication_role = DEFAULT;