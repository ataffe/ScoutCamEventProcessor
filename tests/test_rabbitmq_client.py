import io
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from PIL import Image

from src.clients.rabbitmq_client import get_rabbitmq_connection, on_message
from src.ml.rules_model import RuleEvaluationResult


RABBITMQ_CONFIG = {
    'rabbitmq': {
        'host': 'localhost',
        'port': 5672,
        'queue_name': 'test_queue',
        'durable': True,
    }
}


@pytest.fixture
def valid_jpeg_bytes():
    img = Image.new('RGB', (100, 100), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


@pytest.fixture
def mock_channel():
    return MagicMock()


@pytest.fixture
def mock_method():
    m = MagicMock()
    m.delivery_tag = 42
    return m


@pytest.fixture
def mock_properties():
    p = MagicMock()
    p.headers = {'camera_public_id': str(uuid4())}
    return p


@pytest.fixture
def mock_rules_model():
    m = MagicMock()
    m.evaluate_rules.return_value = []
    return m


@pytest.fixture
def mock_sql_engine():
    return MagicMock()


@pytest.fixture
def sample_rule():
    rule = MagicMock()
    rule.public_rule_id = uuid4()
    rule.rule_nickname = 'Person Detection'
    rule.rule = 'a person is present'
    return rule


# --- get_rabbitmq_connection ---

def test_connection_uses_host_and_port_from_config():
    with patch('src.clients.rabbitmq_client.pika.BlockingConnection') as mock_conn_cls:
        get_rabbitmq_connection(RABBITMQ_CONFIG, MagicMock())
    params = mock_conn_cls.call_args[0][0]
    assert params.host == 'localhost'
    assert params.port == 5672


def test_declares_queue_with_config_settings():
    with patch('src.clients.rabbitmq_client.pika.BlockingConnection') as mock_conn_cls:
        mock_chan = mock_conn_cls.return_value.channel.return_value
        get_rabbitmq_connection(RABBITMQ_CONFIG, MagicMock())
    mock_chan.queue_declare.assert_called_once_with(
        queue='test_queue',
        durable=True,
        arguments={'x-queue-type': 'quorum'},
    )


def test_registers_callback_on_queue():
    with patch('src.clients.rabbitmq_client.pika.BlockingConnection') as mock_conn_cls:
        mock_chan = mock_conn_cls.return_value.channel.return_value
        callback = MagicMock()
        get_rabbitmq_connection(RABBITMQ_CONFIG, callback)
    mock_chan.basic_consume.assert_called_once_with(
        queue='test_queue',
        on_message_callback=callback,
    )


def test_returns_connection_and_channel():
    with patch('src.clients.rabbitmq_client.pika.BlockingConnection') as mock_conn_cls:
        mock_conn = mock_conn_cls.return_value
        mock_chan = mock_conn.channel.return_value
        conn, chan = get_rabbitmq_connection(RABBITMQ_CONFIG, MagicMock())
    assert conn is mock_conn
    assert chan is mock_chan


# --- on_message: routing/ack behaviour ---

def test_acks_message_when_no_camera_id_in_headers(
        mock_channel, mock_method, mock_rules_model, mock_sql_engine):
    props = MagicMock()
    props.headers = {}
    with patch('src.clients.rabbitmq_client.get_rules_by_id'):
        on_message(mock_channel, mock_method, props, b'', mock_rules_model, mock_sql_engine)
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)


def test_acks_message_when_headers_is_none(
        mock_channel, mock_method, mock_rules_model, mock_sql_engine):
    props = MagicMock()
    props.headers = None
    with patch('src.clients.rabbitmq_client.get_rules_by_id'):
        on_message(mock_channel, mock_method, props, b'', mock_rules_model, mock_sql_engine)
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)


def test_acks_message_when_no_rules_found(
        mock_channel, mock_method, mock_properties, mock_rules_model, mock_sql_engine):
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[]):
        on_message(mock_channel, mock_method, mock_properties, b'', mock_rules_model, mock_sql_engine)
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)


def test_acks_message_after_processing_valid_image(
        mock_channel, mock_method, mock_properties, mock_rules_model,
        mock_sql_engine, sample_rule, valid_jpeg_bytes):
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[sample_rule]):
        on_message(mock_channel, mock_method, mock_properties, valid_jpeg_bytes,
                   mock_rules_model, mock_sql_engine)
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)


def test_acks_message_when_image_bytes_are_corrupt(
        mock_channel, mock_method, mock_properties, mock_rules_model,
        mock_sql_engine, sample_rule):
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[sample_rule]):
        on_message(mock_channel, mock_method, mock_properties, b'not_an_image',
                   mock_rules_model, mock_sql_engine)
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)


# --- on_message: DB lookup ---

