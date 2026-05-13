@REM Это командный файл для Windows, который автоматизирует подготовку и запуск всей твоей системы.
REM  
mkdir .\services\pg_data_wh
mkdir .\services\pg_grafana
mkdir .\services\grafana

REM 
@REM docker-compose — обращение к инструменту, который управляет группой контейнеров.
@REM -p traffic_analyzer — флаг project name. Он дает твоей группе контейнеров красивое имя «traffic_analyzer» в списке Docker Desktop. Если этот флаг не указывать, Docker назовет проект просто по имени папки, где лежит файл.
@REM up — команда «поднять» все сервисы, описанные в файле docker-compose.yaml.
@REM -d — сокращение от detached (фоновый режим). Это значит, что после запуска контейнеров терминал не «зависнет», показывая бесконечные логи базы данных, а сразу освободится для дальнейшей работы. Контейнеры будут тихо работать в фоне.
docker-compose -p traffic_analyzer up -d