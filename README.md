# Traffic Analyzer

Traffic Analyzer is a computer vision pipeline for vehicle detection, tracking, and traffic analytics. The project processes a road video, assigns stable track IDs to vehicles, calculates per-road activity, writes statistics to PostgreSQL, and visualizes metrics in Grafana.

## Demo

### Tracking window

Place the application screenshot here:

![Tracking window](docs/screenshots/tracking-window.png)

The tracking window shows detected vehicles, track IDs, road ROI polygons, FPS, total vehicle count, and traffic activity by road.

### Grafana dashboard

Place the Grafana screenshot here:

![Grafana dashboard](docs/screenshots/grafana-dashboard.png)

The dashboard can be imported from [`utils_local/dashboard_configuration.json`](utils_local/dashboard_configuration.json).

## Features

- Vehicle detection with YOLOv8.
- Multi-object tracking with ByteTrack.
- ROI-based road analytics from configurable polygons.
- Real-time OpenCV visualization with tracking IDs and statistics.
- PostgreSQL storage for time-series traffic metrics.
- Grafana dashboard for monitoring vehicle count and traffic congestion.

## Project Structure

```text
traffic_analyzer/
|-- byte_tracker/                 # ByteTrack implementation
|-- configs/
|   |-- app_config.yaml           # Main Hydra config
|   `-- entry_exit_lanes.json     # Road ROI polygons
|-- docs/screenshots/             # README screenshots
|-- elements/                     # Pipeline data objects
|-- nodes/                        # Pipeline processing nodes
|-- utils_local/
|   `-- dashboard_configuration.json
|-- docker-compose.yaml           # PostgreSQL + Grafana services
|-- main.py                       # Application entry point
|-- requirements.txt
`-- run_services.bat              # Windows helper for Docker services
```

## Requirements

- Python 3.11+
- Docker Desktop
- NVIDIA GPU is recommended for fast YOLO inference, but CPU mode can work for small tests.

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv env
env\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create local environment variables:

```bash
copy .env.example .env
```

Edit `.env` and replace `change_me` values with local passwords. The `.env` file is ignored by Git.

4. Add local assets:

```text
weights/yolov8m.pt
test_videos/test_video.mp4
```

Large model weights and videos are intentionally not stored in Git.

## Run Services

Start PostgreSQL and Grafana:

```bash
docker compose -p traffic_analyzer up -d
```

or on Windows:

```bash
run_services.bat
```

Default local addresses:

- PostgreSQL with traffic data: `localhost:5488`
- Grafana: `http://localhost:3111`

## Run Analyzer

```bash
python main.py
```

Main runtime settings are in [`configs/app_config.yaml`](configs/app_config.yaml):

- `video_reader.src` - input video path
- `detection_node.weight_pth` - YOLO weights path
- `pipeline.sent_info_db` - write analytics to PostgreSQL
- `show_node.imshow` - show OpenCV tracking window
- `show_node.show_info_statistics` - show statistics panel next to video

## Grafana Setup

1. Open `http://localhost:3111`.
2. Log in with values from `.env`:
   - `GRAFANA_ADMIN_USER`
   - `GRAFANA_ADMIN_PASSWORD`
3. Add a PostgreSQL data source:
   - Host: `pg_data_wh:5432`
   - Database: value of `POSTGRES_DB`
   - User: value of `POSTGRES_USER`
   - Password: value of `POSTGRES_PASSWORD`
   - TLS/SSL mode: disable
4. Import dashboard JSON from:

```text
utils_local/dashboard_configuration.json
```

## Screenshots of the project

```text
docs/screenshots/tracking.png
docs/screenshots/grafana.png
```


