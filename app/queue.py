import json
from typing import Any, Dict

import pika

from app.config import RABBITMQ_URL

QUEUE_NAME = "crawl_jobs"


def get_rabbitmq_connection():
    """Create and return a RabbitMQ connection"""
    parameters = pika.URLParameters(RABBITMQ_URL)
    return pika.BlockingConnection(parameters)


def publish_job(job_data: Dict[str, Any]) -> None:
    """
    Publish a crawl job to RabbitMQ queue

    Args:
        job_data: Dictionary containing job_id and job_type
    """
    connection = get_rabbitmq_connection()
    channel = connection.channel()

    # Declare queue (idempotent)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    # Publish message
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=json.dumps(job_data),
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        ),
    )

    connection.close()


def consume_jobs(callback):
    """
    Consume jobs from RabbitMQ queue.

    Args:
        callback: Function called for each message (channel, method, properties, body).
    """
    connection = get_rabbitmq_connection()
    channel = connection.channel()

    # Declare queue (idempotent)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    # Set QoS to only process one message at a time
    channel.basic_qos(prefetch_count=1)

    # Set up consumer
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print(f" [*] Waiting for messages in queue '{QUEUE_NAME}'. To exit press CTRL+C")
    channel.start_consuming()
