"""
Metrics Export Module
=====================
Prometheus metrics endpoint and export utilities.
"""

from flask import Flask, Response, jsonify
from prometheus_client import (
    generate_latest,
    REGISTRY,
    CONTENT_TYPE_LATEST,
    Gauge,
    Counter,
    Histogram
)
import logging

logger = logging.getLogger('trading_app.export')


class PrometheusExporter:
    """Prometheus metrics exporter for Flask."""

    def __init__(self, app: Flask = None):
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize with Flask app."""
        app.config.setdefault('METRICS_ENABLED', True)
        app.config.setdefault('METRICS_AUTH_ENABLED', False)

        auth_enabled = app.config.get('METRICS_AUTH_ENABLED', False)

        @app.route('/metrics')
        def metrics_endpoint():
            """Prometheus metrics endpoint."""
            if not app.config.get('METRICS_ENABLED', True):
                return 'Service Unavailable', 503

            if auth_enabled:
                from flask import request
                auth = request.authorization
                if not auth or not self._verify_auth(auth):
                    return Response(
                        'Unauthorized',
                        401,
                        {'WWW-Authenticate': 'Basic realm="Metrics"'}
                    )

            return Response(
                generate_latest(REGISTRY),
                mimetype=CONTENT_TYPE_LATEST
            )

        @app.route('/metrics/detailed')
        def detailed_metrics():
            """Detailed metrics with more labels."""
            if not app.config.get('METRICS_ENABLED', True):
                return 'Service Unavailable', 503
            return Response(
                generate_latest(REGISTRY),
                mimetype=CONTENT_TYPE_LATEST
            )

        @app.route('/metrics/json')
        def metrics_json():
            """Metrics in JSON format."""
            if not app.config.get('METRICS_ENABLED', True):
                return jsonify({'error': 'Service Unavailable'}), 503

            metrics = {}
            for metric in REGISTRY.collect():
                metric_name = metric.name
                for sample in metric.samples:
                    if sample.name == metric_name:
                        key = f"{sample.name}" + "{" + ",".join(
                            f'{k}="{v}"' for k, v in sample.labels.items()
                        ) + "}"
                        metrics[key] = sample.value

            return jsonify(metrics)

        logger.info("Prometheus exporter initialized with /metrics endpoint")

    def _verify_auth(self, auth) -> bool:
        """Verify basic auth credentials."""
        username = self.app.config.get('METRICS_USERNAME', 'admin')
        password = self.app.config.get('METRICS_PASSWORD', 'admin')
        return auth.username == username and auth.password == password


metrics_endpoint = PrometheusExporter


def create_custom_metrics():
    """Create custom metrics not in standard collectors."""

    custom_metrics = {}

    custom_metrics['application_info'] = Gauge(
        'application_info',
        'Application information',
        ['version', 'environment', 'service']
    )

    custom_metrics['deployment_info'] = Gauge(
        'deployment_info',
        'Deployment information',
        ['version', 'commit', 'environment']
    )

    custom_metrics['build_info'] = Gauge(
        'build_info',
        'Build information',
        ['version', 'build_time']
    )

    return custom_metrics


custom_metrics = create_custom_metrics()


def set_application_info(version: str, environment: str, service: str = 'trading-backend'):
    """Set application info."""
    custom_metrics['application_info'].labels(
        version=version,
        environment=environment,
        service=service
    ).set(1)


def set_deployment_info(version: str, commit: str, environment: str):
    """Set deployment info."""
    custom_metrics['deployment_info'].labels(
        version=version,
        commit=commit,
        environment=environment
    ).set(1)


def set_build_info(version: str, build_time: str):
    """Set build info."""
    custom_metrics['build_info'].labels(
        version=version,
        build_time=build_time
    ).set(1)