import time 
import logging 
import psycopg2 

from elements.FrameElement import FrameElement 
from elements.VideoEndBreakElement import VideoEndBreakElement 
from utils_local.utils import profile_time 

# Создаётся логгер. __name__ = имя текущего файла.
logger = logging.getLogger(__name__)


class SentInfoDBNode:
    '''Модуль для отправки информации в базу данных'''

    def __init__(self, config) -> None:
        config_db = config["sent_info_db_node"] 
        self.how_often_add_info = config_db["how_often_add_info"] 
        self.table_name = config_db["table_name"]
        self.last_db_update = time.time() # время последнего обновления базы данных

        # устанавливаем соединение с базой данных
        db_connection = config_db["connection_info"]
        conn_params = {
            "user": db_connection["user"],
            "password": db_connection["password"],
            "host": db_connection["host"],
            "port": str(db_connection["port"]),
            "database": db_connection["database"],
        }

        self.buffer_analytics_sec = (
            config["general"]["buffer_analytics"] * 60 + 
            config["general"]["min_time_life_track"]
        ) # размер буфера для аналитики в секундах (время жизни трека + размер буфера в минутах)

        try: 
            # **conn_params распаковывает словарь:
            self.connection = psycopg2.connect(**conn_params) 
            print("Connected to PostgreSQL")
        # «Если внутри try произошла ошибка типа Exception ИЛИ psycopg2.Error, то сохрани эту ошибку в переменную error».
        except (Exception, psycopg2.Error) as error:
            print("Error while connecting to PostgreSQL:", error)
            raise RuntimeError(
                "Could not connect to PostgreSQL. Check .env values and Docker services."
            ) from error
        
        # Курсор — это объект, через который Python отправляет SQL-команды в PostgreSQL.
        self.cursor = self.connection.cursor() # создаём курсор для выполнения SQL-запросов
        # Через него выполняются: CREATE TABLE, INSERT, SELECT, DELETE
        # sql-запрос для удаления таблицы, если она уже существует (для очистки данных при каждом запуске)
        drop_table_query = f"DROP TABLE IF EXISTS {self.table_name};"

        try: 
            self.cursor.execute(drop_table_query) # выполняем запрос на удаление таблицы
            self.connection.commit() # сохраняем изменения в базе данных
        except (Exception, psycopg2.Error) as error:
            logger.error(f"Error while dropping table: {error}") # логируем ошибку, если не удалось удалить таблицу

        # sql-запрос для создания новой таблицы для хранения информации (если её нет)
        create_table_query = f"""
        CREATE TABLE {self.table_name} (
            id SERIAL PRIMARY KEY,
            timestamp INTEGER,
            timestamp_date TIMESTAMP,
            cars INTEGER,
            road_1 FLOAT,
            road_2 FLOAT,
            road_3 FLOAT,
            road_4 FLOAT,
            road_5 FLOAT);"""

        try:
            self.cursor.execute(create_table_query)
            self.connection.commit() 
            logger.info(
                f"Table {self.table_name} created successfully"
            )
        except (Exception, psycopg2.Error) as error:
            logger.error(f"Error while creating table: {error}")
    

    @profile_time 
    def process(self, frame_element: FrameElement) -> FrameElement:
        if isinstance(frame_element, VideoEndBreakElement):
            return frame_element 
        assert isinstance(
            frame_element, FrameElement
        ), f"SentInfoDBNode | неправильный формат входного элемента {type(frame_element)}"

        info_dictionary = frame_element.info 
        timestamp = frame_element.timestamp 
        timestamp_date = time.time() 

        # 
        current_time = time.time()
        if current_time - self.last_db_update >= self.how_often_add_info:
            self._insert_in_db(info_dictionary, timestamp, timestamp_date)
            frame_element.send_info_of_frame_to_db = True 
            self.last_db_update = current_time 

        return frame_element
    
    
    def _insert_in_db(self, info_dictionary: dict, timestamp: float, timestamp_date: float) -> None:
        insert_query = (
            f"INSERT INTO {self.table_name} "
            "(timestamp, timestamp_date, cars, road_1, road_2, road_3, road_4, road_5) "
            "VALUES (%s, to_timestamp(%s), %s, %s, %s, %s, %s, %s)"
        )
        try:
            self.cursor.execute(
                insert_query,
                (
                    timestamp,
                    timestamp_date, 
                    info_dictionary["cars_amount"],
                    info_dictionary["roads_activity"][1] if timestamp >= self.buffer_analytics_sec else None,
                    info_dictionary["roads_activity"][2] if timestamp >= self.buffer_analytics_sec else None,
                    info_dictionary["roads_activity"][3] if timestamp >= self.buffer_analytics_sec else None,
                    info_dictionary["roads_activity"][4] if timestamp >= self.buffer_analytics_sec else None,
                    info_dictionary["roads_activity"][5] if timestamp >= self.buffer_analytics_sec else None,
                )
            )
            self.connection.commit()
            logger.info(
                f"successfully inserted data into PostgreSQL"
            )
        except (Exception, psycopg2.Error) as error:
            logger.error(f"Error while inserting data into PostgreSQL: {error}")
