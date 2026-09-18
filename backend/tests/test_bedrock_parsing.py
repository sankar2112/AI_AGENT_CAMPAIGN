from app.services.bedrock import _mock_generation, _parse_json


def test_parse_json_from_fenced_block():
    payload = _parse_json('```json\n{"subject": "Hi", "propensity": 0.4}\n```')
    assert payload["subject"] == "Hi"
    assert payload["propensity"] == 0.4


def test_parse_json_falls_back_to_raw_text():
    payload = _parse_json("no json here")
    assert payload["body"] == "no json here"


def test_mock_generation_respects_sms_limit():
    generation = _mock_generation({"channel": "sms", "first_name": "Aarav", "product": "Term Plan", "customer_id": 1})
    assert len(generation.body) <= 320
    assert generation.provider == "mock"
