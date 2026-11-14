# Project Context

## 1. Product summary

This project is a unified application security, exposure, and resilience platform.

It continuously discovers how an application works, what it depends on, and what happens when a dependency becomes unavailable or degraded. It connects runtime dependencies and infrastructure to business capabilities and user journeys.

An engineer can select or enter:

- An AWS service
- An AWS API operation
- A domain, URL, or IP address
- An internal microservice
- A database, queue, or stream
- An identity provider
- An operational service such as AWS Systems Manager
- A network or authentication path

The platform then answers:

1. Does the application use this dependency?
2. What evidence proves that it is used?
3. Which components call it?
4. Which user journeys and business capabilities depend on it?
5. What is predicted to fail if the dependency becomes unavailable?
6. Can that failure be simulated safely?
7. What actually failed during the experiment?
8. How far did the failure spread?
9. Did fallbacks, retries, circuit breakers, monitoring, and recovery work?
10. How long did the application take to recover?

The main outcome is not a list of failed resources. It is a capability-level impact report.

## Platform vision

The destination is a central application security, exposure, and resilience workspace. One evidence-backed application graph connects:

- Business capabilities, user journeys, owners, criticality, and recovery objectives.
- Services, APIs, cloud resources, databases, queues, and external dependencies.
- Identities, permissions, network reachability, exposure, packages, and known vulnerabilities.
- Failure propagation, fallbacks, monitoring, administrative access, recovery paths, and experiment results.

The application is the entry point: select an application, inspect capabilities and dependencies, investigate exposure, predict impact, validate through controlled experiments, and review evidence and recommended actions.

Example questions include: Is a vulnerable service reachable, which customer capability depends on it, and what would isolation affect? If the identity provider fails, can customers log in and can engineers still access recovery systems?

Integrate existing scanners, inventories, and telemetry through collectors. Preserve provenance and limitations rather than rebuilding every tool. Every assessment must expose sources, recency, confidence, and coverage gaps. Missing or stale evidence means unknown, not healthy or secure. A confirmed dependency does not confirm a predicted failure; predictions and observations remain separate. Do not invent completeness percentages without a measurable denominator.

The hackathon is the first validated resilience path through this shared foundation. Broader security integrations remain staged later work.

## 2. Core example

Suppose the user enters:

`dynamodb.us-east-1.amazonaws.com`

The platform should:

1. Search runtime evidence to determine whether the application uses the endpoint.
2. Identify callers and operations such as `GetItem` and `PutItem`.
3. Connect those calls to application capabilities.
4. Predict the impact of losing the endpoint.
5. Offer a safe experiment against a local, staging, or canary target.
6. Inject a temporary fault such as latency, throttling, HTTP 500, or HTTP 503.
7. Run health checks and user-journey probes.
8. Automatically remove the fault.
9. Compare predicted and observed results.

A useful report might state:

- Product browsing remained available.
- Cart reads remained available through cache.
- Order creation failed because `PutItem` returned 503.
- SQS backlog increased by 842 messages.
- The circuit breaker opened after 17 seconds.
- Normal service recovered 94 seconds after restoration.

## 3. Why this is needed

Existing tools usually cover only part of the problem:

- Infrastructure inventory describes resources but may not explain business impact.
- Tracing shows runtime calls but not all IAM, firewall, recovery, or supply-chain relationships.
- Chaos tools inject faults but require the operator to already understand the target and blast radius.
- Security scanners report vulnerabilities but may not show which user journeys depend on the affected component.
- Cloud-native resilience tools may be limited to one provider or supported resource set.

The proposed platform joins these views through an evidence-backed application graph.

## 4. Application capability model

The system must model application behavior above the infrastructure layer.

Example capabilities:

- User login
- Product search
- Cart management
- Checkout
- Payment processing
- Notifications
- Deployment
- Monitoring
- Incident recovery
- Administrative access

Each capability should eventually include:

- Stable identifier and name
- Description
- Owner
- Criticality
- Related user journeys
- Availability objective
- RTO and RPO when applicable
- Required services and data
- External dependencies
- Fallback and recovery expectations

For the hackathon, a small manually defined catalog is acceptable. Runtime evidence should then connect discovered dependencies to these capabilities.

## 5. Functional requirements

### 5.1 Dependency discovery

