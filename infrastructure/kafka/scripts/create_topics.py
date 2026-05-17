#!/usr/bin/env python3
"""
Kafka Topic Management Script
==============================
Create, delete, and manage Kafka topics for trading platform.
"""

import sys
import os
import logging
import argparse
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_topics(bootstrap_servers: list, topics_config: list, wait_time: int = 30):
    """Create Kafka topics based on configuration."""
    try:
        from kafka import KafkaAdminClient
        from kafka.admin import NewTopic, ConfigResource, ConfigResourceType
        from kafka.errors import TopicAlreadyExistsError, KafkaError
    except ImportError:
        logger.error("kafka-python not installed. Run: pip install kafka-python")
        sys.exit(1)

    admin_client = None
    try:
        logger.info(f"Connecting to Kafka at {bootstrap_servers}")
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='topic-manager'
        )

        existing_topics = admin_client.list_topics()
        logger.info(f"Existing topics: {existing_topics}")

        new_topics = []
        topic_configs = {
            'ticks.raw': {
                'retention.ms': '604800000',
                'retention.bytes': '10737418240',
                'segment.bytes': '104857600',
                'cleanup.policy': 'delete',
                'compression.type': 'lz4',
                'min.insync.replicas': '2'
            },
            'ticks.processed': {
                'retention.ms': '2592000000',
                'cleanup.policy': 'delete',
                'compression.type': 'lz4',
                'min.insync.replicas': '2'
            },
            'orders.created': {
                'retention.ms': '7776000000',
                'cleanup.policy': 'delete',
                'compression.type': 'snappy',
                'min.insync.replicas': '2'
            },
            'orders.status': {
                'retention.ms': '7776000000',
                'cleanup.policy': 'delete',
                'min.insync.replicas': '2'
            },
            'trades.executed': {
                'retention.ms': '220752000000',  # 7 years
                'retention.bytes': '-1',
                'cleanup.policy': 'compact',
                'compression.type': 'zstd',
                'min.insync.replicas': '2'
            },
            'trades.reconciled': {
                'retention.ms': '220752000000',
                'cleanup.policy': 'compact',
                'min.insync.replicas': '2'
            },
            'risk.events': {
                'retention.ms': '2592000000',
                'cleanup.policy': 'delete',
                'min.insync.replicas': '2'
            },
            'risk.position': {
                'retention.ms': '2592000000',
                'cleanup.policy': 'delete',
                'min.insync.replicas': '2'
            },
            'signals.generated': {
                'retention.ms': '7776000000',
                'cleanup.policy': 'delete',
                'min.insync.replicas': '2'
            },
            'signals.executed': {
                'retention.ms': '7776000000',
                'cleanup.policy': 'delete',
                'min.insync.replicas': '2'
            },
            'system.health': {
                'retention.ms': '604800000',
                'cleanup.policy': 'delete',
                'min.insync.replicas': '2'
            },
            'audit.trading': {
                'retention.ms': '315360000000',  # 10 years
                'retention.bytes': '-1',
                'cleanup.policy': 'compact',
                'compression.type': 'zstd',
                'min.insync.replicas': '2'
            },
            'audit.user': {
                'retention.ms': '315360000000',
                'retention.bytes': '-1',
                'cleanup.policy': 'compact',
                'min.insync.replicas': '2'
            },
            'dlq.errors': {
                'retention.ms': '2592000000',
                'cleanup.policy': 'delete',
                'min.insync.replicas': '2'
            }
        }

        topic_partitions = {
            'ticks.raw': 16,
            'ticks.processed': 16,
            'orders.created': 8,
            'orders.status': 8,
            'trades.executed': 8,
            'trades.reconciled': 8,
            'risk.events': 4,
            'risk.position': 4,
            'signals.generated': 8,
            'signals.executed': 8,
            'system.health': 2,
            'audit.trading': 4,
            'audit.user': 4,
            'dlq.errors': 2
        }

        for topic_name, partition_count in topic_partitions.items():
            if topic_name in existing_topics:
                logger.info(f"Topic {topic_name} already exists, skipping")
                continue

            config = topic_configs.get(topic_name, {})
            topic = NewTopic(
                name=topic_name,
                num_partitions=partition_count,
                replication_factor=3,
                topic_configs=config
            )
            new_topics.append(topic)
            logger.info(f"Prepared topic {topic_name} with {partition_count} partitions")

        if new_topics:
            logger.info(f"Creating {len(new_topics)} topics...")
            admin_client.create_topics(new_topics, validate_only=False)

            logger.info(f"Waiting for topics to be created (max {wait_time}s)...")
            start_time = time.time()
            while time.time() - start_time < wait_time:
                created_topics = set(admin_client.list_topics())
                all_created = all(t.name in created_topics for t in new_topics)
                if all_created:
                    break
                time.sleep(1)

            logger.info(f"Successfully created {len(new_topics)} topics")
        else:
            logger.info("No new topics to create")

    except Exception as e:
        logger.error(f"Error creating topics: {e}")
        sys.exit(1)

    finally:
        if admin_client:
            admin_client.close()


