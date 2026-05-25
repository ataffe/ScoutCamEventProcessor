import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from src.ml.gemma4_rules_model import Gemma4RulesModel
from src.ml.rules_model import RuleEvaluationInput


@pytest.fixture
def sample_rules():
    return [
        RuleEvaluationInput(
            rule_public_id='1',
            rule_name='Person Detection',
            rule='a person is present'),
        RuleEvaluationInput(
            rule_public_id='2',
            rule_name='Vehicle Detection',
            rule='a vehicle is present'),
    ]


@pytest.fixture
def sample_image():
    return Image.new('RGB', (100, 100), color=(128, 64, 32))


@pytest.fixture
def initialized_model():
    instance = Gemma4RulesModel(
        model_variant='test-variant', model_weights_dir='test_weights')
    instance.model = MagicMock()
    instance.processor = MagicMock()
    instance.processor.decode.return_value = 'yes'
    instance.processor.parse_response.return_value = {'content': 'yes'}
    return instance


# --- __init__ ---

def test_constructor_sets_variant_and_weights_dir():
    model = Gemma4RulesModel(
        model_variant='gemma4-e2b-it', model_weights_dir='ml_weights')
    assert model.variant == 'gemma4-e2b-it'
    assert model.weights_dir == 'ml_weights'


def test_constructor_leaves_model_and_processor_as_none():
    model = Gemma4RulesModel(model_variant='test', model_weights_dir='test')
    assert model.model is None
    assert model.processor is None


# --- init(): weight downloading ---

def test_init_skips_download_when_weights_are_present(tmp_path):
    (tmp_path / 'model.safetensors').touch()
    model = Gemma4RulesModel(
        model_variant='test-variant', model_weights_dir=str(tmp_path))
    with patch('src.ml.gemma4_rules_model.AutoModelForCausalLM'), \
         patch('src.ml.gemma4_rules_model.AutoProcessor'), \
         patch('src.ml.gemma4_rules_model.download_weights_s3') as mock_dl:
        model.init()
    mock_dl.assert_not_called()


def test_init_downloads_weights_when_dir_does_not_exist(tmp_path):
    weights_dir = str(tmp_path / 'nonexistent')
    model = Gemma4RulesModel(
        model_variant='test-variant', model_weights_dir=weights_dir)
    with patch('src.ml.gemma4_rules_model.AutoModelForCausalLM'), \
         patch('src.ml.gemma4_rules_model.AutoProcessor'), \
         patch('src.ml.gemma4_rules_model.download_weights_s3') as mock_dl:
        model.init()
    mock_dl.assert_called_once_with('gemma4', 'test-variant', weights_dir)


def test_init_downloads_weights_when_dir_is_empty(tmp_path):
    model = Gemma4RulesModel(
        model_variant='test-variant', model_weights_dir=str(tmp_path))
    with patch('src.ml.gemma4_rules_model.AutoModelForCausalLM'), \
         patch('src.ml.gemma4_rules_model.AutoProcessor'), \
         patch('src.ml.gemma4_rules_model.download_weights_s3') as mock_dl:
        model.init()
    mock_dl.assert_called_once_with('gemma4', 'test-variant', str(tmp_path))


# --- init(): model loading ---

def test_init_loads_model_with_bfloat16_and_auto_device_map(tmp_path):
    (tmp_path / 'model.safetensors').touch()
    model = Gemma4RulesModel(
        model_variant='test-variant', model_weights_dir=str(tmp_path))
    with patch('src.ml.gemma4_rules_model.AutoModelForCausalLM') as mock_cls, \
         patch('src.ml.gemma4_rules_model.AutoProcessor'), \
         patch('src.ml.gemma4_rules_model.torch') as mock_torch, \
         patch('src.ml.gemma4_rules_model.download_weights_s3'):
        model.init()
    mock_cls.from_pretrained.assert_called_once_with(
        str(tmp_path),
        dtype=mock_torch.bfloat16,
        device_map='auto',
    )


def test_init_loads_processor_from_weights_dir(tmp_path):
    (tmp_path / 'model.safetensors').touch()
    model = Gemma4RulesModel(
        model_variant='test-variant', model_weights_dir=str(tmp_path))
    with patch('src.ml.gemma4_rules_model.AutoModelForCausalLM'), \
         patch('src.ml.gemma4_rules_model.AutoProcessor') as mock_proc, \
         patch('src.ml.gemma4_rules_model.download_weights_s3'):
        model.init()
    mock_proc.from_pretrained.assert_called_once_with(str(tmp_path))


