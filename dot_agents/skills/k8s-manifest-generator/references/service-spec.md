# Service design and diagnostic reference

Use the project's supported Kubernetes/distribution and network-controller
versions. Example ports, annotations, namespaces and service types are illustrative;
they do not authorize public exposure or a provider migration.

## Service types and ownership

- **ClusterIP:** the ordinary internal virtual-IP Service. Exposure still depends
  on routes, gateways, policy and attached infrastructure; the name alone is not
  a proof of isolation.
- **Headless:** `clusterIP: None` exposes endpoint discovery rather than the usual
  virtual-IP load-balancing behavior. Stateful workloads often need per-Pod identity;
  discovery and readiness behavior must match the client contract.
- **NodePort:** exposes a selected port through nodes under the cluster's networking
  and policy. Do not assume node addresses or firewalls permit external access.
- **LoadBalancer:** requests the installed controller's supported implementation.
  Public/private selection, address allocation, source restrictions, health and
  cost are provider/controller-specific decisions. Do not copy AWS/GCP annotations
  into another provider or infer desired public access.
- **ExternalName:** supplies a DNS alias, not ordinary proxying or port translation.
  Client DNS, Host headers and TLS names can affect whether it works.

Ingress and Gateway APIs/controllers provide additional routing capabilities;
they do not follow automatically from a Service's existence. Establish the owner,
protocol, TLS termination, exposure, client identity and recovery requirements.

## Selectors, ports and endpoint discovery

A selector must match the intended backend labels. Verify actual Pod ownership
and revision; a broad selector can accidentally route to unrelated workloads.
Services without selectors need explicitly owned backend discovery rather than
an assumption that the control plane creates it.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: <service-name>
  namespace: <namespace>
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: <workload-name>
  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
```

The named targetPort must resolve to the intended backend container port. A
containerPort declaration does not itself make the process listen, and Service
creation does not prove that the backend implements the application protocol.
Name multiple ports distinctly and preserve client compatibility when changing
ports, selectors or DNS names. Protocol and appProtocol support depend on the
actual implementation/version.

Prefer current EndpointSlice evidence for backend discovery. A slice may contain
ready, serving or terminating conditions; inspect the condition relevant to the
routing contract rather than counting addresses alone. EndpointSlice presence
proves neither network reachability nor application health. A legacy Endpoints
object can be incomplete or inappropriate for the current cluster/version.

## DNS, topology and traffic policy

A short Service name is resolved relative to a Pod's search domains. Cross-
namespace names and full service DNS names have different assumptions; establish
namespace and configured cluster domain instead of hardcoding cluster.local.
Environment-variable service discovery can be stale or absent and should not be
assumed equivalent to DNS.

`externalTrafficPolicy`, `internalTrafficPolicy`, topology preferences and
sessionAffinity have distinct load distribution, source-address and availability
consequences. For example, Local traffic policies need suitable local endpoints;
select them from the intended behavior and supported network implementation.
ClientIP affinity is a routing feature, not authentication or a guarantee that
application state remains available after a Pod change.

Validate supported dual-stack/address-family and service-allocation behavior
against the actual cluster. Do not infer it from a copied Service field or a
single successful connection.

## TLS, access and provider integration

Resolve where TLS terminates and which identities/hosts clients verify. A
certificate Secret reference is not proof of successful trust or rotation.
Public/internal load-balancer annotations, health-check settings and firewall
management belong to the selected controller/provider and project policy.
Changing a Service type can create billable resources and alter exposure.

Do not disable network policy, broaden source ranges or open a public endpoint to
make a test pass. Preserve the selected ingress/egress and secret authorities;
return any required scoped change to the primary with validation and recovery.

## Scoped diagnostics

Use resolved context and namespace, with the exact Service and relevant workload:

```bash
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get service "$SERVICE" -o jsonpath='{.spec.selector}'
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get endpointslices --selector "kubernetes.io/service-name=$SERVICE" -o json
```

Inspect only relevant endpoint identity, ports and conditions; redact sensitive
configuration before retaining evidence. Check the corresponding backend's
readiness and actual listening/protocol behavior, applicable NetworkPolicies,
DNS, route/controller health and client-side errors. Empty endpoints can mean a
selector/readiness issue, not only a process that failed to start.

Execution probes from an existing Pod or a new debug Pod require the appropriate
task scope and permissions. Do not create a workload with an unpinned image or
install tools as an incidental read-only check. A failed/offline query is a
capability gap; it cannot establish that a permissive network change is needed.

## Primary references

- [Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
