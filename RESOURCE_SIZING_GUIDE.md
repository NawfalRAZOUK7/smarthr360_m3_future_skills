# SmartHR360 - Resource Sizing & Cluster Capacity Guide

## 📊 Resource Requirements Overview

### Minimum Production Deployment

| Component     | Replicas | CPU Request | Memory Request | CPU Limit | Memory Limit |
| ------------- | -------- | ----------- | -------------- | --------- | ------------ |
| API           | 3        | 500m        | 1Gi            | 1000m     | 2Gi          |
| Celery Worker | 2        | 500m        | 1Gi            | 1500m     | 3Gi          |
| Celery Beat   | 1        | 100m        | 256Mi          | 250m      | 512Mi        |
| PostgreSQL    | 1        | 250m        | 512Mi          | 1000m     | 2Gi          |
| Redis         | 1        | 100m        | 256Mi          | 500m      | 1Gi          |
| **Total**     | **8**    | **2.45**    | **4.512Gi**    | **7.75**  | **14.512Gi** |

### Maximum with Horizontal Pod Autoscaler (HPA)

| Component     | Max Replicas | CPU Request | Memory Request | CPU Limit | Memory Limit |
| ------------- | ------------ | ----------- | -------------- | --------- | ------------ |
| API           | 10           | 5000m       | 10Gi           | 10000m    | 20Gi         |
| Celery Worker | 8            | 4000m       | 8Gi            | 12000m    | 24Gi         |
| Celery Beat   | 1            | 100m        | 256Mi          | 250m      | 512Mi        |
| PostgreSQL    | 1            | 250m        | 512Mi          | 1000m     | 2Gi          |
| Redis         | 1            | 100m        | 256Mi          | 500m      | 1Gi          |
| **Total**     | **21**       | **9.45**    | **19.024Gi**   | **23.75** | **47.512Gi** |

### Storage Requirements (PersistentVolumeClaims)

| Volume        | Size      | Access Mode   | Used By                |
| ------------- | --------- | ------------- | ---------------------- |
| postgres-pvc  | 100Gi     | ReadWriteOnce | PostgreSQL StatefulSet |
| redis-pvc     | 10Gi      | ReadWriteOnce | Redis Deployment       |
| media-pvc     | 50Gi      | ReadWriteMany | API, Celery Workers    |
| ml-models-pvc | 20Gi      | ReadWriteMany | API, Celery Workers    |
| logs-pvc      | 30Gi      | ReadWriteMany | All components         |
| **Total**     | **210Gi** |               |                        |

---

## 🎯 Recommended Cluster Configurations

### 1. Small Development/Testing Cluster

**Suitable for:** Development, testing, demo environments

**Cluster Size:**

- **Nodes**: 2-3 nodes
- **Node Size**: 4 vCPU, 8GB RAM per node
- **Total**: 8-12 vCPU, 16-24GB RAM

**Configuration Adjustments:**

```yaml
# Reduce replicas in deployment files
API: replicas: 2
Celery Worker: replicas: 1

# Adjust HPA minimums
API HPA: minReplicas: 2, maxReplicas: 4
Worker HPA: minReplicas: 1, maxReplicas: 3

# Reduce resource requests
API: requests: { cpu: 250m, memory: 512Mi }
Worker: requests: { cpu: 250m, memory: 512Mi }
```

**Storage:** Use gp2/standard storage class (cheaper)

### 2. Medium Production Cluster

**Suitable for:** Small to medium production workloads (< 10,000 requests/day)

**Cluster Size:**

- **Nodes**: 3-5 nodes
- **Node Size**: 4 vCPU, 16GB RAM per node
- **Total**: 12-20 vCPU, 48-80GB RAM

**Configuration:** Use default settings as provided

**Storage:** Use gp3/ssd storage class for better performance

### 3. Large Production Cluster

**Suitable for:** High-traffic production (> 50,000 requests/day)

**Cluster Size:**

- **Nodes**: 5-10 nodes
- **Node Size**: 8 vCPU, 32GB RAM per node
- **Total**: 40-80 vCPU, 160-320GB RAM

**Configuration Adjustments:**

```yaml
# Increase replicas
API: replicas: 5
Celery Worker: replicas: 4

# Adjust HPA for more headroom
API HPA: minReplicas: 5, maxReplicas: 15
Worker HPA: minReplicas: 4, maxReplicas: 12

# Increase resource limits
API: limits: { cpu: 2000m, memory: 4Gi }
Worker: limits: { cpu: 2000m, memory: 4Gi }
PostgreSQL: limits: { cpu: 2000m, memory: 4Gi }
```

**Storage:** Use provisioned IOPS storage for databases

