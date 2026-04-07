import pytest
import json
from pathlib import Path
from unittest.mock import mock_open, patch
from infrastructure.file_repo import save_alerts, load_alerts, reset_alerts, ALERT_FILE


class TestFileRepo:
    """Test suite for file_repo.py functions."""

    def test_save_alerts_writes_correct_format(self, sample_alerts, tmp_path):
        """Test that save_alerts writes alerts in JSON format."""
        # Arrange
        alert_file = tmp_path / "alert.txt"

        # Act
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            save_alerts(sample_alerts)

        # Assert
        assert alert_file.exists()
        content = alert_file.read_text(encoding='utf-8').strip().split('\n')
        assert len(content) == len(sample_alerts)

        # Verify each line is valid JSON and contains the alert data
        for i, line in enumerate(content):
            alert_dict = json.loads(line)
            assert alert_dict['category'] == sample_alerts[i].category
            assert alert_dict['occur_time'] == sample_alerts[i].occur_time
            assert alert_dict['latitude'] == sample_alerts[i].latitude
            assert alert_dict['longitude'] == sample_alerts[i].longitude

    def test_save_alerts_empty_list(self, tmp_path):
        """Test saving an empty list of alerts."""
        # Arrange
        alert_file = tmp_path / "alert.txt"

        # Act
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            save_alerts([])

        # Assert
        content = alert_file.read_text(encoding='utf-8')
        assert content == ""

    def test_load_alerts_returns_correct_alerts(self, sample_alerts, tmp_path):
        """Test that load_alerts correctly reads and parses saved alerts."""
        # Arrange
        alert_file = tmp_path / "alert.txt"
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            # Save alerts first
            save_alerts(sample_alerts)

            # Act
            loaded = load_alerts()

        # Assert
        assert len(loaded) == len(sample_alerts)
        for loaded_alert, original_alert in zip(loaded, sample_alerts):
            assert loaded_alert.category == original_alert.category
            assert loaded_alert.occur_time == original_alert.occur_time
            assert loaded_alert.latitude == original_alert.latitude
            assert loaded_alert.longitude == original_alert.longitude

    def test_load_alerts_empty_file(self, tmp_path):
        """Test loading alerts from an empty file."""
        # Arrange
        alert_file = tmp_path / "alert.txt"

        # Act
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            result = load_alerts()

        # Assert
        assert result == []

    def test_load_alerts_nonexistent_file(self, tmp_path):
        """Test loading alerts when file doesn't exist."""
        # Arrange
        alert_file = tmp_path / "nonexistent.txt"

        # Act
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            result = load_alerts()

        # Assert
        assert result == []

    def test_reset_alerts_clears_file(self, sample_alerts, tmp_path):
        """Test that reset_alerts clears the alert file."""
        # Arrange
        alert_file = tmp_path / "alert.txt"
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            # Save some alerts first
            save_alerts(sample_alerts)
            assert alert_file.exists()
            assert alert_file.read_text(encoding='utf-8') != ""

            # Act
            reset_alerts()

        # Assert
        assert alert_file.read_text(encoding='utf-8') == ""

    def test_reset_alerts_empty_file(self, tmp_path):
        """Test reset_alerts on an already empty file."""
        # Arrange
        alert_file = tmp_path / "alert.txt"
        alert_file.write_text("")

        # Act
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            reset_alerts()

        # Assert
        assert alert_file.read_text(encoding='utf-8') == ""

    def test_round_trip_save_and_load(self, sample_alerts, tmp_path):
        """Test that saving and then loading returns the same data."""
        # Arrange
        alert_file = tmp_path / "alert.txt"

        # Act
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            save_alerts(sample_alerts)
            loaded = load_alerts()

        # Assert
        assert len(loaded) == len(sample_alerts)
        for loaded_alert, original_alert in zip(loaded, sample_alerts):
            assert loaded_alert.category == original_alert.category
            assert loaded_alert.occur_time == original_alert.occur_time
            assert loaded_alert.latitude == original_alert.latitude
            assert loaded_alert.longitude == original_alert.longitude