from pii_masking.masker import mask_event_data, mask_string


def test_pii__pan_masked() -> None:
    result = mask_string("PAN: ABCDE1234F")
    assert "ABCDE1234F" not in result
    assert "AB" in result
    assert "F" in result


def test_pii__aadhaar_masked() -> None:
    result = mask_string("Aadhaar: 1234 5678 9012")
    assert "1234 5678 9012" not in result
    assert "XXXX" in result


def test_pii__sensitive_keys_redacted() -> None:
    data = {
        "symbol": "RELIANCE",
        "password": "secret123",
        "api_key": "my-api-key",
        "totp_secret": "JBSWY3DPEHPK3PXP",
        "price": "2500",
    }
    masked = mask_event_data(data)
    assert masked["symbol"] == "RELIANCE"
    assert masked["password"] == "***REDACTED***"
    assert masked["api_key"] == "***REDACTED***"
    assert masked["totp_secret"] == "***REDACTED***"
    assert masked["price"] == "2500"


def test_pii__nested_dict_masked() -> None:
    data = {
        "order": {
            "symbol": "INFY",
            "session_token": "abc123",
        }
    }
    masked = mask_event_data(data)
    assert masked["order"]["symbol"] == "INFY"
    assert masked["order"]["session_token"] == "***REDACTED***"


def test_pii__no_sensitive_data__unchanged() -> None:
    data = {"symbol": "TCS", "quantity": 10, "price": "3500.50"}
    masked = mask_event_data(data)
    assert masked == data
