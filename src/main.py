import logging
import os

import yaml
from functools import partial
from queue.rabbitmq_client import get_rabbitmq_connection, on_message
import time

from src.ml.gemma4_rules_model import Gemma4RulesModel
from src.db.engine import get_sql_engine


logger = logging.getLogger("GuardianCamService")

image_num = 0

def set_log_level(level_str: str):
    logger_level = logging.INFO
    if level_str.lower() == 'debug':
        logger_level = logging.DEBUG
    elif level_str.lower() == 'warning':
        logger_level = logging.WARNING
    elif level_str.lower() == 'error':
        logger_level = logging.ERROR
    elif level_str.lower() == 'critical':
        logger_level = logging.CRITICAL
    else:
        logger.error('Invalid log level, defaulting to info')
    logging.basicConfig(level=logger_level)

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

if __name__ == '__main__':
    config = load_config('../config/config_dev.yaml')
    set_log_level(config['logging']['level'])

    # Dev Environment
    # Set S3 Credentials
    if not os.environ.get('ENV', None):
        os.environ['S3_ML_BUCKET'] = config['b2']['bucket_name']
        os.environ['S3_ENDPOINT_URL'] = config['b2']['endpoint']
        os.environ['S3_ACCESS_KEY_ID'] = config['b2']['access_key_id']
        os.environ['S3_SECRET_ACCESS_KEY'] = config['b2']['application_key']

    guardian_cam_rules_model = Gemma4RulesModel(
        model_variant=config['ml']['model_variant_name'],
        model_weights_dir=config['ml']['model_variant_version'])
    logger.info("Initializing rules model.")
    start = time.perf_counter()
    guardian_cam_rules_model.init()
    logger.info('Initialized rules model in {:.2f} seconds.'.format(time.perf_counter() - start))
    sql_engine = get_sql_engine()
    callback = partial(on_message, rules_model=guardian_cam_rules_model, sql_engine=sql_engine)
    connection, channel = get_rabbitmq_connection(config, callback)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        logger.info("Worker exiting gracefully.")
    finally:
        connection.close()