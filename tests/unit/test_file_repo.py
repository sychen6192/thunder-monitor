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

    # Negative tests for error conditions
    def test_load_alerts_invalid_json(self, tmp_path):
        """Test loading alerts from file with invalid JSON."""
        # Arrange
        alert_file = tmp_path / "alert.txt"
        alert_file.write_text('{"invalid": json}\n{"category": "test", "occur_time": "2024-01-01", "latitude": 1.0, "longitude": 2.0}')

        # Act
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            result = load_alerts()

        # Assert - should skip invalid line and load valid one
        assert len(result) == 1
        assert result[0].category == "test"
        assert result[0].occur_time == "2024-01-01"
        assert result[0].latitude == 1.0
        assert result[0].longitude == 2.0

    def test_load_alerts_missing_fields(self, tmp_path):
        """Test loading alerts with missing required fields."""
        # Arrange
        alert_file = tmp_path / "alert.txt"
        # Missing longitude field
        alert_file.write_text('{"category": "test", "occur_time": "2024-01-01", "latitude": 1.0}')

        # Act
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            result = load_alerts()

        # Assert - should skip line with missing fields
        assert result == []

    def test_load_alerts_invalid_data_types(self, tmp_path):
        """Test loading alerts with invalid data types."""
        # Arrange
        alert_file = tmp_path / "alert.txt"
        # latitude should be float, but is string
        alert_file.write_text('{"category": "test", "occur_time": "2024-01-01", "latitude": "not-a-float", "longitude": 2.0}')

        # Act
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            result = load_alerts()

        # Assert - should skip line with invalid data types
        assert result == []

    def test_save_alerts_permission_error(self, sample_alerts, tmp_path):
        """Test that save_alerts raises PermissionError when file is not writable."""
        # Arrange
        alert_file = tmp_path / "alert.txt"
        # Make directory read-only to simulate permission error
        tmp_path.chmod(0o444)

        # Act & Assert
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            with pytest.raises(PermissionError):
                save_alerts(sample_alerts)

        # Clean up
        tmp_path.chmod(0o755)

    def test_load_alerts_permission_error(self, tmp_path):
        """Test that load_alerts raises PermissionError when file is not readable."""
        # Arrange
        alert_file = tmp_path / "alert.txt"
        alert_file.write_text('{"category": "test", "occur_time": "2024-01-01", "latitude": 1.0, "longitude": 2.0}')
        # Make file read-only to others (not owner)
        alert_file.chmod(0o600)

        # Change file ownership simulation by mocking permission error
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file), \
             patch('builtins.open', side_effect=PermissionError("Permission denied")):
            # Act & Assert
            with pytest.raises(PermissionError):
                load_alerts()

    def test_reset_alerts_permission_error(self, tmp_path):
        """Test that reset_alerts raises PermissionError when file is not writable."""
        # Arrange
        alert_file = tmp_path / "alert.txt"
        alert_file.write_text("test content")
        # Make file read-only
        alert_file.chmod(0o444)

        # Act & Assert
        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            with pytest.raises(PermissionError):
                reset_alerts()

        # Clean up
        alert_file.chmod(0o644)

    def test_save_alerts_empty_list_clears_file(self, sample_alerts, tmp_path):
        """Test that saving empty list calls reset_alerts to clear file."""
        # Arrange
        alert_file = tmp_path / "alert.txt"

        with patch('infrastructure.file_repo.ALERT_FILE', alert_file):
            # First save some alerts
            save_alerts(sample_alerts)
            assert alert_file.exists()
            assert alert_file.read_text(encoding='utf-8') != ""

            # Act: Save empty list
            save_alerts([])

            # Assert: File should be empty
            assert alert_file.read_text(encoding='utf-8') == ""