# Структура данных Redis

Redis 7 хранит кеш карточек студентов — копию таблицы `students`.

## Поля хеша `students:{id}`

Все значения — строки (так пишет и коннектор, и генератор).

| Поле | Пример | Исходная колонка |
|---|---|---|
| `id` | `3b2628be-1450-4e5b-a584-e91255b06753` | `id UUID` |
| `group_id` | `5b184e8c-7fcc-4867-8f80-5983a2007835` | `group_id UUID` |
| `last_name` | `Федосеев` | `last_name` |
| `first_name` | `Аскольд` | `first_name` |
| `patronymic` | `Васильевич` | `patronymic` (может отсутствовать) |
| `email` | `fedoseev.av1632@edu.mirea.ru` | `email` |
| `phone` | `+79383770585` | `phone` |
| `student_card_number` | `24Б0417` | `student_card_number` |
| `enrollment_date` | `2024-09-01Z` | `enrollment_date DATE` |
| `status` | `active` | `status` |
| `created_at` | `2026-10-28T18:18:20.841446Z` | `created_at` |
| `updated_at` | `2026-10-28T18:18:20.841446Z` | `updated_at` |

Хеш выбран вместо JSON-строки: поля читаются и обновляются по отдельности,
а коннектор записывает строку таблицы без дополнительной сериализации.
