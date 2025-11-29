# Monitoring and Observability

This directory contains monitoring, alerting, and observability configurations for SmartHR360.

## Components

### Prometheus

- Metrics collection from application and infrastructure
- Service discovery for Kubernetes pods
- Metric retention and aggregation

### Grafana

- Dashboards for application and infrastructure metrics
- Alerting rules and notification channels
- Data visualization

### Fluentd/Loki

- Log aggregation from all pods
- Centralized log storage
- Log search and filtering

### Alert Manager

- Alert routing and grouping
- Integration with Slack, PagerDuty, email
- Silence and inhibition rules

## Setup

1. Install monitoring stack:

```bash
kubectl apply -f monitoring/prometheus/
kubectl apply -f monitoring/grafana/
kubectl apply -f monitoring/alertmanager/
```

2. Configure dashboards:

```bash
kubectl apply -f monitoring/dashboards/
```

3. Setup alerts:

```bash
kubectl apply -f monitoring/alerts/
```

## Access

- Prometheus: http://prometheus.smarthr360.com
- Grafana: http://grafana.smarthr360.com
- AlertManager: http://alertmanager.smarthr360.com
