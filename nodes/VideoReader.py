import os # work with files(checking is there file or not)
import json # reading json files with roads
import time 
import logging # логирование вывод предупреждений
from typing import Generator # тип для функции, которая использует yield
# Generator из модуля typing — это тип для функций, которые используют yield, то есть для генераторов
# Генератор — это функция, которая возвращает значения по одному, а не сразу все.
# Функция с yield возвращает генератор-объект, а не список: <generator object ...>
import cv2

from elements.FrameElement import FrameElement 
from elements.VideoEndBreakElement import VideoEndBreakElement 
# логгер для вывода ошибок в случае если видео не найден или не может быть прочитано
logger = logging.getLogger(__name__) # logger for output mistakes 

class VideoReader:
    """Модуль для чтения кадров с видеопотока"""

    def __init__(self, config: dict) -> None:
        self.video_path = config["src"]
        self.video_source = f"Processing of {self.video_path}"
        '''assert — это проверка (утверждение):
        Если True → программа идёт дальше
        Если False → выбрасывается ошибка AssertionError 
        Должно быть хотя бы одно True'''
        assert (
            os.path.isfile(self.video_path) # существует ли источник видео (self.video_path)
            or type(self.video_path) == int  # число ли это проверяем елси число то это веб камера или вторая камера
            or "://" in self.video_path # или это ссылка (rtsp/http) 
        ), f"VideoReader| File {self.video_path} not found" # иначе будет ошибкой и программа остановится 
 
        self.stream = cv2.VideoCapture(self.video_path)
        # сколько секунд пропускать между кадрами
        self.skip_secs = config["skip_secs"]
        self.last_frame_timestamp = -1 #время последнего кадра Почему значение = -1 - "мы ещё не обработали ни одного кадра"
        self.first_timestamp = 0 # Значение времени в момент первого кадра потока

        self.break_element_sent = False # Был ли отправлен элемент прерывания видеопотока

        # устанавливаем ширину и высоту если это видео-камеры (на входе int значение номера камеры)
        if type(self.video_path) == int:
            self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # Чтение данных из файла JSON (информация о координатах въезда и выезда дорог)
        with open(config["roads_info"], "r") as file:
            data_json = json.load(file)
        # Преобразование данных координат дорог в формат int
        self.roads_info = {
            key: [int(value) for value in values] for key, values in data_json.items()
        }
        
    # FrameElement → что выдаём - None → ничего не принимаем через .send() - None → ничего не возвращаем через return
    # (возвращает кадры по одному
    def process(self) -> Generator[FrameElement, None, None]:
        # номер кадра текущего видео
        frame_number = 0 

        while True:
            ret, frame = self.stream.read()
            if not ret: 
                # просто пишем в лог: "видео закончилось"
                logger.warning("Can't receive frame (stream end?). Exiting ...")
                # если ещё не отправили сигнал
                if not self.break_element_sent:
                    self.break_element_sent = True 
                    # отправим VideoEndBreakElement чтобы обозначить окончание потока
                    # yield - отдаёт объект, но функция может продолжить или завершиться позже
                    yield VideoEndBreakElement(self.video_path, self.last_frame_timestamp)
                break
            
            # # Вычисление timestamp в случае если вытягиваем с видоса rtsp или камеры (стартуем с 0 сек)
            if type(self.video_path) == int or "://" in self.video_path:
                # запоминаем время начала
                if frame_number == 0:
                    self.first_timestamp = time.time()
                # считаем время с начала
                timestamp = time.time() - self.first_timestamp 
            # если видео файл → берём время из видео
            else: 
                # self.stream.get(...) Это функция OpenCV: 👉 она спрашивает у видео: “на какой позиции ты сейчас находишься?”
                # cv2.CAP_PROP_POS_MSEC Это константа OpenCV: означает: текущее время видео в миллисекундах
                # ТО ЕСТЬ ПОЛУЧИМ текущее время кадра в видео (в секундах)"
                timestamp = self.stream.get(cv2.CAP_PROP_POS_MSEC) / 1000
            # Если новый кадр пришёл слишком быстро после предыдущего - просто игнорируем его
            if abs(self.last_frame_timestamp - timestamp) < self.skip_secs:
                continue 

            self.last_frame_timestamp = timestamp 

            frame_number += 1 

            yield FrameElement(self.video_source, frame, timestamp, frame_number, self.roads_info)

                
            
