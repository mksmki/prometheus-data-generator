# Prometheus Data Generator

A service that generates synthetic Prometheus metrics for testing monitoring
infrastructure, Grafana dashboards, and alerting rules. Supports multiple
metric types (Counter, Gauge, Summary, Histogram) with configurable update
instances and label combinations.

## Why use this?

When creating Grafana dashboards or Prometheus alerts, it is common to make
mistakes. You define a threshold that they have to meet, but when modified the
next time you may forget those thresholds.

Using this tool, you can create data with the format you want and
thus being able to base alerts and graphics on data that resemble reality.

To use this, you'll create a configuration file in which you will define a
metric name, description, type and labels and sequences of certain operations.

For example, you'll be able to create a alarm called `http_requests` with the
labels `{path=/login/, return_code=200}` which will be updated as you wish.

## Configuration

There's an example configuration file called `config.yml` in the root of the
repository. It has the next format:

``` yaml
metrics:
  - name: snmp_ifHCInOctets
    description: Inbound traffic on the interface
    type: counter
    labels: [host, ip, interface]
    instances:
      # Host: apple
      - name: apple
        labels:
          host: apple
          ip: 10.10.11.2
          interface: eth0
        sequence:
          - time: 5
            eval_time: 5
            range: 0-20
            operation: inc
          - eval_time: 5
            operation: set
      # Host: grape
      - name: grape
        labels:
          host: grape
          ip: 10.10.11.5
          interface: eth0
        sequence:
          - time: 5
            eval_time: 1
            range: 0-20
            operation: inc
          - time: 5
            eval_time: 1
            range: 0-5
            operation: dec
      # Host: zala
      - name: zala
        labels:
          host: zala
          ip: 10.10.11.8
          interface: eth0
        sequence:
          - time: 5
            eval_time: 1
            value: 3
            operation: inc

  - name: snmp_sysUpTimeInstance
    description: System uptime
    type: counter
    labels: [host, ip, interface]
    instances:
      # Host: apple
      - name: apple
        labels:
          host: apple
          ip: 10.10.11.2
          interface: eth0
        sequence:
          - time: 1
            eval_time: 1
            value: 1
            operation: inc
      # Host: grape
      - name: grape
        labels:
          host: grape
          ip: 10.10.11.5
          interface: eth0
        sequence:
          - time: 1
            eval_time: 1
            value: 1
            operation: inc
      # Host: zala
      - name: zala
        labels:
          host: zala
          ip: 10.10.11.8
          interface: eth0
        sequence:
          - time: 1
            eval_time: 1
            value: 1
            operation: inc
```

The generated metrics will be like this:

``` text
# HELP snmp_ifHCInOctets Inbound traffic on the interface
# TYPE snmp_ifHCInOctets counter
snmp_ifHCInOctets{host="apple",ip="10.10.11.2",interface="eth0"} 15.0
snmp_ifHCInOctets{host="grape",ip="10.10.11.5",interface="eth0"} 8.0
snmp_ifHCInOctets{host="zala",ip="10.10.11.8",interface="eth0"} 3.0

# HELP snmp_sysUpTimeInstance System uptime
# TYPE snmp_sysUpTimeInstance counter
snmp_sysUpTimeInstance{host="apple",ip="10.10.11.2",interface="eth0"} 120.0
snmp_sysUpTimeInstance{host="grape",ip="10.10.11.5",interface="eth0"} 120.0
snmp_sysUpTimeInstance{host="zala",ip="10.10.11.8",interface="eth0"} 120.0
```

### Supported keywords

#### Metric-level keywords:
- `name`: The [metric
  name](https://prometheus.io/docs/instrumenting/writing_clientlibs/#metric-names).
  [**Type**: string] [**Required**]
- `description`: The description to be shown as
  [HELP](https://prometheus.io/docs/instrumenting/writing_clientlibs/#metric-description-and-help).
  [**Type**: string] [**Required**]
- `type`: It should be one of the supported metric types, which you can see in the next section.
  [**Type**: string] [**Required**]
- `labels`: The labels that will be used with the metric. [**Type**: list of
  strings] [**Optional**]
- `instances`: List of metric instances, each with their own labels and sequences.
  [**Type**: list] [**Required**]

#### Instance-level keywords:
- `instances.name`: Name identifier for this metric instance. [**Type**: string] [**Optional**]
- `instances.labels`: The label values for this specific instance. They must match
  the metric-level `labels` definition. [**Type**: dict] [**Required**]
- `instances.sequence`: List of update sequences for this instance. [**Type**: list] [**Required**]

#### Sequence-level keywords:
- `instances.sequence.eval_time`: Number of seconds that the sequence will be running.
  [**Type**: int] [**Required**]
- `instances.sequence.interval`: The interval of seconds between each operation will be
  performed. 1 second is a sane number. [**Type**: int] [**Required**]
- `instances.sequence.value`: The value that the operation will apply. It must be a single
  value. You must choose between `value` and `range`. [**Type**: int] [**Optional**]
- `instances.sequence.range`: The range of values that will randomly be choosed and the
  operation will apply. It must be two range separed by a dash. You must choose
  between `value` and `range`. [**Type**: string (int-int / float-float)] [**Optional**]
- `instances.sequence.operation`: The operation that will be applied. It only will be used
  with the gauge type, and you can choose between `inc`, `dec` or `set`. [**Optional**]

### Supported metric types

The ones defined [here](https://prometheus.io/docs/concepts/metric_types/).
- Counter
- Gauge
- Histogram
- Summary

## Manual use

```bash
git clone https://github.com/mksmki/prometheus-data-generator.git
virtualenv -p python3 venv
pip install -r requirements.txt
python prometheus_data_generator/main.py
curl localhost:9000/metrics/
```

## Use in docker

``` bash
wget https://raw.githubusercontent.com/mksmki/prometheus-data-generator/master/config.yml
docker run -ti -v `pwd`/config.yml:/config.yml -p 127.0.0.1:9000:9000 \
    littleangryclouds/prometheus-data-generator
curl localhost:9000/metrics/
```

## Use in kubernetes

There's some example manifests in the `kubernetes` directory. There's defined a
service, configmap, deployment (with
[configmap-reload](https://github.com/jimmidyson/configmap-reload) configured)
and a Service Monitor to be used with the [prometheus
operator](https://github.com/coreos/prometheus-operator).

You may deploy the manifests:

``` bash
kubectl create namespace prom-data-gen
kubectl -n prom-data-gen apply -f kubernetes/
kubectl -n prom-data-gen port-forward service/prometheus-data-generator 9000:9000
curl localhost:9000/metrics/
```

You can edit the configmap as you wish and the configmap-reload will
eventually reload the configuration without killing the pod.

## Generate prometheus alerts unit tests

TODO

## Tests

TODO
