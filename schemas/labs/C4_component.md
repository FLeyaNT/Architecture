
'''plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

' LAYOUT_WITH_LEGEND()

Person(user, "Пользователь", "Внешний запрос с JWT токеном")

System_Boundary(university_system, "Информационная система университетов") {
    Container(api_gateway, "API Gateway", "Python", "Маршрутизация запросов, JWT валидация, аутентификация")

    Container(lab1_service, "Lab1 Service", "Python", "Отчёт о 10 студентах с минимальным процентом посещения лекций")
    Container(lab2_service, "Lab2 Service", "Python", "Отчёт по заданному курсу")
    Container(lab3_service, "Lab3 Service", "Python", "Отчёт по заданной группе учащихся")
}

ContainerDb(redis, "Redis", "Redis", "Данные о студентах")
ContainerDb(elasticsearch, "Elasticsearch", "Elasticsearch", "Полнотекстовый поиск по лекциям")
ContainerDb(postgresql, "PostgreSQL", "PostgreSQL", "Все данные")
ContainerDb(neo4j, "Neo4j", "Neo4j", "Граф связей курсов, занятий, лекций, групп, студентов и специальностей")
ContainerDb(mongodb, "MongoDB", "MongoDB", "Документы университет → институт → кафедра")

System_Boundary(generator_system, "Система генерации данных") {
    Container(generator, "Генератор данных", "Python", "Генерация тестовых данных")
}

Rel(user, api_gateway, "HTTP + JWT", "JSON")
Rel(api_gateway, lab1_service, "Маршрутизация Lab1", "HTTP/JSON")
Rel(api_gateway, lab2_service, "Маршрутизация Lab2", "HTTP/JSON")
Rel(api_gateway, lab3_service, "Маршрутизация Lab3", "HTTP/JSON")

' Lab1 connections
Rel(lab1_service, redis, "")
Rel(lab1_service, elasticsearch, "")
Rel(lab1_service, neo4j, "")
Rel(lab1_service, postgresql, "")

' Lab2 connections
Rel(lab2_service, neo4j, "")

' Lab3 connections
Rel(lab3_service, redis, "")
Rel(lab3_service, neo4j, "")
Rel(lab3_service, postgresql, "")

' Generator connections
Rel(user, generator, "")
Rel(generator, postgresql, "")
Rel(generator, redis, "")
Rel(generator, neo4j, "")
Rel(generator, mongodb, "")
Rel(generator, elasticsearch, "")
@enduml
'''
