import logging
import pika
import numpy as np
import cv2
from PIL import Image as PILImage
from sqlalchemy.engine import Engine

from src.db.rules import get_rules_by_id
from src.ml.rules_model import RulesModel, RuleEvaluationInput

logger = logging.getLogger("GuardianCamService_RabbitMQClient")


def get_rabbitmq_connection(config_dict: dict, on_message_callback: callable):
    logger.info("Creating RabbitMQ connection")
    conn = pika.BlockingConnection(pika.ConnectionParameters(
        host=config_dict['rabbitmq']['host'],
        port=config_dict['rabbitmq']['port']))
    chan = conn.channel()
    queue_name = config_dict['rabbitmq']['queue_name']
    chan.queue_declare(
        queue=queue_name,
        durable=config_dict['rabbitmq']['durable'],
        arguments={'x-queue-type': 'quorum'})
    chan.basic_consume(
        queue=queue_name,
        on_message_callback=on_message_callback)
    logger.info(
        "Connection created listening for messages. To exit press CTRL+C")
    return conn, chan


def on_message(
        ch, method, properties, body: bytes,
        rules_model: RulesModel, sql_engine: Engine):
    camera_public_id = (
        properties.headers.get('camera_public_id', None)
        if properties.headers else None
    )
    rules = get_rules_by_id(camera_public_id, sql_engine) \
        if camera_public_id else []

    if len(rules) > 0:
        img_array = cv2.imdecode(
            np.frombuffer(body, np.uint8), cv2.IMREAD_COLOR)
        if img_array is None:
            logger.error("Received empty image.")
        else:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            logger.debug(f"Received image shape {img_array.shape}")
            img = PILImage.fromarray(img_array)
            rules_eval_input = [
                RuleEvaluationInput.from_rule_entity(rule)
                for rule in rules
            ]
            results = rules_model.evaluate_rules(
                rules=rules_eval_input, image=img)
            for result in results:
                if result.is_triggered:
                    logger.info(f'Rule {result.rule_name} triggered.')

    ch.basic_ack(delivery_tag=method.delivery_tag)
