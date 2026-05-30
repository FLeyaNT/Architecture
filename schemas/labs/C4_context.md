# C4 уровня контекста (уровень 1)


<img width="716" height="491" alt="image" src="https://github.com/user-attachments/assets/59f41739-8a94-4097-a893-cb7bc0063c10" />


```plantuml
@startuml C1_Lab_System_Context
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml

' LAYOUT_WITH_LEGEND()

Person(user, "Пользователь")

System_Boundary(university_system, "Информационная система университетов") {
    System(reporting_system, "Система отчётности")
}

SystemDb(data_storage_system, "Система хранения данных")

System_Boundary(generator_system, "Система генерации данных") {
    System(data_generator, "Генератор данных")
}

Rel(user, reporting_system, "Запросы отчётов")
Rel(user, data_generator, "")
Rel(reporting_system, data_storage_system, "Запрос данных")
Rel(data_generator, data_storage_system, "Генерация и загрузка данных")

@enduml
```