def test_does_not_query_db_when_no_camera_id(
        mock_channel, mock_method, mock_rules_model, mock_sql_engine):
    props = MagicMock()
    props.headers = {}
    with patch('src.clients.rabbitmq_client.get_rules_by_id') as mock_get_rules:
        on_message(mock_channel, mock_method, props, b'', mock_rules_model, mock_sql_engine)
    mock_get_rules.assert_not_called()


def test_queries_db_with_camera_id_from_header(
        mock_channel, mock_method, mock_rules_model, mock_sql_engine):
    camera_id = str(uuid4())
    props = MagicMock()
    props.headers = {'camera_public_id': camera_id}
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[]) as mock_get_rules:
        on_message(mock_channel, mock_method, props, b'', mock_rules_model, mock_sql_engine)
    mock_get_rules.assert_called_once_with(camera_id, mock_sql_engine)


# --- on_message: model evaluation ---

def test_does_not_evaluate_rules_when_no_camera_id(
        mock_channel, mock_method, mock_rules_model, mock_sql_engine):
    props = MagicMock()
    props.headers = {}
    with patch('src.clients.rabbitmq_client.get_rules_by_id'):
        on_message(mock_channel, mock_method, props, b'', mock_rules_model, mock_sql_engine)
    mock_rules_model.evaluate_rules.assert_not_called()


def test_does_not_evaluate_rules_when_no_rules_found(
        mock_channel, mock_method, mock_properties, mock_rules_model, mock_sql_engine):
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[]):
        on_message(mock_channel, mock_method, mock_properties, b'', mock_rules_model, mock_sql_engine)
    mock_rules_model.evaluate_rules.assert_not_called()


def test_does_not_evaluate_rules_when_image_is_corrupt(
        mock_channel, mock_method, mock_properties, mock_rules_model,
        mock_sql_engine, sample_rule):
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[sample_rule]):
        on_message(mock_channel, mock_method, mock_properties, b'not_an_image',
                   mock_rules_model, mock_sql_engine)
    mock_rules_model.evaluate_rules.assert_not_called()


def test_evaluates_rules_when_rules_and_valid_image_exist(
        mock_channel, mock_method, mock_properties, mock_rules_model,
        mock_sql_engine, sample_rule, valid_jpeg_bytes):
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[sample_rule]):
        on_message(mock_channel, mock_method, mock_properties, valid_jpeg_bytes,
                   mock_rules_model, mock_sql_engine)
    mock_rules_model.evaluate_rules.assert_called_once()


def test_passes_pil_image_to_model(
        mock_channel, mock_method, mock_properties, mock_rules_model,
        mock_sql_engine, sample_rule, valid_jpeg_bytes):
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[sample_rule]):
        on_message(mock_channel, mock_method, mock_properties, valid_jpeg_bytes,
                   mock_rules_model, mock_sql_engine)
    image_arg = mock_rules_model.evaluate_rules.call_args.kwargs['image']
    assert isinstance(image_arg, Image.Image)


def test_passes_rule_evaluation_inputs_built_from_rules(
        mock_channel, mock_method, mock_properties, mock_rules_model,
        mock_sql_engine, sample_rule, valid_jpeg_bytes):
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[sample_rule]):
        on_message(mock_channel, mock_method, mock_properties, valid_jpeg_bytes,
                   mock_rules_model, mock_sql_engine)
    rules_arg = mock_rules_model.evaluate_rules.call_args.kwargs['rules']
    assert len(rules_arg) == 1
    assert rules_arg[0].rule == sample_rule.rule
    assert rules_arg[0].rule_name == sample_rule.rule_nickname


# --- on_message: triggered rule logging ---

def test_logs_triggered_rule(
        mock_channel, mock_method, mock_properties, mock_sql_engine,
        sample_rule, valid_jpeg_bytes):
    result = RuleEvaluationResult(
        rule_public_id=str(sample_rule.public_rule_id),
        rule_name='Person Detection',
        is_triggered=True,
    )
    model = MagicMock()
    model.evaluate_rules.return_value = [result]
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[sample_rule]), \
         patch('src.clients.rabbitmq_client.logger') as mock_logger:
        on_message(mock_channel, mock_method, mock_properties, valid_jpeg_bytes,
                   model, mock_sql_engine)
    mock_logger.info.assert_any_call('Rule Person Detection triggered.')


def test_does_not_log_untriggered_rule(
        mock_channel, mock_method, mock_properties, mock_sql_engine,
        sample_rule, valid_jpeg_bytes):
    result = RuleEvaluationResult(
        rule_public_id=str(sample_rule.public_rule_id),
        rule_name='Person Detection',
        is_triggered=False,
    )
    model = MagicMock()
    model.evaluate_rules.return_value = [result]
    with patch('src.clients.rabbitmq_client.get_rules_by_id', return_value=[sample_rule]), \
         patch('src.clients.rabbitmq_client.logger') as mock_logger:
        on_message(mock_channel, mock_method, mock_properties, valid_jpeg_bytes,
                   model, mock_sql_engine)
    mock_logger.info.assert_not_called()