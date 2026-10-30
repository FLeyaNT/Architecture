# Маппинг ElasticSearch

ElasticSearch 7.17 хранит тексты материалов занятий для полнотекстового
поиска.

## Настройки и маппинг

```json
PUT /lecture_materials
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "filter": {
        "russian_stop":    { "type": "stop",    "stopwords": "_russian_" },
        "russian_stemmer": { "type": "stemmer", "language": "russian" }
      },
      "analyzer": {
        "russian_custom": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "russian_stop", "russian_stemmer"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "id":           { "type": "keyword" },
      "lecture_id":   { "type": "keyword" },
      "title": {
        "type": "text",
        "analyzer": "russian_custom",
        "fields": { "keyword": { "type": "keyword", "ignore_above": 512 } }
      },
      "content_text": { "type": "text", "analyzer": "russian_custom" }
    }
  }
}
```

| Поле | Тип | Зачем |
|---|---|---|
| `id` | keyword | id материала, совпадает с `_id` |
| `lecture_id` | keyword | Связь с занятием: по нему агрегация `terms` в ЛР1 |
| `title` | text (`russian_custom`) + `title.keyword` | Поиск по заголовку; точное значение — для сортировки и агрегаций |
| `content_text` | text (`russian_custom`) | Основной текст для поиска |