def delete_topics(bootstrap_servers: list, topics: list):
    """Delete specified topics."""
    try:
        from kafka import KafkaAdminClient
    except ImportError:
        logger.error("kafka-python not installed")
        sys.exit(1)

    admin_client = None
    try:
        admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers, client_id='topic-manager')
        admin_client.delete_topics(topics)
        logger.info(f"Deleted topics: {topics}")
    except Exception as e:
        logger.error(f"Error deleting topics: {e}")
    finally:
        if admin_client:
            admin_client.close()


def list_topics(bootstrap_servers: list):
    """List all topics."""
    try:
        from kafka import KafkaAdminClient
    except ImportError:
        logger.error("kafka-python not installed")
        sys.exit(1)

    admin_client = None
    try:
        admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers, client_id='topic-manager')
        topics = admin_client.list_topics()
        logger.info(f"Total topics: {len(topics)}")
        for topic in sorted(topics):
            logger.info(f"  - {topic}")
    finally:
        if admin_client:
            admin_client.close()


def describe_topic(bootstrap_servers: list, topic_name: str):
    """Describe a specific topic."""
    try:
        from kafka import KafkaAdminClient
    except ImportError:
        logger.error("kafka-python not installed")
        sys.exit(1)

    admin_client = None
    try:
        admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers, client_id='topic-manager')

        configs = admin_client.describe_configs(
            config_resources=[{'type': 'TOPIC', 'name': topic_name}]
        )

        logger.info(f"Topic: {topic_name}")
        for config in configs.values():
            for name, value in config.items():
                logger.info(f"  {name}: {value}")

    except Exception as e:
        logger.error(f"Error describing topic: {e}")
    finally:
        if admin_client:
            admin_client.close()


def main():
    parser = argparse.ArgumentParser(description='Manage Kafka topics')
    parser.add_argument('--bootstrap-servers', default='localhost:9092',
                        help='Kafka bootstrap servers (comma-separated)')
    parser.add_argument('--create', action='store_true', help='Create topics')
    parser.add_argument('--delete', nargs='+', help='Delete topics')
    parser.add_argument('--list', action='store_true', help='List all topics')
    parser.add_argument('--describe', help='Describe a specific topic')
    parser.add_argument('--replication-factor', type=int, default=3,
                        help='Replication factor for new topics')
    parser.add_argument('--partitions', type=int, default=8,
                        help='Default partition count for new topics')

    args = parser.parse_args()
    bootstrap_servers = args.bootstrap_servers.split(',')

    if args.create:
        create_topics(bootstrap_servers)
    elif args.delete:
        delete_topics(bootstrap_servers, args.delete)
    elif args.list:
        list_topics(bootstrap_servers)
    elif args.describe:
        describe_topic(bootstrap_servers, args.describe)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()