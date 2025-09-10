#!/usr/bin/env python3
"""
Prometheus Data Generator

A service that generates synthetic Prometheus metrics for testing monitoring
infrastructure, Grafana dashboards, and alerting rules. Supports multiple
metric types (Counter, Gauge, Summary, Histogram) with configurable update
sequences and label combinations.

Features:
- Hot-reload configuration via HTTP endpoint
- Multi-threaded metric updates
- Docker and Kubernetes deployment support
- Configurable logging levels
- Support for random value ranges and fixed values

License: GPLv3
"""

import time
import random
import threading
import logging
from os import _exit, environ
import yaml
from flask import Flask, Response
from prometheus_client import Gauge, Counter, Summary, Histogram
from prometheus_client import generate_latest, CollectorRegistry

# Supported logging levels for PDG_LOG_LEVEL environment variable
supported_log_levels = ["INFO", "ERROR", "DEBUG"]
logger = logging.getLogger("prometheus-data-generator")

# Configure logging with timestamp, level, function name, and message
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s - %(funcName)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Override log level if PDG_LOG_LEVEL environment variable is set
if "PDG_LOG_LEVEL" in environ:
    if environ["PDG_LOG_LEVEL"].upper() in supported_log_levels:
        logger.setLevel(environ["PDG_LOG_LEVEL"].upper())


def read_configuration():
    """
    Read and parse the YAML configuration file for metric definitions.
    
    This function loads the configuration from either the PDG_CONFIG environment
    variable or defaults to 'config.yml'. The configuration contains metric
    definitions including names, types, labels, and update sequences.
    
    Returns:
        dict: Parsed YAML configuration containing metric definitions
        
    Environment Variables:
        PDG_CONFIG (str, optional): Path to configuration file. Defaults to 'config.yml'
        
    Note:
        Currently lacks YAML validation - TODO item for future enhancement
    """
    # TODO validate the yaml
    if "PDG_CONFIG" in environ:
        path = environ["PDG_CONFIG"]
    else:
        path = "config.yml"

    logger.debug(
        "Reading configuration from {}".format(path)
    )
    config = yaml.safe_load(open(path))
    return config


