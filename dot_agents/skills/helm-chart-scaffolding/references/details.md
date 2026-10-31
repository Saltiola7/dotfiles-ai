# helm-chart-scaffolding — detailed patterns and worked examples

## Scope of these examples

Use only the pattern relevant to the selected workload and supported Kubernetes/
Helm version. Values, namespaces, image versions, resource sizing and provider
annotations are illustrative, not deployment defaults or universal gates. Read
existing project facts before asking about a missing material decision. Local
rendering, server admission and rollout health require distinct evidence. Live
commands, dependency downloads, hooks, debug workloads and credential changes
remain under the primary's current task scope and native permissions. Do not
print secrets or infer authorization from a command example.


## Helm Overview

**Helm** is the package manager for Kubernetes that:

- Templates Kubernetes manifests for reusability
- Manages application releases and rollbacks
- Handles dependencies between charts
- Provides version control for deployments
- Simplifies configuration management across environments

## Step-by-Step Workflow

### 1. Initialize Chart Structure

**Create new chart:**

```bash
helm create my-app
```

**Standard chart structure:**

```
my-app/
├── Chart.yaml           # Chart metadata
├── values.yaml          # Default configuration values
├── charts/              # Chart dependencies
├── templates/           # Kubernetes manifest templates
│   ├── NOTES.txt       # Post-install notes
│   ├── _helpers.tpl    # Template helpers
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── serviceaccount.yaml
│   ├── hpa.yaml
│   └── tests/
│       └── test-connection.yaml
└── .helmignore         # Files to ignore
```

### 2. Configure Chart.yaml

**Chart metadata defines the package:**

```yaml
apiVersion: v2
name: my-app
description: A Helm chart for My Application
type: application
version: 1.0.0 # Chart version
appVersion: "2.1.0" # Application version

# Keywords for chart discovery
keywords:
  - web
  - api
  - backend

# Maintainer information
maintainers:
  - name: DevOps Team
    email: devops@example.com
    url: https://github.com/example/my-app

# Source code repository
sources:
  - https://github.com/example/my-app

# Homepage
home: https://example.com

# Chart icon
icon: https://example.com/icon.png

# Dependencies
dependencies:
  - name: postgresql
    version: "12.0.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
  - name: redis
    version: "17.0.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
```

**Reference:** See `assets/Chart.yaml.template` for complete example

### 3. Design values.yaml Structure

**Organize values hierarchically:**

```yaml
# Image configuration
image:
  repository: myapp
  tag: "1.0.0"
  pullPolicy: IfNotPresent

# Number of replicas
replicaCount: 3

# Service configuration
service:
  type: ClusterIP
  port: 80
  targetPort: 8080

# Ingress configuration
ingress:
  enabled: false
  className: nginx
  hosts:
    - host: app.example.com
      paths:
        - path: /
          pathType: Prefix

# Resources
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"

# Autoscaling
autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

# Environment variables
env:
  - name: LOG_LEVEL
    value: "info"

# ConfigMap data
configMap:
  data:
    APP_MODE: production

# Dependencies
postgresql:
  enabled: true
  auth:
    database: myapp
    username: myapp

redis:
  enabled: false
```

**Reference:** See `assets/values.yaml.template` for complete structure

### 4. Create Template Files

**Use Go templating with Helm functions:**

**templates/deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "my-app.fullname" . }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "my-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "my-app.selectorLabels" . | nindent 8 }}
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - name: http
          containerPort: {{ .Values.service.targetPort }}
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
        env:
          {{- toYaml .Values.env | nindent 12 }}
