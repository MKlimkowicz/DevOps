#!/bin/bash
set -e

PROJECT_NAME=$1
ENVIRONMENT=$2
INSTANCE_NAME=$3

echo "Setting up PostgreSQL database on $INSTANCE_NAME instance..."

# Set up kubectl configuration
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Wait for k3s to be ready
sleep 60
until kubectl cluster-info >/dev/null 2>&1; do
    echo "Waiting for k3s cluster..."
    sleep 10
done

# Get region
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone 2>/dev/null)
REGION=$(echo "$AZ" | sed 's/[a-z]$//' || echo "eu-central-1")

# Get PostgreSQL password
POSTGRES_PASSWORD=$(aws ssm get-parameter --name "/$PROJECT_NAME/$ENVIRONMENT/postgres/password" --with-decryption --query 'Parameter.Value' --output text --region "$REGION")

# Create database namespace
kubectl create namespace database || true

# Install PostgreSQL using Bitnami chart
helm upgrade --install postgresql bitnami/postgresql \
  --namespace database \
  --set auth.postgresPassword="$POSTGRES_PASSWORD" \
  --set auth.database="appdb" \
  --set primary.persistence.enabled=true \
  --set primary.persistence.size=10Gi \
  --set primary.service.type=NodePort \
  --set primary.service.nodePorts.postgresql=30432 \
  --wait --timeout=10m

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n database --timeout=600s

# Get pod name and create sample data
POSTGRES_POD=$(kubectl get pods -n database -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n database "$POSTGRES_POD" -- psql -U postgres -d appdb -c "
CREATE TABLE IF NOT EXISTS sample_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metric_name VARCHAR(100),
    metric_value FLOAT,
    instance_id VARCHAR(50)
);
INSERT INTO sample_metrics (metric_name, metric_value, instance_id) VALUES
('cpu_usage', 45.2, 'i-1234567890abcdef0'),
('memory_usage', 67.8, 'i-1234567890abcdef0'),
('disk_usage', 23.1, 'i-1234567890abcdef0');
"

# Install Node Exporter with proper health checks
cat > /tmp/node-exporter.yaml << 'EOF'
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: database
  labels:
    app: node-exporter
    component: metrics
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
        component: metrics
    spec:
      hostNetwork: true
      hostPID: true
      tolerations:
      - operator: Exists
        effect: NoSchedule
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.7.0
        args:
          - '--path.procfs=/host/proc'
          - '--path.sysfs=/host/sys'
          - '--path.rootfs=/host/root'
          - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc|rootfs/var/lib/docker/containers|rootfs/var/lib/docker/overlay2|rootfs/run/docker/netns|rootfs/var/lib/docker/aufs)($$|/)'
          - '--web.listen-address=0.0.0.0:9100'
        ports:
        - containerPort: 9100
          hostPort: 9100
          name: metrics
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          mountPropagation: HostToContainer
          readOnly: true
        resources:
          limits:
            cpu: 200m
            memory: 256Mi
          requests:
            cpu: 100m
            memory: 128Mi
        livenessProbe:
          httpGet:
            path: /
            port: 9100
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /
            port: 9100
          initialDelaySeconds: 5
          periodSeconds: 10
        securityContext:
          runAsNonRoot: true
          runAsUser: 65534
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
---
apiVersion: v1
kind: Service
metadata:
  name: node-exporter
  namespace: database
  labels:
    app: node-exporter
    component: metrics
spec:
  ports:
  - port: 9100
    targetPort: 9100
    nodePort: 30100
    name: metrics
    protocol: TCP
  selector:
    app: node-exporter
  type: NodePort
EOF

echo "Deploying Node Exporter..."
kubectl apply -f /tmp/node-exporter.yaml

# Wait for Node Exporter to be ready
echo "Waiting for Node Exporter to be ready..."
kubectl wait --for=condition=ready pod -l app=node-exporter -n database --timeout=300s

# Verify Node Exporter is working
echo "Verifying Node Exporter functionality..."
for i in {1..10}; do
    if curl -f -s http://localhost:30100/metrics > /dev/null; then
        echo "✅ Node Exporter is responding on port 30100"
        break
    else
        echo "Attempt $i/10: Node Exporter not responding, waiting 10 seconds..."
        if [ $i -eq 10 ]; then
            echo "❌ Node Exporter verification failed"
            kubectl logs -n database daemonset/node-exporter --tail=20
            exit 1
        fi
        sleep 10
    fi
done

# Install PostgreSQL Exporter with enhanced configuration
POSTGRES_PASSWORD_ENCODED=$(echo "$POSTGRES_PASSWORD" | sed 's/#/%23/g; s/@/%40/g; s/ /%20/g; s/\$/%24/g')