Collect evidence from relevant sources such as:

- OpenTelemetry traces
- Application and proxy logs
- DNS observations
- VPC Flow Logs
- Route 53 Resolver query logs
- CloudTrail
- AWS Config and resource inventory
- Kubernetes or service-mesh data
- eBPF observations
- Source configuration
- Terraform or CloudFormation
- IAM policies
- Security groups, NACLs, and firewall rules
- SBOM and vulnerability findings

The MVP does not need every collector. It needs a clean collector interface and enough evidence to prove one vertical slice.

### 5.2 Unified dependency graph

The graph should be capable of representing:

- Applications
- Business capabilities
- User journeys
- Services
- Processes, containers, hosts, and functions
- Cloud resources
- Databases, queues, and streams
- Internal and external endpoints
- DNS names and IP addresses
- IAM roles and policies
- Network controls
- Identity providers
- Software packages and vulnerability findings
- Monitoring and recovery systems

Important relationship types include:

- `DEPENDS_ON`
- `CALLS`
- `IMPLEMENTS`
- `SUPPORTS_CAPABILITY`
- `USES_IDENTITY`
- `ALLOWED_BY`
- `BLOCKED_BY`
- `RUNS_ON`
- `OBSERVED_BY`
- `HAS_VULNERABILITY`

Every discovered edge should preserve provenance and confidence.

### 5.3 Endpoint and dependency analysis

The user must be able to search for a domain, URL, IP, AWS service, API operation, resource, or package.

Return:

- Whether it is used
- Confidence level
- Evidence
- Calling components
- Related capabilities and journeys
- Frequency and recency
- Environments and regions
- Authentication and network paths when available
- Predicted blast radius
- Supported experiment methods

### 5.4 Passive impact analysis

Before changing a running environment, the platform should traverse the graph and calculate likely upstream and downstream effects.

Results must distinguish:

- Confirmed impact
- Likely impact
- Possible impact
- Unknown due to missing telemetry

This path must remain read-only.

### 5.5 Controlled fault injection

The long-term platform may support:

- DNS NXDOMAIN or timeout
- Connection drop or reset
- Latency and packet loss
- HTTP 401, 403, 429, 500, and 503
- AWS API-specific errors
- Invalid or expired tokens
- TLS failures
- Database or queue unavailability
- Process, container, task, or instance termination
- Availability Zone or Region disruption

The hackathon MVP should implement a small subset through LocalStack, starting with one AWS service and operation.

### 5.6 Impact measurement

Measure application-level behavior, including:

- User-journey success
- Capability availability
- HTTP error rate
- Response latency
- Timeouts
- Retries
- Queue backlog
- Failed or duplicated transactions
- Circuit-breaker state
- Recovery time
- Monitoring availability
- Administrative access when relevant

### 5.7 Safety and governance

Every active experiment must include:

- Explicit target
- Environment
- Scope
- Duration
- Fault type
- Pre-flight checks
- Automatic expiration
- Stop conditions
- Cleanup
- Recovery verification
- Audit record

Production experimentation is outside the hackathon MVP.

### 5.8 Reporting

An experiment report should contain:

- Selected dependency
- Evidence that it is used
- Predicted impact
- Fault and scope
- Baseline measurements
- Observed impact
- Affected and unaffected capabilities
- Propagation path
- Detection and recovery time
- Safety controls triggered
- Prediction differences
- Recommended remediation

## 6. Architecture

### 6.1 Logical components

1. **Application Catalog**
   Stores applications, capabilities, user journeys, owners, and criticality.

2. **Discovery Collectors**
   Gather runtime, cloud, network, configuration, and security evidence.

3. **Normalization Layer**
   Converts source-specific data into stable graph entities and relationships.

4. **Dependency Graph**
   Stores topology, provenance, confidence, and capability mappings.

5. **Endpoint Analyzer**
   Resolves user input and finds matching graph nodes and evidence.

6. **Impact Engine**
   Traverses the graph and predicts blast radius.

7. **Experiment Controller**
   Validates, starts, monitors, expires, and cleans up experiments.

8. **Fault Adapters**
   Integrate LocalStack first, followed later by proxy, Kubernetes, or AWS FIS adapters.

9. **Observability Evaluator**
   Captures baseline, experiment, and recovery measurements.