```

### 5. Create Template Helpers

**templates/\_helpers.tpl:**

```yaml
{{/*
Expand the name of the chart.
*/}}
{{- define "my-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "my-app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "my-app.labels" -}}
helm.sh/chart: {{ include "my-app.chart" . }}
{{ include "my-app.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "my-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "my-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

### 6. Manage Dependencies

Update/build only within authorized dependency work; these commands may fetch
artifacts or rewrite locks. Ordinary validation does not resolve missing packages.


**Add dependencies in Chart.yaml:**

```yaml
dependencies:
  - name: postgresql
    version: "12.0.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
```

**Update dependencies:**

```bash
helm dependency update
helm dependency build
```

**Override dependency values:**

```yaml
# values.yaml
postgresql:
  enabled: true
  auth:
    database: myapp
    username: myapp
    existingSecret: "<approved-existing-secret>"
  primary:
    persistence:
      enabled: true
      size: 10Gi
```

### 7. Test and Validate

**Validation commands:**

```bash
# Lint the chart
helm lint my-app/

# Local rendering; not server admission or rollout evidence
helm template validation ./my-app > /dev/null

# Template rendering
helm template validation ./my-app > /dev/null

# Template with values
helm template validation ./my-app -f "$VALUES_FILE" > /dev/null

# Inspect only relevant non-secret chart defaults; default values are not
# necessarily the computed values for a particular release/override set.
```

**Bounded local helper:** Use the reviewed [validation helper](../scripts/validate-chart.sh)
for local lint/render checks. It preserves command failures and does not fetch
dependencies, install a release or claim server admission. Do not add `--validate`
or a live installation to make a local check appear more complete.

### 8. Package and Distribute

**Package the chart:**

```bash
helm package my-app/
# Creates: my-app-1.0.0.tgz
```

**Create chart repository:**

```bash
# Create index
helm repo index .

# Upload to repository
# AWS S3 example
aws s3 sync . s3://my-helm-charts/ --exclude "*" --include "*.tgz" --include "index.yaml"
```

**Use the chart:**

```bash
helm repo add my-repo https://charts.example.com
helm repo update
helm install "$RELEASE" my-repo/my-app --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE"
```

### 9. Multi-Environment Configuration

**Environment-specific values files:**

```
my-app/
├── values.yaml          # Defaults
├── values-dev.yaml      # Development
├── values-staging.yaml  # Staging
└── values-prod.yaml     # Production
```

**values-prod.yaml:**

```yaml
replicaCount: 5

image:
  tag: "2.1.0"

resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20

ingress:
  enabled: true
  hosts:
    - host: app.example.com
      paths:
        - path: /
          pathType: Prefix

postgresql:
  enabled: true
  primary:
    persistence:
      size: 100Gi
```

**Install with environment:**

```bash
helm install "$RELEASE" ./my-app -f "$VALUES_FILE" --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE"
```

### 10. Implement Hooks and Tests

**Pre-install hook (only for an explicitly selected, bounded migration contract):**

```yaml
# templates/pre-install-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "my-app.fullname" . }}-db-setup
  annotations:
    "helm.sh/hook": pre-install
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  template:
    spec:
      containers:
      - name: db-setup
        image: "<approved-migration-image>@sha256:<digest>"
        command: ["/app/bin/approved-migration"]
      restartPolicy: Never
```

**Test connection:**

```yaml
# templates/tests/test-connection.yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "my-app.fullname" . }}-test-connection"
  annotations:
    "helm.sh/hook": test
spec:
  containers:
  - name: wget
    image: "<approved-test-image>@sha256:<digest>"
    command: ['wget']
    args: ['{{ include "my-app.fullname" . }}:{{ .Values.service.port }}']
  restartPolicy: Never
```

**Run tests only for an authorized target release; this executes cluster workloads:**

```bash
helm test "$RELEASE" --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE"
```

## Common Patterns

### Pattern 1: Conditional Resources

```yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "my-app.fullname" . }}
spec:
  # ...
{{- end }}
```

### Pattern 2: Iterating Over Lists

```yaml
env:
{{- range .Values.env }}
- name: {{ .name }}
  value: {{ .value | quote }}
{{- end }}
```

### Pattern 3: Including Files

```yaml
data:
  config.yaml: |
    {{- .Files.Get "config/application.yaml" | nindent 4 }}
```

### Pattern 4: Global Values

```yaml
global:
  imageRegistry: docker.io
  imagePullSecrets:
    - name: regcred

# Use in templates:
image: {{ .Values.global.imageRegistry }}/{{ .Values.image.repository }}
```
