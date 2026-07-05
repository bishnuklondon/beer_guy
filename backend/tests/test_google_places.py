from unittest.mock import Mock, patch

from backend.app.google_places import fetch_pub_records_from_google


def test_fetch_pub_records_from_google_uses_text_search_payload() -> None:
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "places": [
            {
                "displayName": {"text": "The Red Lion"},
                "formattedAddress": "1 High Street",
                "rating": 4.5,
                "websiteUri": "https://example.com",
            }
        ]
    }

    with patch("backend.app.google_places.requests.post", return_value=mock_response) as mock_post:
        records = fetch_pub_records_from_google("SS9", "Leigh-on-Sea", 51.5, 0.1, 5)

    assert len(records) == 1
    assert records[0]["name"] == "The Red Lion"
    assert records[0]["address"] == "1 High Street"
    assert records[0]["rating"] == 4.5
    assert records[0]["website_link"] == "https://example.com"
    mock_post.assert_called_once()