10. **Report Generator**
    Compares prediction with observation and produces a capability-level result.

### 6.2 Suggested MVP stack

- FastAPI backend
- React and TypeScript frontend
- Docker Compose
- LocalStack
- Neo4j or an in-memory graph for the first slice
- OpenTelemetry
- pytest
- LocalStack Chaos API when available
- A small built-in fault adapter or Toxiproxy fallback if licensing blocks the Chaos API

The LocalStack Chaos API is an Enterprise feature. The implementation should detect availability and fail clearly. Do not make the entire demo depend on an unavailable paid feature without a fallback plan.

## 7. LocalStack role

LocalStack is suitable for early AWS-focused resilience tests.

It can emulate AWS services and, with supported paid features, inject faults by service, Region, operation, probability, HTTP status, and latency.

Useful local tests include:

- DynamoDB `PutItem` returns 503
- DynamoDB calls return throttling errors
- A percentage of calls fail
- AWS API calls experience added latency
- A simulated Region becomes unavailable

LocalStack cannot prove real behavior for:

- AWS control-plane failures
- Full IAM and Organizations enforcement
- Real VPC, NAT, NACL, Transit Gateway, or resolver behavior
- Managed-service failover timing
- Real capacity and quotas
- Third-party providers
- Production traffic
- Actual emergency access paths

The intended progression is:

1. LocalStack
2. Isolated AWS staging
3. Carefully controlled production canary, only after the product matures

## 8. Endpoint disruption design

Endpoint blocking is one experiment type, not the whole product.

For arbitrary endpoints, later adapters may use Envoy, Toxiproxy, a service mesh, DNS proxy, or carefully scoped eBPF/network controls.

Tests must distinguish:

- Blocking an AWS management API hostname
- Blocking application data traffic
- Breaking DNS resolution itself
- Returning an application-level error
- Making the connection hang
- Breaking authentication

For example, blocking `route53.amazonaws.com` affects the Route 53 management API. It does not by itself simulate failure of normal DNS resolution.

## 9. Security scope

The graph can correlate:

- IAM
- Network reachability
- Firewall rules
- Resource exposure
- SBOM inventory
- Known vulnerabilities
- Application capabilities

The platform should not promise detection of unknown zero-days. It can identify known and newly disclosed vulnerabilities after intelligence becomes available and may later integrate runtime anomaly signals.

Discovery permissions and experiment permissions must remain separate.

## 10. Important technical corrections from the original discussion

- Do not assume AWS FIS API error injection supports DynamoDB or SSM. Verify current AWS documentation before adding any action.
- AWS Resilience Hub can discover tagged and deployed resources and newer capabilities can analyze DNS-derived dependencies, but DNS-based discovery has blind spots.
- FIS is an experiment system, not a complete dependency-discovery engine.
- eBPF is one evidence source, not a guarantee that every encrypted or serverless dependency will be mapped.
- No single scanner can guarantee discovery of an unknown zero-day.

## 11. Hackathon MVP definition

The MVP succeeds when a judge can:

1. Open the application.
2. View a small set of business capabilities.
3. Enter or select a DynamoDB endpoint or operation.
4. See evidence that the sample application uses it.
5. See the predicted affected capability path.
6. Start a safe, time-limited local experiment.
7. Observe an actual user journey fail or degrade.
8. See unaffected capabilities remain healthy.
9. See automatic restoration.
10. View a report comparing predicted and observed impact.

## 12. Non-goals for the hackathon

- Production-wide chaos engineering
- Full multi-cloud normalization
- Complete enterprise asset discovery
- Automatic remediation of production systems
- Unknown zero-day detection
- Replacing existing observability or security platforms
- Supporting every AWS service and FIS action
- Building a general-purpose CNAPP

## 13. Reference documentation

- LocalStack Chaos API: https://docs.localstack.cloud/aws/developer-tools/chaos-engineering/chaos-api/
- LocalStack outage tutorial: https://docs.localstack.cloud/aws/tutorials/simulating-outages/
- AWS FIS actions reference: https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html
- AWS Resilience Hub dependency discovery: https://docs.aws.amazon.com/resilience-hub/latest/userguide/next-gen-dependency-discovery.html
- OpenTelemetry: https://opentelemetry.io/docs/