cat > /tmp/postgres-exporter.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-exporter
  namespace: database
  labels:
    app: postgres-exporter
    component: metrics
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres-exporter
  template:
    metadata:
      labels:
        app: postgres-exporter
        component: metrics
    spec:
      containers:
      - name: postgres-exporter
        image: prometheuscommunity/postgres-exporter:v0.15.0
        ports:
        - containerPort: 9187
          name: metrics
        env:
        - name: DATA_SOURCE_NAME
          value: "postgresql://postgres:$POSTGRES_PASSWORD_ENCODED@postgresql.database.svc.cluster.local:5432/appdb?sslmode=disable"
        - name: PG_EXPORTER_WEB_LISTEN_ADDRESS
          value: "0.0.0.0:9187"
        - name: PG_EXPORTER_EXTEND_QUERY_PATH
          value: "/etc/postgres_exporter/queries.yaml"
        resources:
          limits:
            cpu: 200m
            memory: 256Mi
          requests:
            cpu: 100m
            memory: 128Mi
        livenessProbe:
          httpGet:
            path: /metrics
            port: 9187
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /metrics
            port: 9187
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        volumeMounts:
        - name: queries
          mountPath: /etc/postgres_exporter
          readOnly: true
      volumes:
      - name: queries
        configMap:
          name: postgres-exporter-queries
          defaultMode: 420
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-exporter-queries
  namespace: database
data:
  queries.yaml: |
    pg_replication:
      query: "SELECT CASE WHEN NOT pg_is_in_recovery() THEN 0 ELSE GREATEST (0, EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))) END AS lag"
      master: true
      metrics:
        - lag:
            usage: "GAUGE"
            description: "Replication lag behind master in seconds"
    
    pg_postmaster:
      query: "SELECT pg_postmaster_start_time as start_time_seconds from pg_postmaster_start_time()"
      master: true
      metrics:
        - start_time_seconds:
            usage: "GAUGE"
            description: "Time at which postmaster started"
    
    pg_stat_user_tables:
      query: |
        SELECT
          current_database() datname,
          schemaname,
          relname,
          seq_scan,
          seq_tup_read,
          idx_scan,
          idx_tup_fetch,
          n_tup_ins,
          n_tup_upd,
          n_tup_del,
          n_tup_hot_upd,
          n_live_tup,
          n_dead_tup,
          n_mod_since_analyze,
          COALESCE(last_vacuum, '1970-01-01Z') as last_vacuum,
          COALESCE(last_autovacuum, '1970-01-01Z') as last_autovacuum,
          COALESCE(last_analyze, '1970-01-01Z') as last_analyze,
          COALESCE(last_autoanalyze, '1970-01-01Z') as last_autoanalyze,
          vacuum_count,
          autovacuum_count,
          analyze_count,
          autoanalyze_count
        FROM pg_stat_user_tables
      metrics:
        - datname:
            usage: "LABEL"
            description: "Name of current database"
        - schemaname:
            usage: "LABEL"
            description: "Name of the schema that this table is in"
        - relname:
            usage: "LABEL"
            description: "Name of this table"
        - seq_scan:
            usage: "COUNTER"
            description: "Number of sequential scans initiated on this table"
        - seq_tup_read:
            usage: "COUNTER"
            description: "Number of live rows fetched by sequential scans"
        - idx_scan:
            usage: "COUNTER"
            description: "Number of index scans initiated on this table"
        - idx_tup_fetch:
            usage: "COUNTER"
            description: "Number of live rows fetched by index scans"
        - n_tup_ins:
            usage: "COUNTER"
            description: "Number of rows inserted"
        - n_tup_upd:
            usage: "COUNTER"
            description: "Number of rows updated"
        - n_tup_del:
            usage: "COUNTER"
            description: "Number of rows deleted"
        - n_tup_hot_upd:
            usage: "COUNTER"
            description: "Number of rows HOT updated"
        - n_live_tup:
            usage: "GAUGE"
            description: "Estimated number of live rows"
        - n_dead_tup:
            usage: "GAUGE"
            description: "Estimated number of dead rows"
        - n_mod_since_analyze:
            usage: "GAUGE"
            description: "Estimated number of rows changed since last analyze"
        - last_vacuum:
            usage: "GAUGE"
            description: "Last time at which this table was manually vacuumed"
        - last_autovacuum:
            usage: "GAUGE"
            description: "Last time at which this table was vacuumed by the autovacuum daemon"
        - last_analyze:
            usage: "GAUGE"
            description: "Last time at which this table was manually analyzed"
        - last_autoanalyze:
            usage: "GAUGE"
            description: "Last time at which this table was analyzed by the autovacuum daemon"
        - vacuum_count:
            usage: "COUNTER"
            description: "Number of times this table has been manually vacuumed"
        - autovacuum_count:
            usage: "COUNTER"
            description: "Number of times this table has been vacuumed by the autovacuum daemon"
        - analyze_count:
            usage: "COUNTER"
            description: "Number of times this table has been manually analyzed"
        - autoanalyze_count:
            usage: "COUNTER"
            description: "Number of times this table has been analyzed by the autovacuum daemon"
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-exporter
  namespace: database
  labels:
    app: postgres-exporter
    component: metrics
