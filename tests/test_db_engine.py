import os
from unittest.mock import patch, mock_open

from src.db.engine import get_sql_engine


MOCK_DB_CONFIG = {
    'db': {
        'db_dialect': 'postgresql',
        'dbapi': 'psycopg',
        'user': 'testuser',
        'password': 'testpass',
        'host': 'localhost',
        'port': '5432',
        'db_name': 'testdb',
    }
}


def test_engine_url_built_from_config():
    with patch('src.db.engine.Path.is_file', return_value=True), \
         patch('builtins.open', mock_open()), \
         patch('yaml.safe_load', return_value=MOCK_DB_CONFIG):
        engine = get_sql_engine()
    url = engine.url
    assert url.drivername == 'postgresql+psycopg'
    assert url.username == 'testuser'
    assert url.host == 'localhost'
    assert url.port == 5432
    assert url.database == 'testdb'


def test_uses_dev_config_by_default():
    with patch.dict(os.environ, {'ENV': ''}), \
         patch('src.db.engine.Path.is_file', return_value=True), \
         patch('builtins.open', mock_open()) as mock_file, \
         patch('yaml.safe_load', return_value=MOCK_DB_CONFIG):
        get_sql_engine()
    mock_file.assert_called_once_with('config/config_dev.yaml', 'r')


def test_uses_env_specific_config_when_env_var_set():
    with patch.dict(os.environ, {'ENV': 'prod'}), \
         patch('src.db.engine.Path.is_file', return_value=True), \
         patch('builtins.open', mock_open()) as mock_file, \
         patch('yaml.safe_load', return_value=MOCK_DB_CONFIG):
        get_sql_engine()
    mock_file.assert_called_once_with('config/config_prod.yaml', 'r')


def test_raises_if_config_file_missing():
    with patch('src.db.engine.Path.is_file', return_value=False), \
         patch.dict(os.environ, {'ENV': 'prod'}):
        try:
            get_sql_engine()
            assert False, 'Expected FileNotFoundError'
        except FileNotFoundError as e:
            assert 'config_prod.yaml' in str(e)