def test_init_assigns_loaded_model_and_processor_to_instance(tmp_path):
    (tmp_path / 'model.safetensors').touch()
    model = Gemma4RulesModel(
        model_variant='test-variant', model_weights_dir=str(tmp_path))
    with patch('src.ml.gemma4_rules_model.AutoModelForCausalLM') as mock_cls, \
         patch('src.ml.gemma4_rules_model.AutoProcessor') as mock_proc, \
         patch('src.ml.gemma4_rules_model.download_weights_s3'):
        model.init()
    assert model.model is mock_cls.from_pretrained.return_value
    assert model.processor is mock_proc.from_pretrained.return_value


def test_init_runs_warmup_generate(tmp_path):
    (tmp_path / 'model.safetensors').touch()
    model = Gemma4RulesModel(
        model_variant='test-variant', model_weights_dir=str(tmp_path))
    with patch('src.ml.gemma4_rules_model.AutoModelForCausalLM') as mock_cls, \
         patch('src.ml.gemma4_rules_model.AutoProcessor'), \
         patch('src.ml.gemma4_rules_model.download_weights_s3'):
        model.init()
    mock_cls.from_pretrained.return_value.generate.assert_called_once()


# --- _build_rule_messages ---

def test_build_rule_messages_includes_two_system_messages(
        initialized_model, sample_rules):
    messages = initialized_model._build_rule_messages(sample_rules)
    system_messages = [m for m in messages if m['role'] == 'system']
    assert len(system_messages) == 2


def test_build_rule_messages_creates_one_user_message_per_rule(
        initialized_model, sample_rules):
    messages = initialized_model._build_rule_messages(sample_rules)
    user_messages = [m for m in messages if m['role'] == 'user']
    assert len(user_messages) == len(sample_rules)


def test_build_rule_messages_formats_rule_as_question(initialized_model):
    rules = [RuleEvaluationInput(
        rule_public_id='1', rule_name='Test', rule='a cat is present')]
    messages = initialized_model._build_rule_messages(rules)
    user_message = next(m for m in messages if m['role'] == 'user')
    text_part = next(c for c in user_message['content'] if c['type'] == 'text')
    assert text_part['text'] == 'is a cat is present?'


def test_build_rule_messages_includes_image_placeholder_in_each_user_message(
        initialized_model, sample_rules):
    messages = initialized_model._build_rule_messages(sample_rules)
    user_messages = [m for m in messages if m['role'] == 'user']
    for msg in user_messages:
        image_parts = [c for c in msg['content'] if c['type'] == 'image']
        assert len(image_parts) == 1


def test_build_rule_messages_with_no_rules_returns_only_system_messages(
        initialized_model):
    messages = initialized_model._build_rule_messages([])
    user_messages = [m for m in messages if m['role'] == 'user']
    assert len(user_messages) == 0


# --- evaluate_rules ---

def test_evaluate_rules_calls_apply_chat_template(
        initialized_model, sample_rules, sample_image):
    initialized_model.evaluate_rules(rules=sample_rules, image=sample_image)
    initialized_model.processor.apply_chat_template.assert_called_once()


def test_evaluate_rules_passes_one_user_message_per_rule_to_chat_template(
        initialized_model, sample_rules, sample_image):
    initialized_model.evaluate_rules(rules=sample_rules, image=sample_image)
    call_args = initialized_model.processor.apply_chat_template.call_args
    messages = call_args.args[0]
    user_messages = [m for m in messages if m['role'] == 'user']
    assert len(user_messages) == len(sample_rules)


def test_evaluate_rules_calls_model_generate(
        initialized_model, sample_rules, sample_image):
    initialized_model.evaluate_rules(rules=sample_rules, image=sample_image)
    initialized_model.model.generate.assert_called_once()


def test_evaluate_rules_returns_a_list(
        initialized_model, sample_rules, sample_image):
    result = initialized_model.evaluate_rules(
        rules=sample_rules, image=sample_image)
    assert isinstance(result, list)
