# эта библиотека загружает yaml конфиг, передает параметры в код, все свои настройки там реализуем а здесь просто берем оттуда
import os
from pathlib import Path

import hydra 
# через ноды мы реализуем разных логик отдельно и потом всех их соберем здесь 
# эффективно если будем добавить новые логики то в нодах и напишем и здесь импортируем не меняем весь код 
from nodes.VideoReader import VideoReader 
from nodes.ShowNode import ShowNode 
from nodes.VideoSaverNode import VideoSaverNode
from nodes.DetectionTrackingNodes import DetectionTrackingNodes
from nodes.TrackerInfoUpdateNode import TrackerInfoUpdateNode
from nodes.CalcStatisticsNode import CalcStatisticsNode
from nodes.SentInfoDBNode import SentInfoDBNode 


def load_local_env(env_path=".env") -> None:
    env_file = Path(env_path)
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_local_env()

# Декоратор Hydra - ищет файл в текущем папке проекта: configs/app_config.yaml - загружает его и передаёт в функцию:
# version_base - указываем какую версию hydra использовать если None то используем по умолчанию текущую версию 
# декоратор это обертка над функцией то есть 
'''
@something()
def main():
    pass 
означает something(main)
находим где конфиг файл читает yaml превращает в объект config 
передает в функцию, но это не просто dict это объект хидра. но можем использовать как словарь
'''
@hydra.main(version_base=None, config_path="configs", config_name="app_config")
# -> None = ничего не возвращаем
def main(config) -> None:
    video_reader = VideoReader(config["video_reader"])
    detection_node = DetectionTrackingNodes(config)
    tracker_info_update_node = TrackerInfoUpdateNode(config)
    calc_statistics_node = CalcStatisticsNode(config)
    show_node = ShowNode(config)
    video_saver_node = VideoSaverNode(config["video_saver_node"])

    save_video = config["pipeline"]["save_video"]
    sent_info_db = config["pipeline"]["sent_info_db"]
    
    # инициализируем базу данных для него ноду создаем
    if sent_info_db:
        sent_info_db_node = SentInfoDBNode(config)
    
    # 
    for frame_element in video_reader.process():
        frame_element = detection_node.process(frame_element)
        frame_element = tracker_info_update_node.process(frame_element)
        frame_element = calc_statistics_node.process(frame_element)

        if sent_info_db:
            frame_element = sent_info_db_node.process(frame_element)
        
        frame_element = show_node.process(frame_element)

        if save_video:
            video_saver_node.process(frame_element)


if __name__ == "__main__":
    main()





