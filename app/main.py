from services.alert_service import AlertService
from infrastructure.config import load_config
from loguru import logger


def main() -> None:
    try:
        config = load_config("STAGE")
        logger.add(config["LOG"], rotation="1 week")
        service = AlertService(config)
        service.run()
    except Exception as e:
        logger.exception(e)


if __name__ == "__main__":
    main()