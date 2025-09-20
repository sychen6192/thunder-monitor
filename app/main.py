from services.alert_service import AlertService
from infrastructure.config import load_config
from loguru import logger
import argparse

def main() -> None:
    try:
        config = load_config(env=parse_args())
        logger.add(config["LOG"], rotation="1 week")
        service = AlertService(config)
        service.run()
    except Exception as e:
        logger.exception(e)

def parse_args() -> str:
    parser = argparse.ArgumentParser(description="Thunder Monitor")
    parser.add_argument("--env", default="PROD", choices=["PROD", "STAGE"], help="Environment config")
    args = parser.parse_args()
    return args.env

if __name__ == "__main__":
    main()