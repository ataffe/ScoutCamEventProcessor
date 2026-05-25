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
    db = config['db']
    url = (
        f'{db["db_dialect"]}+{db["dbapi"]}://'
        f'{db["user"]}:{db["password"]}'
        f'@{db["host"]}:{db["port"]}/{db["db_name"]}'
    )
    return create_engine(url)