---

## ☁️ Cloud Provider Specific Recommendations

### AWS (EKS)

#### Small Cluster

```bash
# Node group configuration
Instance Type: t3.large (2 vCPU, 8GB RAM)
Min Size: 2
Max Size: 4
Desired: 2
```

**Storage Classes:**

- Database: `gp3` (general purpose SSD)
- Application: `gp2` or `gp3`
- High performance: `io1` or `io2`

**Cost Estimate:** ~$150-200/month

#### Medium Cluster

```bash
Instance Type: t3.xlarge (4 vCPU, 16GB RAM)
Min Size: 3
Max Size: 5
Desired: 3
```

**Cost Estimate:** ~$350-500/month

#### Large Cluster

```bash
Instance Type: m5.2xlarge (8 vCPU, 32GB RAM)
Min Size: 5
Max Size: 10
Desired: 5
```

**Cost Estimate:** ~$1,200-2,000/month

### Google Cloud (GKE)

#### Small Cluster

```bash
Machine Type: n1-standard-2 (2 vCPU, 7.5GB RAM)
Number of nodes: 3
```

**Storage Classes:**

- Database: `pd-ssd` (SSD persistent disk)
- Application: `pd-standard` (standard persistent disk)

**Cost Estimate:** ~$120-180/month

#### Medium Cluster

```bash
Machine Type: n1-standard-4 (4 vCPU, 15GB RAM)
Number of nodes: 3
```

**Cost Estimate:** ~$300-450/month

#### Large Cluster

```bash
Machine Type: n1-standard-8 (8 vCPU, 30GB RAM)
Number of nodes: 5
```

**Cost Estimate:** ~$1,000-1,500/month

### Azure (AKS)

#### Small Cluster

```bash
VM Size: Standard_D2s_v3 (2 vCPU, 8GB RAM)
Node count: 3
```

**Storage Classes:**

- Database: `managed-premium` (Premium SSD)
- Application: `default` (Standard HDD)

**Cost Estimate:** ~$140-200/month

#### Medium Cluster

```bash
VM Size: Standard_D4s_v3 (4 vCPU, 16GB RAM)
Node count: 3
```

**Cost Estimate:** ~$320-480/month

#### Large Cluster

```bash
VM Size: Standard_D8s_v3 (8 vCPU, 32GB RAM)
Node count: 5
```

**Cost Estimate:** ~$1,100-1,600/month

### DigitalOcean Kubernetes

#### Small Cluster

```bash
Droplet Size: s-2vcpu-4gb (2 vCPU, 4GB RAM)
Node count: 3
```

**Cost Estimate:** ~$60-90/month

#### Medium Cluster

```bash
Droplet Size: s-4vcpu-8gb (4 vCPU, 8GB RAM)
Node count: 3
```

**Cost Estimate:** ~$120-180/month

#### Large Cluster

```bash
Droplet Size: s-8vcpu-16gb (8 vCPU, 16GB RAM)
Node count: 5
```

**Cost Estimate:** ~$400-600/month

---

## 🔧 Resource Optimization Tips

### 1. CPU Optimization

**For API Pods:**

- Use `gthread` worker class for better CPU utilization
- Adjust workers: `(2 × CPU cores) + 1`
- Monitor CPU usage and adjust requests/limits

**For Celery Workers:**

- Set concurrency based on task type:
  - CPU-bound tasks: `concurrency = CPU cores`
  - I/O-bound tasks: `concurrency = (CPU cores × 2)`
- Use task queues to separate different workloads

### 2. Memory Optimization

**Reduce Memory Usage:**

```yaml
# Use memory-efficient settings in ConfigMap
GUNICORN_MAX_REQUESTS: "1000" # Restart workers periodically
GUNICORN_MAX_REQUESTS_JITTER: "50"
CELERY_WORKER_MAX_TASKS_PER_CHILD: "1000" # Prevent memory leaks
```

**Monitor Memory:**

```bash
kubectl top pods -n smarthr360
kubectl describe pod <pod-name> -n smarthr360 | grep -A 5 "Limits"
```

### 3. Storage Optimization

**Use appropriate storage classes:**

- **Hot data** (database): Premium SSD
- **Warm data** (media files): Standard SSD
- **Cold data** (logs, backups): Standard HDD

**Enable storage compression:**

```yaml
# For PostgreSQL
POSTGRES_INITDB_ARGS: "--data-checksums --encoding=UTF8"
```

**Implement retention policies:**

```python
# Celery beat task for log cleanup
@periodic_task(run_every=timedelta(days=7))
def cleanup_old_logs():
    # Delete logs older than 30 days
    pass
```

### 4. Network Optimization

