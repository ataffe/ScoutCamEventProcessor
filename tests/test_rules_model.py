import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from src.ml.rules_model import RuleEvaluationResult, RuleEvaluationInput


# --- RuleEvaluationResult ---

def test_result_stores_all_fields():
    result = RuleEvaluationResult(rule_public_id='abc-123', rule_name='Person Detection', is_triggered=True)
    assert result.rule_public_id == 'abc-123'
    assert result.rule_name == 'Person Detection'
    assert result.is_triggered is True


def test_result_is_triggered_can_be_false():
    result = RuleEvaluationResult(rule_public_id='abc', rule_name='Test', is_triggered=False)
    assert result.is_triggered is False


# --- RuleEvaluationInput ---

def test_input_stores_all_fields():
    inp = RuleEvaluationInput(rule_public_id='123', rule_name='Person Detection', rule='a person is present')
    assert inp.rule_public_id == '123'
    assert inp.rule_name == 'Person Detection'
    assert inp.rule == 'a person is present'


# --- RuleEvaluationInput.from_rule_entity ---

def test_from_rule_entity_maps_fields_correctly():
    rule_id = uuid4()
    mock_rule = MagicMock()
    mock_rule.public_rule_id = rule_id
    mock_rule.rule_nickname = 'Person Detection'
    mock_rule.rule = 'a person is present'

    result = RuleEvaluationInput.from_rule_entity(mock_rule)

    assert result.rule_public_id == str(rule_id)
    assert result.rule_name == 'Person Detection'
    assert result.rule == 'a person is present'


def test_from_rule_entity_converts_uuid_to_string():
    mock_rule = MagicMock()
    mock_rule.public_rule_id = uuid4()
    mock_rule.rule_nickname = 'Test'
    mock_rule.rule = 'a test rule'

    result = RuleEvaluationInput.from_rule_entity(mock_rule)

    assert isinstance(result.rule_public_id, str)