spec:
  ports:
  - port: 9187
    targetPort: 9187
    nodePort: 30187
    name: metrics
    protocol: TCP
  selector:
    app: postgres-exporter
  type: NodePort
EOF

echo "Deploying PostgreSQL Exporter..."
kubectl apply -f /tmp/postgres-exporter.yaml

# Wait for PostgreSQL Exporter to be ready
echo "Waiting for PostgreSQL Exporter to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres-exporter -n database --timeout=300s

# Enhanced PostgreSQL Exporter verification
echo "Verifying PostgreSQL Exporter functionality..."
EXPORTER_WORKING=false
for i in {1..15}; do
    echo "Attempt $i/15: Testing PostgreSQL Exporter connectivity..."
    
    # Test basic connectivity
    if ! curl -f -s http://localhost:30187/metrics > /dev/null; then
        echo "   PostgreSQL Exporter not responding on port 30187, waiting 10 seconds..."
        sleep 10
        continue
    fi
    
    # Test PostgreSQL connection via pg_up metric
    EXPORTER_RESPONSE=$(curl -s http://localhost:30187/metrics 2>/dev/null || echo "")
    if echo "$EXPORTER_RESPONSE" | grep -q "pg_up"; then
        PG_UP_VALUE=$(echo "$EXPORTER_RESPONSE" | grep "^pg_up" | head -1 | awk '{print $2}')
        if [ "$PG_UP_VALUE" = "1" ]; then
            echo "✅ PostgreSQL Exporter is responding correctly and connected to PostgreSQL"
            
            # Additional verification - check for key metrics
            if echo "$EXPORTER_RESPONSE" | grep -q "pg_stat_database_numbackends"; then
                echo "✅ Database connection metrics available"
                EXPORTER_WORKING=true
                break
            else
                echo "⚠️  Basic connection OK but database metrics may be limited"
                EXPORTER_WORKING=true
                break
            fi
        else
            echo "   PostgreSQL Exporter responding but not connected to PostgreSQL (pg_up=$PG_UP_VALUE)"
            
            # Debug connection issues
            echo "   Debugging PostgreSQL connection..."
            if kubectl exec -n database "$POSTGRES_POD" -- psql -U postgres -d appdb -c "SELECT 1;" > /dev/null 2>&1; then
                echo "   ✅ PostgreSQL is accessible directly"
                echo "   ❌ Exporter connection issue - checking logs..."
                kubectl logs -n database deployment/postgres-exporter --tail=20
            else
                echo "   ❌ PostgreSQL itself is not accessible"
            fi
        fi
    else
        echo "   PostgreSQL Exporter responding but no pg_up metric found"
        echo "   Response preview: $(echo "$EXPORTER_RESPONSE" | head -5)"
    fi
    
    sleep 10
done

if [ "$EXPORTER_WORKING" = "false" ]; then
    echo "❌ PostgreSQL Exporter failed to connect to PostgreSQL after 15 attempts"
    echo "Collecting diagnostic information..."
    echo "1. PostgreSQL Exporter pods:"
    kubectl get pods -n database -l app=postgres-exporter
    echo "2. PostgreSQL Exporter logs:"
    kubectl logs -n database deployment/postgres-exporter --tail=50
    echo "3. PostgreSQL connectivity test:"
    kubectl exec -n database "$POSTGRES_POD" -- psql -U postgres -d appdb -c "SELECT version();" || echo "PostgreSQL connection failed"
    echo "4. Network connectivity test:"
    kubectl exec -n database deployment/postgres-exporter -- nslookup postgresql.database.svc.cluster.local || echo "DNS resolution failed"
    
    echo "⚠️  Continuing setup, but PostgreSQL monitoring may not work properly"
fi

# Store private IP for cross-instance monitoring
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/private-ipv4)
aws ssm put-parameter \
    --name "/$PROJECT_NAME/$ENVIRONMENT/database/private-ip" \
    --value "$PRIVATE_IP" \
    --type "String" \
    --overwrite \
    --region "$REGION" || echo "Warning: Could not store IP"

# Final verification and summary
echo "============================================"
echo "✅ PostgreSQL database setup completed!"
echo "============================================"
echo "📍 Database Access Information:"
echo "   Host: $PRIVATE_IP:30432"
echo "   Database: appdb"
echo "   Username: postgres"
echo "   Password: Stored in Parameter Store"
echo ""
echo "📊 Exporter Status:"
echo "   Node Exporter: http://$PRIVATE_IP:30100/metrics"
echo "   PostgreSQL Exporter: http://$PRIVATE_IP:30187/metrics"
echo ""
echo "🔧 Kubernetes Resources:"
kubectl get pods,svc -n database
echo "============================================"
