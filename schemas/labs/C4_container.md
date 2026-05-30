# C4 уровня котнейнеров (уровень 2)


<img width="782" height="532" alt="image" src="https://github.com/user-attachments/assets/e2223ff8-6fe2-463c-8c3b-6bf6f3f8aecf" />


```plantuml
@startuml C2_Lab_System_Container
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

' LAYOUT_WITH_LEGEND()

Person(user, "Пользователь", "Внешний запрос с JWT токеном")

System_Boundary(university_system, "Информационная система университетов") {
    Container(reporting_system, "Система отчётности")
}

ContainerDb(redis, "Redis", "Redis")
ContainerDb(elasticsearch, "Elasticsearch", "Elasticsearch")
ContainerDb(postgresql, "PostgreSQL", "PostgreSQL")
ContainerDb(neo4j, "Neo4j", "Neo4j")
ContainerDb(mongodb, "MongoDB", "MongoDB")

System_Boundary(generator_system, "Система генерации данных") {
    Container(generator, "Генератор данных")
}

Rel(user, reporting_system, "HTTP + JWT", "JSON")
Rel(user, generator, "")

Rel(reporting_system, redis, "")
Rel(reporting_system, elasticsearch, "")
Rel(reporting_system, postgresql, "")
Rel(reporting_system, neo4j, "")
Rel(reporting_system, mongodb, "")

Rel(generator, postgresql, "")
Rel(generator, redis, "")
Rel(generator, neo4j, "")
Rel(generator, mongodb, "")
Rel(generator, elasticsearch, "")

@enduml
```
