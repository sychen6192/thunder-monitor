from unittest.mock import Mock, patch

from services.alert_service import AlertService


def _config():
    return {
        "AREAS": [[23.0, 22.0, 120.0, 121.0]],
        "CWB_TOKEN": "w",
        "TELEGRAM_TOKEN": "t",
        "TELEGRAM_CHAT_ID": "c",
        "LINE_CHANNEL_ACCESS_TOKEN": "la",
        "LINE_TO": "U1",
        "IMGUR_CLIENT_ID": "ic",
        "LOG": "./log/x.log",
    }


def test_init_builds_manager_with_telegram_and_line():
    service = AlertService(_config())
    names = [type(n).__name__ for n in service.notifier.notifiers]
    assert names == ["TelegramNotifier", "LineNotifier"]


def test_init_without_imgur_id_leaves_line_without_imgur():
    config = _config()
    del config["IMGUR_CLIENT_ID"]
    service = AlertService(config)
    assert service.notifier.notifiers[1].imgur_client is None


def test_run_sends_new_alerts(sample_alert):
    with patch("services.alert_service.file_repo") as file_repo, \
         patch("services.alert_service.cwb_client"), \
         patch("services.alert_service.image_processor") as image_processor, \
         patch("services.alert_service.is_alert_valid") as is_valid:
        file_repo.load_alerts.return_value = []
        is_valid.return_value = [sample_alert]

        service = AlertService(_config())
        service.notifier = Mock()
        service.run()

        image_processor.download_thunder_img.assert_called_once_with("crop.jpg")
        service.notifier.send_all.assert_called_once_with(sample_alert, "crop.jpg")
        file_repo.save_alerts.assert_called_once_with([sample_alert])


def test_run_clearance_sends_message(sample_alert):
    with patch("services.alert_service.file_repo") as file_repo, \
         patch("services.alert_service.cwb_client"), \
         patch("services.alert_service.image_processor"), \
         patch("services.alert_service.is_alert_valid") as is_valid:
        file_repo.load_alerts.return_value = [sample_alert]
        is_valid.return_value = []

        service = AlertService(_config())
        service.notifier = Mock()
        service.run()

        file_repo.reset_alerts.assert_called_once()
        service.notifier.send_message_all.assert_called_once_with("⚠️ 雷擊警報解除", "crop.jpg")
