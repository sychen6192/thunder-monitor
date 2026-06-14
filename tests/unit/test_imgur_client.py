from unittest.mock import patch
from infrastructure.imgur_client import ImgurClient


def test_upload_image_success_returns_link(tmp_path):
    img = tmp_path / "crop.jpg"
    img.write_bytes(b"fake-bytes")
    with patch("infrastructure.imgur_client.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"data": {"link": "https://i.imgur.com/x.jpg"}}
        client = ImgurClient("client-id")
        assert client.upload_image(str(img)) == "https://i.imgur.com/x.jpg"
        mock_post.assert_called_once()
        assert mock_post.call_args[1]["headers"]["Authorization"] == "Client-ID client-id"


def test_upload_image_api_failure_returns_none(tmp_path):
    img = tmp_path / "crop.jpg"
    img.write_bytes(b"fake-bytes")
    with patch("infrastructure.imgur_client.requests.post") as mock_post:
        mock_post.side_effect = Exception("boom")
        client = ImgurClient("client-id")
        assert client.upload_image(str(img)) is None


def test_upload_image_missing_file_returns_none():
    client = ImgurClient("client-id")
    assert client.upload_image("/no/such/file.jpg") is None
