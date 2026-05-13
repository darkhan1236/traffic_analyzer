import logging 
import os 
import time
import numpy as np 
from shapely.geometry import Point, Polygon # работа с геометрией: Point → точка, Polygon → многоугольник

logger_profile = logging.getLogger("profile")

def check_and_set_env_var(var_name, value_new):
    """
    Проверяет, установлена ли переменная окружения `var_name`. 
    если нет → создаёт"""
    value = os.getenv(var_name)
    if value is None:
        # Если переменная окружения не установлена, то устанавливаем её значение на value_new
        # создаём переменную
        os.environ[var_name] = str(value_new)
        print(f"Значение {value_new} сохраено в переменную окружения {var_name}.")
    else:
        print(f"Переменная {var_name} уже установлена: {value}")

# Декоратор для замера времени выполнения функции. 
def profile_time(func):
    # внутренняя функция это “обёртка” вокруг функции, которую мы декорируем. Она принимает любые аргументы и передаёт их в исходную функцию.
    def exec_and_print_status(*args, **kwargs):
        t_start = time.time() # время начала выполнения функции 
        out = func(*args, **kwargs) # выполнение функции и сохранение ее 
        t_end = time.time()
        dt_msecs = (t_end - t_start) * 100 # время выполнения функции в миллисекундах

        self = args[0] # первый аргумент функции - это self (экземпляр класса, которому принадлежит функция)
        logger_profile.debug(
            f"{self.__class__.__name__}.{func.__name__}, time spent {dt_msecs:.2f} msecs"
        )
        return out 
    # возвращаем внутреннюю функцию, которая будет вызываться вместо исходной функции при её декорировании
    # если без () то мы возвращаем функцию, а не результат её выполнения 
    return exec_and_print_status 


class FPS_Counter:
    def __init__(self, calc_time_perion_N_frames: int) -> None:
        """Счетчик FPS по ограниченным участкам видео
         Args:
            calc_time_perion_N_frames (int): количество фреймов окна подсчета статистики.
        """
        self.time_buffer = [] # буфер для хранения времени обработки последних N кадров
        self.calc_time_perion_N_frames = calc_time_perion_N_frames # количество кадров для расчета FPS

    def calc_FPS(self) -> float:
        """Производит рассчет FPS по нескольким кадрам видео. 
        Returns:
            float: значение FPS.
        """
        time_buffer_is_full = len(self.time_buffer) == self.calc_time_perion_N_frames 
        t = time.time() 
        self.time_buffer.append(t)
        if time_buffer_is_full:
            self.time_buffer.pop(0) # удаляем самое старое время из буфера, чтобы он всегда содержал только последние N времен обработки кадров
            fps = len(self.time_buffer) / (self.time_buffer[-1] - self.time_buffer[0])
            return np.round(fps, 2) # округляем FPS до 2 знаков после запятой
        else: 
            return 0.0 # если буфер не заполнен, то возвращаем 0 FPS (потому что у нас ещё нет данных для расчета)
            

def intersects_central_point(tracked_xyxy, polygons):
    """Проверяет пересечение центральной точки трека с полигонами дорог. 
    Args:
        tracked_xyxy (list): координаты трека в формате [x1, y1, x2, y2].
        polygons (dict): словарь с информацией о дорогах и их полигонах.
    Returns:
        str or None: название дороги, если есть пересечение, иначе None.
    """
    # Вычисляем центральную точку трека
    center_point = [
        (tracked_xyxy[0] + tracked_xyxy[2]) / 2, # x центральной точки
        (tracked_xyxy[1] + tracked_xyxy[3]) / 2, # y центральной точки
    ]
    center_point = Point(center_point) # преобразуем в объект Point для работы с геометрией с ней можно делать:
    # внутри ли полигона, пересекается ли, расстояния и т.д.
    for key, polygon in polygons.items():
        polygon = Polygon([(polygon[i], polygon[i + 1]) for i in range(0, len(polygon), 2)]) # преобразуем список координат в объект Polygon для работы с геометрией 
        if polygon.contains(center_point):
            return int(key) # если центральная точка трека находится внутри полигона дороги, возвращаем номер дороги (ключ из словаря)
    return None