class PrometheusDataGenerator:
    def __init__(self):
        """
        Initialize the Prometheus Data Generator service.
        
        Sets up the Flask web application, initializes the metrics registry,
        creates metric threads, and configures HTTP endpoints. This is the
        main entry point for the service initialization.
        
        Attributes:
            threads (list): List of active metric update threads
            app (Flask): Flask web application instance
            registry (CollectorRegistry): Prometheus metrics registry
            data (dict): Parsed configuration data
        """
        self.threads = []
        self.app = Flask(__name__)
        self.serve_metrics()
        self.init_metrics()
        logger.debug(
            "Total number of threads: {}".format(len(self.threads))
        )


    def init_metrics(self):
        """
        Initialize Prometheus metrics and create update threads.
        
        Reads the configuration file and creates Prometheus metric instruments
        (Counter, Gauge, Summary, Histogram) based on the configuration.
        Each metric gets its own dedicated thread for continuous updates.
        
        Supported metric types:
            - Counter: Monotonically increasing values
            - Gauge: Values that can go up or down
            - Summary: Quantile-based statistics
            - Histogram: Bucket-based statistics
            
        Thread Management:
            Each metric spawns a separate thread running update_metrics()
            to ensure concurrent metric updates without blocking.
            
        Note:
            Histogram buckets are currently fixed - TODO for customization
        """
        logger.debug(
            "Initializing metrics"
        )
        self.registry = CollectorRegistry()
        self.data = read_configuration()
        for metric in self.data["metrics"]:
            if "labels" in metric:
                labels = metric["labels"]
            else:
                labels = []
            if metric["type"].lower() == "counter":
                instrument = Counter(
                    metric["name"],
                    metric["description"],
                    labels,
                    registry=self.registry
                )
            elif metric["type"].lower() == "gauge":
                instrument = Gauge(
                    metric["name"],
                    metric["description"],
                    labels,
                    registry=self.registry
                )
            elif metric["type"].lower() == "summary":
                instrument = Summary(
                    metric["name"],
                    metric["description"],
                    labels,
                    registry=self.registry
                )
            elif metric["type"].lower() == "histogram":
                # TODO add support to overwrite buckets
                instrument = Histogram(
                    metric["name"],
                    metric["description"],
                    labels,
                    registry=self.registry
                )
            else:
                logger.warning(
                    "Unknown metric type {type} for metric {name}, ignoring.".format(**metric)
                )

            t = threading.Thread(
                target=self.update_metrics,
                args=(instrument, metric)
            )
            t.start()
            self.threads.append(t)
            logger.debug(
                "Initialized metric {}".format(metric["name"])
            )

    def update_metrics(self, metric_object, metric_metadata):
        """
        Continuously update Prometheus metrics based on configuration sequences.
        
        This method runs in a separate thread for each metric and executes
        the configured sequences of operations. It supports different value
        generation methods and metric-specific operations.
        
        Args:
            metric_object: Prometheus metric instrument (Gauge, Counter, Summary, or Histogram)
            metric_metadata (dict): Configuration data for this metric from config.yml
                Expected keys:
                - name (str): Metric name
                - type (str): Metric type (counter, gauge, summary, histogram)
                - sequences (list): List of update sequences
                
        Sequence Configuration:
            Each sequence can contain:
            - eval_time (int): Duration in seconds to run this sequence
            - interval (int): Seconds between updates (default: 1)
            - value (int/float): Fixed value to use
            - range (str): Random range in format "min-max"
            - operation (str): For gauges only - "inc", "dec", or "set"
            - labels (dict): Label values for this sequence
            
        Value Generation:
            - Fixed values: Use 'value' key
            - Random ranges: Use 'range' key with "min-max" format
            - Automatic type detection (int vs float)
            
        Metric Operations:
            - Gauge: inc, dec, set operations
            - Counter: increment only
            - Summary/Histogram: observe operations
            
        Thread Safety:
            Uses self.stopped flag for graceful shutdown during reloads
        """
        # Initialize stop flag for graceful shutdown
        self.stopped = False
        
        # Main metric update loop - runs until service is stopped
        while True:
            if self.stopped:
                break
                
            # Process each sequence in the metric configuration
            for sequence in metric_metadata["sequences"]:
                if self.stopped:
                    break

                # Extract label values from sequence configuration
                if "labels" in sequence:
                    labels = [key for key in sequence["labels"].values()]
                else:
                    labels = []

                # Calculate sequence timeout duration
                if "eval_time" in sequence:
                    timeout = time.time() + sequence["eval_time"]
                else:
                    logger.warning(
                        "eval_time for metric {} not set, setting default to 1.".format(metric_metadata["name"])
                    )
                    timeout = time.time() + 1

                logger.debug(
                    "Changing sequence in {} metric".format(metric_metadata["name"])
                )

                # Set update interval between metric operations
                if "interval" in sequence:
                    interval = sequence["interval"]
                else:
                    logger.warning(
                        "interval for metric {} not set, setting default to 1.".format(metric_metadata["name"])
                    )
                    interval = 1

                # Execute sequence operations until timeout or stop signal
                while True:
                    if self.stopped:
                        break

                    # Check if sequence timeout has been reached
                    if time.time() > timeout:
                        break

                    # Generate metric value - either fixed or random range
                    if "value" in sequence:
                        # Use fixed value from configuration
                        value = sequence["value"]
                        if isinstance(value, float):
                            value = float(value)
                        else:
                            value = int(value)

                    elif "range" in sequence:
                        # Generate random value within specified range
                        if "." in sequence["range"].split("-")[0]:
                            # Float range: "1.5-10.0"
                            initial_value = float(sequence["range"].split("-")[0])
                            end_value = float(sequence["range"].split("-")[1])
                            value = random.uniform(initial_value, end_value)
                        else:
                            # Integer range: "1-10"
                            initial_value = int(sequence["range"].split("-")[0])
                            end_value = int(sequence["range"].split("-")[1])
                            value = random.randrange(initial_value, end_value)

                    # Apply metric operations based on metric type
                    if metric_metadata["type"].lower() == "gauge":
                        # Gauge metrics support inc, dec, and set operations
                        try:
                            operation = sequence["operation"].lower()
                        except:
                            logger.error(
                                "You must set an operation when using Gauge"
                            )
                            _exit(1)
                        if operation == "inc":
                            # Increment gauge by value
                            if labels == []:
                                metric_object.inc(value)
                            else:
                                metric_object.labels(*labels).inc(value)
                        elif operation == "dec":
                            # Decrement gauge by value
                            if labels == []:
                                metric_object.dec(value)
                            else:
                                metric_object.labels(*labels).dec(value)
                        elif operation == "set":
                            # Set gauge to specific value
                            if labels == []:
                                metric_object.set(value)
                            else:
                                metric_object.labels(*labels).set(value)

                    elif metric_metadata["type"].lower() == "counter":
                        # Counter metrics only support increment
                        if labels == []:
                            metric_object.inc(value)
                        else:
                            metric_object.labels(*labels).inc(value)
                    elif metric_metadata["type"].lower() == "summary":
                        # Summary metrics observe values for quantile calculation
                        if labels == []:
                            metric_object.observe(value)
                        else:
                            metric_object.labels(*labels).observe(value)
                    elif metric_metadata["type"].lower() == "histogram":
                        # Histogram metrics observe values for bucket distribution
                        if labels == []:
                            metric_object.observe(value)
                        else:
                            metric_object.labels(*labels).observe(value)
                    
                    # Wait for the configured interval before next update
                    time.sleep(interval)

    def serve_metrics(self):
        """
        Configure Flask routes for serving metrics and management endpoints.
        
        Sets up three HTTP endpoints:
        1. Root endpoint (/) - Simple HTML page with metrics link
        2. Metrics endpoint (/metrics/) - Prometheus metrics in text format
        3. Reload endpoint (/-/reload) - Hot-reload configuration
        
        The metrics endpoint generates fresh metric data on each request
        using the current state of all metric instruments.
        """
        @self.app.route("/")
        def root():
            """
            Serve a simple HTML page with a link to the metrics endpoint.
            
            Returns:
                str: HTML page with link to /metrics/
            """
            page = "<a href=\"/metrics/\">Metrics</a>"
            return page

        @self.app.route("/metrics/")
        def metrics():
            """
            Expose Prometheus metrics in the standard text format.
            
            Generates the latest metric values from the registry and returns
            them in the Prometheus exposition format. This endpoint is
            typically scraped by Prometheus servers.
            
            Returns:
                Response: HTTP response with metrics in text/plain format
            """
            metrics = generate_latest(self.registry)
            return Response(metrics,
                            mimetype="text/plain",
                            content_type="text/plain; charset=utf-8")

        @self.app.route("/-/reload")
        def reload():
            """
            Hot-reload configuration without restarting the service.
            
            Gracefully stops all metric update threads, waits for them to
            complete, then reinitializes metrics with the current configuration.
            This allows configuration changes to take effect without downtime.
            
            Process:
            1. Set stopped flag to signal threads to terminate
            2. Wait for all threads to complete (thread.join())
            3. Reinitialize metrics with fresh configuration
            4. Return success response
            
            Returns:
                Response: HTTP 200 OK response
            """
            self.stopped = True
            for thread in self.threads:
                thread.join()
            self.init_metrics()
            logger.info("Configuration reloaded. Metrics will be restarted.")
            return Response("OK")

    def run_webserver(self):
        """
        Start the Flask web server in a separate thread.
        
        Launches the Flask application on port 9000, binding to all interfaces
        (0.0.0.0). The server runs in a daemon thread to allow the main thread
        to continue execution.
        
        Server Configuration:
            - Port: 9000 (standard for Prometheus exporters)
            - Host: 0.0.0.0 (accepts connections from any interface)
            - Threading: Enabled for concurrent request handling
            
        Note:
            This method starts the server but doesn't block the calling thread.
            The server will continue running until the process terminates.
        """
        threading.Thread(
            target=self.app.run,
            kwargs={"port": "9000", "host": "0.0.0.0"}
        ).start()


if __name__ == "__main__":
    """
    Main entry point for the Prometheus Data Generator service.
    
    Creates a PrometheusDataGenerator instance which:
    1. Initializes the Flask web application
    2. Sets up HTTP endpoints for metrics and management
    3. Creates and starts metric update threads
    4. Launches the web server on port 9000
    
    The service will continue running until terminated, serving metrics
    at http://localhost:9000/metrics/ and providing a reload endpoint
    at http://localhost:9000/-/reload for configuration hot-reloads.
    """
    PROM = PrometheusDataGenerator()
    PROM.run_webserver()