**Use Network Policies** (already configured):

- Restrict pod-to-pod communication
- Only allow necessary traffic
- Reduces attack surface and network overhead

**Enable Compression:**

```yaml
# In Ingress annotations
nginx.ingress.kubernetes.io/enable-compression: "true"
```

---

## 📈 Scaling Guidelines

### When to Scale Up (Add Resources)

**Indicators:**

- CPU usage > 70% consistently
- Memory usage > 80% consistently
- Response times increasing
- Request queue growing
- Pod restarts due to OOM

**Actions:**

```bash
# Increase HPA max replicas
kubectl edit hpa smarthr360-api-hpa -n smarthr360

# Or increase resource limits
kubectl edit deployment smarthr360-api -n smarthr360
```

### When to Scale Down

**Indicators:**

- CPU usage < 30% for extended periods
- Memory usage < 40%
- Low traffic patterns
- Cost optimization needed

**Actions:**

```bash
# Reduce minimum replicas
kubectl scale deployment smarthr360-api --replicas=2 -n smarthr360

# Or adjust HPA minimum
kubectl edit hpa smarthr360-api-hpa -n smarthr360
```

### Horizontal vs Vertical Scaling

**Horizontal Scaling (More Pods):**

- ✅ Better for handling traffic spikes
- ✅ Improved fault tolerance
- ✅ Automatic with HPA
- ❌ Requires ReadWriteMany volumes for stateful apps

**Vertical Scaling (Bigger Pods):**

- ✅ Better for memory-intensive tasks
- ✅ Simpler architecture
- ❌ Requires pod restart
- ❌ Limited by node size

---

## 🎯 Cost Optimization Strategies

### 1. Use Spot/Preemptible Instances

- Save 60-80% on compute costs
- Suitable for stateless workloads (API, Celery workers)
- Not recommended for databases

### 2. Right-Size Resources

- Start with lower requests/limits
- Monitor actual usage for 1-2 weeks
- Adjust based on real data

### 3. Implement Autoscaling

- Use HPA for workloads
- Use Cluster Autoscaler for nodes
- Scale down during off-peak hours

### 4. Optimize Storage

- Use lifecycle policies for old data
- Implement data compression
- Use appropriate storage classes

### 5. Resource Quotas

```bash
# Set namespace quotas to prevent runaway costs
kubectl apply -f - <<EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: smarthr360-quota
  namespace: smarthr360
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "25"
    limits.memory: 50Gi
    persistentvolumeclaims: "10"
EOF
```

---

## 📊 Monitoring Resource Usage

### CPU and Memory

```bash
# Real-time monitoring
kubectl top pods -n smarthr360
kubectl top nodes

# Watch for changes
watch kubectl top pods -n smarthr360
```

### HPA Status

```bash
# Check autoscaler status
kubectl get hpa -n smarthr360

# Detailed HPA metrics
kubectl describe hpa smarthr360-api-hpa -n smarthr360
```

### Storage Usage

```bash
# Check PVC usage
kubectl get pvc -n smarthr360

# Check actual disk usage in pods
kubectl exec -it $API_POD -n smarthr360 -- df -h
```

### Set Up Alerts

```bash
# Example Prometheus alert rules
groups:
- name: smarthr360
  rules:
  - alert: HighCPUUsage
    expr: sum(rate(container_cpu_usage_seconds_total{namespace="smarthr360"}[5m])) > 0.8
    annotations:
      summary: "High CPU usage in smarthr360 namespace"

  - alert: HighMemoryUsage
    expr: sum(container_memory_usage_bytes{namespace="smarthr360"}) > 80000000000
    annotations:
      summary: "High memory usage in smarthr360 namespace"
```

---

## 🔍 Capacity Planning Checklist

- [ ] Estimate expected traffic (requests per second/minute/hour)
- [ ] Calculate required compute resources based on traffic
- [ ] Add 30-50% buffer for growth and peaks
- [ ] Consider database size growth (plan for 6-12 months)
- [ ] Plan for high availability (minimum 3 nodes)
- [ ] Budget for storage backups (2-3x production storage)
- [ ] Account for monitoring and logging overhead (10-20%)
- [ ] Test scaling under load before production
- [ ] Document baseline metrics for future comparison
- [ ] Set up alerting for resource thresholds

---

## 📞 Need Help?

If you need assistance with resource sizing:

1. Review actual metrics from similar applications
2. Start with medium configuration
3. Monitor for 1-2 weeks
4. Adjust based on real usage patterns

**Remember:** It's easier to scale up than down. Start conservative and scale as needed.

---

**Last Updated:** November 28, 2025  
**Version:** 1.0.0
