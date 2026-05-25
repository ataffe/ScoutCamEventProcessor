from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from pathlib import Path
import yaml
import os

def get_sql_engine() -> Engine:
    config = {}
    env = os.environ.get('ENV')
    config_filename = f'config_{env}.yaml' if env else 'config_dev.yaml'
    config_path = Path(f'config/{config_filename}')
    if not config_path.is_file():
        raise FileNotFoundError(f'Config file not found at {config_path}')

    with open(str(config_path), 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)
    database_config = config['db']
    return create_engine(
        f'{database_config['db_dialect']}+{database_config['dbapi']}://' +
        f'{database_config['user']}:{database_config['password']}'+
        f'@{database_config['host']}:{database_config['port']}/{database_config["db_name"]}')