# Detailed Pulumi component guidance

Locally modified adaptation of the pinned official skill; see
[upstream attribution](../UPSTREAM.md). Read the sections needed for the task.

The TypeScript/Python/AWS examples are illustrative. Preserve the project's
language, CLI/SDK/provider pins, backend, stack, dependency manager and existing
resource contracts. Omitted types/resources are not a standalone application.
Choose inline resources, local components or a distributed package according to
actual consumers. Loading this document does not select packaging or authorize
installation, code generation, publication, CI/account changes or deployment.

## Component Anatomy

A conventional locally authored component has these registration responsibilities:

1. **Extend ComponentResource** and call `super()` with a resource type token
2. **Accept standard parameters**: name, args, and `ComponentResourceOptions`
3. **Set `parent: this`** on all child resources
4. **Register outputs** once child/output registration is complete (normally at constructor completion)

### TypeScript

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

interface StaticSiteArgs {
    indexDocument?: pulumi.Input<string>;
    errorDocument?: pulumi.Input<string>;
}

class StaticSite extends pulumi.ComponentResource {
    public readonly bucketName: pulumi.Output<string>;
    public readonly websiteUrl: pulumi.Output<string>;

    constructor(name: string, args: StaticSiteArgs, opts?: pulumi.ComponentResourceOptions) {
        // 1. Call super with resource type token: <package>:<module>:<type>
        super("myorg:index:StaticSite", name, {}, opts);

        // 2. Create child resources with parent: this
        const bucket = new aws.s3.Bucket(`${name}-bucket`, {}, { parent: this });

        const website = new aws.s3.BucketWebsiteConfigurationV2(`${name}-website`, {
            bucket: bucket.id,
            indexDocument: { suffix: args.indexDocument ?? "index.html" },
            errorDocument: { key: args.errorDocument ?? "error.html" },
        }, { parent: this });

        // 3. Expose outputs as class properties
        this.bucketName = bucket.id;
        this.websiteUrl = website.websiteEndpoint;

        // 4. Register outputs when component registration is complete
        this.registerOutputs({
            bucketName: this.bucketName,
            websiteUrl: this.websiteUrl,
        });
    }
}

// Usage
const site = new StaticSite("marketing", {
    indexDocument: "index.html",
});
export const url = site.websiteUrl;
```

### Python

```python
from typing import Optional

import pulumi
import pulumi_aws as aws

class StaticSiteArgs:
    def __init__(self,
                 index_document: pulumi.Input[str] = "index.html",
                 error_document: pulumi.Input[str] = "error.html"):
        self.index_document = index_document
        self.error_document = error_document

class StaticSite(pulumi.ComponentResource):
    bucket_name: pulumi.Output[str]
    website_url: pulumi.Output[str]

    def __init__(self, name: str, args: StaticSiteArgs,
                 opts: Optional[pulumi.ResourceOptions] = None):
        super().__init__("myorg:index:StaticSite", name, None, opts)

        bucket = aws.s3.Bucket(f"{name}-bucket",
            opts=pulumi.ResourceOptions(parent=self))

        website = aws.s3.BucketWebsiteConfigurationV2(f"{name}-website",
            bucket=bucket.id,
            index_document=aws.s3.BucketWebsiteConfigurationV2IndexDocumentArgs(
                suffix=args.index_document,
            ),
            error_document=aws.s3.BucketWebsiteConfigurationV2ErrorDocumentArgs(
                key=args.error_document,
            ),
            opts=pulumi.ResourceOptions(parent=self))

        self.bucket_name = bucket.id
        self.website_url = website.website_endpoint

        self.register_outputs({
            "bucket_name": self.bucket_name,
            "website_url": self.website_url,
        })

site = StaticSite("marketing", StaticSiteArgs())
pulumi.export("url", site.website_url)
```

### Type Token Format

The first argument to `super()` is the resource type token: `<package>:<module>:<type>`. It is not a full resource URN, which also identifies stack, project, qualified type/parent and logical name. Changing identity-bearing fields requires compatibility/alias review.

| Segment | Convention | Example |
|---------|-----------|---------|
| package | Organization or package name | `myorg`, `acme`, `pkg` |
| module  | Usually `index` | `index` |
| type    | PascalCase class name | `StaticSite`, `VpcNetwork` |

Full examples: `myorg:index:StaticSite`, `acme:index:KubernetesCluster`

### Complete Component Output Registration

**Why**: `registerOutputs()` / `register_outputs()` signals completion of component output registration and records the declared outputs. Omitting it can leave incomplete status/output information. Call it when registration is complete; async construction and remote component protocols must follow the selected SDK rather than an unconditional last-line rule.

**Wrong**:

```typescript
class MyComponent extends pulumi.ComponentResource {
    public readonly url: pulumi.Output<string>;

    constructor(name: string, args: MyArgs, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:index:MyComponent", name, {}, opts);
        const bucket = new aws.s3.Bucket(`${name}-bucket`, {}, { parent: this });
        this.url = bucket.bucketRegionalDomainName;
        // Missing registerOutputs leaves registration/output information incomplete
    }
}
```

**Right**:

```typescript
class MyComponent extends pulumi.ComponentResource {
    public readonly url: pulumi.Output<string>;

    constructor(name: string, args: MyArgs, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:index:MyComponent", name, {}, opts);
        const bucket = new aws.s3.Bucket(`${name}-bucket`, {}, { parent: this });
        this.url = bucket.bucketRegionalDomainName;

        this.registerOutputs({ url: this.url });
    }
}
```

### Derive Child Names from the Component Name

**Why**: A Pulumi URN includes the parent type chain, not parent instance names. Two instances of the same component type that create the same child type and logical name can therefore collide. Derive stable child logical names from the component name. Explicit physical names need their own uniqueness contract. Renaming existing children needs alias/preview review. See the [resource naming contract](https://www.pulumi.com/docs/iac/concepts/resources/names/).

**Wrong**:

```typescript
// Collides when same-type component instances create this fixed child name
const bucket = new aws.s3.Bucket("my-bucket", {}, { parent: this });
```

**Right**:

```typescript
// Derived, descriptive logical name; retain physical-name policy
const bucket = new aws.s3.Bucket(`${name}-bucket`, {}, { parent: this });
```

---

## Designing the Args Interface

The args interface is the most impactful design decision. It defines what consumers can configure and how composable the component is.

### Wrap Properties in Input<T>

**Why**: `Input<T>` accepts plain values and `Output<T>` from other resources. A property that depends on an Output should accept an Input rather than force imperative extraction. A synchronous topology switch can deliberately accept a plain known value; an unresolved Output cannot be used as a normal boolean.

**Wrong**:

```typescript
interface WebServiceArgs {
    port: number;            // Forces consumers to unwrap Outputs
    vpcId: string;           // Cannot accept vpc.id directly
}
```

**Right**:

```typescript
interface WebServiceArgs {
    port: pulumi.Input<number>;     // Accepts 8080 or someOutput
    vpcId: pulumi.Input<string>;    // Accepts "vpc-123" or vpc.id
}
```

### Keep Structures Flat

Avoid deeply nested arg objects. Flat interfaces are easier to use and evolve.

```typescript
// Prefer flat
interface DatabaseArgs {
    instanceClass: pulumi.Input<string>;
    storageGb: pulumi.Input<number>;
    enableBackups?: pulumi.Input<boolean>;
    backupRetentionDays?: pulumi.Input<number>;
}

// Avoid deep nesting
interface DatabaseArgs {
    instance: {
        compute: { class: pulumi.Input<string> };
        storage: { sizeGb: pulumi.Input<number> };
    };
    backup: {
        config: { enabled: pulumi.Input<boolean>; retention: pulumi.Input<number> };
    };
}
```

### Qualify Cross-Language Types

For a selected cross-language package, check the actual schema generator and consumer SDKs. Not every authoring-language union maps to a usable schema/SDK interface. This is not a claim that Python cannot express unions or a blanket ban in a local TypeScript component.

**Wrong**:

```typescript
interface MyArgs {
    port: pulumi.Input<string | number>;  // Check selected schema/SDK support
}
```

**Right**:

```typescript
interface MyArgs {
    port: pulumi.Input<number>;  // One clear numeric contract
}
```

If you need to accept multiple forms, use separate optional properties:

```typescript
interface StorageArgs {
    sizeGb?: pulumi.Input<number>;      // Specify size in GB
    sizeMb?: pulumi.Input<number>;      // Or specify size in MB; validate exclusive use
}
```

### No Functions or Callbacks

Ordinary callbacks are not serializable cross-language package inputs. A local same-language interface may choose callbacks deliberately; do not carry them into a generated schema without supported semantics.

**Wrong**:

```typescript
interface MyArgs {
    nameTransform: (name: string) => string;  // Cannot serialize
}
```

**Right**:

```typescript
interface MyArgs {
    namePrefix?: pulumi.Input<string>;   // Configuration instead of callback
    nameSuffix?: pulumi.Input<string>;
}
```

### Use Defaults for Optional Properties

Set sensible defaults inside the constructor so consumers only configure what they need:

```typescript
interface SecureBucketArgs {
    enableVersioning?: boolean;   // Defaults to true
    enableEncryption?: boolean;   // Defaults to true
    blockPublicAccess?: boolean;  // Defaults to true
}

class SecureBucket extends pulumi.ComponentResource {
    constructor(name: string, args: SecureBucketArgs, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:index:SecureBucket", name, {}, opts);

        const enableVersioning = args.enableVersioning ?? true;
        const enableEncryption = args.enableEncryption ?? true;
        const blockPublicAccess = args.blockPublicAccess ?? true;

        // Apply defaults...
    }
}

// Consumer only overrides what they need
const bucket = new SecureBucket("data", { enableVersioning: false });
```

---

## Exposing Outputs

### Expose Only What Consumers Need

Components often create many internal resources. Expose only the values consumers need, not every internal resource.

**Wrong**:

```typescript
class Database extends pulumi.ComponentResource {
    // Exposes everything -- consumers see implementation details
    public readonly cluster: aws.rds.Cluster;
    public readonly primaryInstance: aws.rds.ClusterInstance;
    public readonly replicaInstance: aws.rds.ClusterInstance;
    public readonly subnetGroup: aws.rds.SubnetGroup;
    public readonly securityGroup: aws.ec2.SecurityGroup;
    public readonly parameterGroup: aws.rds.ClusterParameterGroup;
    // ...
}
```

**Right**:

```typescript
class Database extends pulumi.ComponentResource {
    // Exposes only what consumers need
    public readonly endpoint: pulumi.Output<string>;
    public readonly port: pulumi.Output<number>;
    public readonly securityGroupId: pulumi.Output<string>;

    constructor(name: string, args: DatabaseArgs, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:index:Database", name, {}, opts);

        const sg = new aws.ec2.SecurityGroup(`${name}-sg`, { /* ... */ }, { parent: this });
        const cluster = new aws.rds.Cluster(`${name}-cluster`, { /* ... */ }, { parent: this });

        this.endpoint = cluster.endpoint;
        this.port = cluster.port;
        this.securityGroupId = sg.id;

        this.registerOutputs({
            endpoint: this.endpoint,
            port: this.port,
            securityGroupId: this.securityGroupId,
        });
    }
}
```

### Derive Composite Outputs

Use `pulumi.interpolate` or `pulumi.concat` to build derived values (`apply` is also valid for a transformation). Ensure a password is secret-marked before constructing a connection string; an `Input<string>` annotation alone does not make it secret:

```typescript
const password = pulumi.secret(args.password);
this.connectionString = pulumi.interpolate`postgresql://${args.username}:${password}@${cluster.endpoint}:${cluster.port}/${args.databaseName}`;

this.registerOutputs({ connectionString: this.connectionString });
```

---

## Component Design Patterns

### Sensible Defaults with Override

Encode best practices as defaults. Allow consumers to override when they have specific requirements.

```typescript
interface SecureBucketArgs {
    enableVersioning?: boolean;
    enableEncryption?: boolean;
    blockPublicAccess?: boolean;
    tags?: pulumi.Input<Record<string, pulumi.Input<string>>>;
}

class SecureBucket extends pulumi.ComponentResource {
    public readonly bucketId: pulumi.Output<string>;
    public readonly arn: pulumi.Output<string>;

    constructor(name: string, args: SecureBucketArgs = {}, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:index:SecureBucket", name, {}, opts);

        const bucket = new aws.s3.Bucket(`${name}-bucket`, {
            tags: args.tags,
        }, { parent: this });

        // Versioning on by default
        if (args.enableVersioning !== false) {
            new aws.s3.BucketVersioningV2(`${name}-versioning`, {
                bucket: bucket.id,
                versioningConfiguration: { status: "Enabled" },
            }, { parent: this });
        }

        // Encryption on by default
        if (args.enableEncryption !== false) {
            new aws.s3.BucketServerSideEncryptionConfigurationV2(`${name}-encryption`, {
                bucket: bucket.id,
                rules: [{ applyServerSideEncryptionByDefault: { sseAlgorithm: "AES256" } }],
            }, { parent: this });
        }

        // Public access blocked by default
        if (args.blockPublicAccess !== false) {
            new aws.s3.BucketPublicAccessBlock(`${name}-public-access`, {
                bucket: bucket.id,
                blockPublicAcls: true,
                blockPublicPolicy: true,
                ignorePublicAcls: true,
                restrictPublicBuckets: true,
            }, { parent: this });
        }

        this.bucketId = bucket.id;
        this.arn = bucket.arn;
        this.registerOutputs({ bucketId: this.bucketId, arn: this.arn });
    }
}
```

### Conditional Resource Creation

Use known plain configuration for resource-existence choices in a synchronous constructor. The switches and optional email below intentionally use `boolean`/`string`, not `Input`: a Promise/Output is truthy regardless of its eventual value. If topology really depends on an unknown Output, redesign toward stable resources/direct Inputs where possible and document any apply-time preview limits. Do not silently treat an Output object as its result.

```typescript
interface WebServiceArgs {
    image: pulumi.Input<string>;
    port: pulumi.Input<number>;
    enableMonitoring?: boolean;
    alarmEmail?: string;
}

class WebService extends pulumi.ComponentResource {
    constructor(name: string, args: WebServiceArgs, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:index:WebService", name, {}, opts);

        const service = new aws.ecs.Service(`${name}-service`, {
            // ...service config...
        }, { parent: this });

        // Only create alarm infrastructure when monitoring is enabled
        if (args.enableMonitoring) {
            const topic = new aws.sns.Topic(`${name}-alerts`, {}, { parent: this });

            if (args.alarmEmail) {
                new aws.sns.TopicSubscription(`${name}-alert-email`, {
                    topic: topic.arn,
                    protocol: "email",
                    endpoint: args.alarmEmail,
                }, { parent: this });
            }

            new aws.cloudwatch.MetricAlarm(`${name}-cpu-alarm`, {
                // ...alarm config referencing service...
                alarmActions: [topic.arn],
            }, { parent: this });
        }

        this.registerOutputs({});
    }
}
```

### Composition

Build higher-level components from lower-level ones. Each level manages a single concern.

```typescript
// Lower-level component
class VpcNetwork extends pulumi.ComponentResource {
    public readonly vpcId: pulumi.Output<string>;
    public readonly publicSubnetIds: pulumi.Output<string>[];
    public readonly privateSubnetIds: pulumi.Output<string>[];

    constructor(name: string, args: VpcNetworkArgs, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:index:VpcNetwork", name, {}, opts);
        // ...create VPC, subnets, route tables...
        this.registerOutputs({ vpcId: this.vpcId });
    }
}

// Higher-level component that uses VpcNetwork
class Platform extends pulumi.ComponentResource {
    public readonly clusterEndpoint: pulumi.Output<string>;

    constructor(name: string, args: PlatformArgs, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:index:Platform", name, {}, opts);

        // Compose lower-level components
        const network = new VpcNetwork(`${name}-network`, {
            cidrBlock: args.cidrBlock,
        }, { parent: this });

        const cluster = new aws.eks.Cluster(`${name}-cluster`, {
            roleArn: args.clusterRoleArn,
            vpcConfig: {
                subnetIds: network.privateSubnetIds,
            },
        }, { parent: this });

        this.clusterEndpoint = cluster.endpoint;
        this.registerOutputs({ clusterEndpoint: this.clusterEndpoint });
    }
}
```

### Provider Passthrough

Accept project-selected explicit providers for multi-region/account deployments. A component provider map can be inherited by matching child provider packages through their parent; preserve deliberate child overrides and verify which account/region each child actually uses:

```typescript
// Consumer passes a provider for a different region
const usWest = new aws.Provider("us-west", { region: "us-west-2" });
const site = new StaticSite("west-site", { indexDocument: "index.html" }, {
    providers: [usWest],
});
```

A matching child with `{ parent: this }` can inherit that provider unless its options override selection. Provider-package compatibility, SDK behavior and resource invokes need their own check; parenting alone does not prove every operation uses the intended provider. Do not create a new account or switch region from this example.

---

## Multi-Language Components

If your component will be consumed from multiple Pulumi languages (TypeScript, Python, Go, C#, Java, YAML), package it as a multi-language component.

### Do You Need Multi-Language?

Ask: "Will anyone consume this component from a different language than it was authored in?"

**Single-language component** (no packaging needed):

- Your team uses one language and the component stays within that codebase
- The component is internal to a single project or monorepo
- No `PulumiPlugin.yaml` needed -- just import the class directly

**Multi-language component** (packaging required):

- Other teams consume your component in different languages
- Platform teams building abstractions for developers who choose their own language
- YAML consumers need access -- even if you author in TypeScript, YAML programs require multi-language packaging to use your component
- Building a shared component library for your organization
- Publishing to the Pulumi private registry or public registry is a common reason, but not required for multi-language support

**Common mistake**: A TypeScript platform team builds components only their TypeScript users can consume. If application developers use Python or YAML, those components are invisible to them without multi-language packaging.

### Setup

Only for a selected compatible source-based component package, create a `PulumiPlugin.yaml` in the component directory to declare the runtime:

```yaml
runtime: nodejs
```

Or for Python:

```yaml
runtime: python
```

### Serialization Constraints

For multi-language compatibility, args must be serializable. Check these illustrative constraints against the selected package/schema tooling; they are not universal restrictions on local components:

| Allowed | Not Allowed |
|---------|-------------|
| `string`, `number`, `boolean` | Unions unsupported by the chosen generator/consumer contract |
| `Input<T>` wrappers | Functions and callbacks |
| Arrays and maps of primitives | Complex nested generics |
| Enums | Platform-specific types |

### Consuming Multi-Language Components

For a compatible selected source-package workflow, consumers can use `pulumi package add`, which can download a provider plugin, generate a local SDK and update `Pulumi.yaml`. Confirm selected CLI behavior and authorized dependency setup first:

```bash
# From an explicitly selected immutable package reference
pulumi package add "$pinned_component_ref"

# Or from a selected repository and selected immutable version
pulumi package add "${component_repository}@${component_version}"
```

If an authorized dependency setup task selects a CLI version supporting this workflow, `pulumi install` can provision package dependencies. It can download/execute dependencies and is not a routine read-only validation command. Preserve the existing lock/install authority; do not run it simply because this reference was loaded.

Authors who publish SDKs to package managers (npm, PyPI, etc.) can optionally use `pulumi package gen-sdk` to generate language-specific SDKs for publishing. Most component authors do not need this -- `pulumi package add` handles SDK generation on the consumer side.

### Entry Points

The following upstream source-based/executable-package examples depend on the selected CLI, SDK and package model. Verify support before adopting them; experimental APIs can differ. They do not require changing an existing project to this model. Entry points host a component provider process and differ by language.

**TypeScript** (`runtime: nodejs`):

Export component classes from `index.ts`. No separate entry point file is needed. Pulumi introspects exported classes automatically.

```typescript
// index.ts -- exports are the entry point
export { StaticSite, StaticSiteArgs } from "./staticSite";
export { SecureBucket, SecureBucketArgs } from "./secureBucket";
```

**Python** (`runtime: python`):

Create a `__main__.py` that calls `component_provider_host` with all component classes:

```python
from pulumi.provider.experimental import component_provider_host
from static_site import StaticSite
from secure_bucket import SecureBucket

if __name__ == "__main__":
    component_provider_host(
        name="my-components",
        components=[StaticSite, SecureBucket],
    )
```

**Go** (`runtime: go`):

Create a `main.go` that builds and runs the provider:

```go
package main

import (
    "context"
    "fmt"
    "os"

    "github.com/pulumi/pulumi-go-provider/infer"
)

func main() {
    p, err := infer.NewProviderBuilder().
        WithComponents(
            infer.ComponentF(NewStaticSite),
            infer.ComponentF(NewSecureBucket),
        ).
        Build()
    if err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
    if err := p.Run(context.Background(), "my-components", "0.1.0"); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}
```

**C#** (`runtime: dotnet`):

Create a `Program.cs` that serves the component provider host:

```csharp
using System.Threading.Tasks;

class Program
{
    public static Task Main(string[] args) =>
        Pulumi.Experimental.Provider.ComponentProviderHost.Serve(args);
}
```

For package authoring details, use the official selected-version documentation below; a third-party example is not a required installed dependency.

**Reference**: https://www.pulumi.com/docs/iac/using-pulumi/pulumi-packages/

---

## Distribution

Only when distribution is in the task, choose a method from the actual audience and compatibility contract. The commands below are separate network/publication operations, not an execution checklist. Use project-selected registries, identity, immutable versions and existing release gates. Tag/push/publish authority does not arise from loading a skill.

| Audience | Method | How |
|----------|--------|-----|
| Same project | Direct import | Standard language import |
| Same organization | Private registry | `pulumi package publish` to Pulumi Cloud |
| Same organization | Git repository | `pulumi package add <repo>` with version tags |
| Language ecosystem | Package manager | Publish to npm, PyPI, NuGet, or Maven |
| Public community | Pulumi Registry | Submit via pulumi/registry GitHub repo |

### Pulumi Private Registry

The private registry is the centralized catalog for your organization's components. It provides automatic API documentation, version management, and discoverability for all teams.

Publish a component to the private registry:

```bash
pulumi package publish https://github.com/myorg/my-component --publisher myorg
```

Version components using git tags with a `v` prefix:

```bash
git tag v1.0.0
git push origin v1.0.0
```

A README file is required when publishing. Pulumi uses it as the component's documentation page in the registry.

For a selected CI publication workflow, preserve the existing action pins, runner,
permissions and registry identity. OIDC is one supported authentication option when
already configured; adding a federation trust or obtaining a token is a separate
boundary. Verify current official publication syntax and selected CLI support.
Do not add automatic tag-triggered publishing or a new token/account by default.

The private registry automatically generates SDK documentation for each published component. Enrich the generated docs by adding type annotations to your component's inputs and outputs (JSDoc in TypeScript, docstrings in Python, `Annotate()` methods in Go).

**Reference**: https://www.pulumi.com/docs/idp/get-started/private-registry/

### Git Repository Distribution

Tag releases for consumers to pin versions:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Consumers install with:

```bash
pulumi package add https://github.com/myorg/my-component@v1.0.0
```

### Package Manager Distribution

Publish language-specific packages for native dependency management:

- **npm**: `npm publish` for TypeScript/JavaScript
- **PyPI**: `twine upload` for Python
- **NuGet**: `dotnet nuget push` for .NET
- **Maven Central**: Standard Maven publishing for Java

**Reference**: https://www.pulumi.com/docs/iac/using-pulumi/pulumi-packages/

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Resources inside `apply()` | May be absent from preview when input is unknown | Prefer outside declarations and direct Inputs |
| Incomplete output registration | Missing output/completion information | Register outputs at completion using selected SDK |
| Missing `parent: this` | Children appear at root level | Pass `{ parent: this }` to all child resources |
| Unsupported cross-language input | Generated schema/SDK mismatch | Check selected tooling; choose a representable contract |
| Functions in args | Cannot serialize across languages | Use configuration properties instead |
| Inconsistent child naming | Confusing identity or physical-name conflicts | Derive useful logical names and preserve physical-name/alias policy |
| Over-exposed outputs | Leaks implementation details | Export only what consumers need |
| Single-use component | Unnecessary abstraction overhead | Use inline resources until a pattern repeats |
| Deeply nested args | Hard to use and evolve | Keep interfaces flat with optional properties |

---

## Quick Reference

| Topic | Key Point |
|-------|-----------|
| Type Token | `<package>:<module>:<type>`, module usually `index` |
| Constructor | Base registration, intended children and completed output registration |
| Child resources | Always `{ parent: this }`, derive name from `${name}-suffix` |
| Args interface | Input for value dependencies; known config for topology; selected schema for cross-language types |
| Outputs | Public readonly `Output<T>` properties, expose only essentials |
| Defaults | Use `??` operator to apply sensible defaults in constructor |
| Composition | Lower-level components composed into higher-level ones |
| Multi-language | `PulumiPlugin.yaml` + entry point; consumers use `pulumi package add` |
| Distribution | Private registry, git tags, package managers, or public Pulumi Registry |

## Related Skills

- **pulumi-best-practices**: General Pulumi patterns including Output handling, secrets, and aliases
Automation API and ESC are optional upstream subjects, not assumed installed skills
or required dependencies. Keep the existing coordinator, secret authority and task
scope; do not fetch/install another skill as a prerequisite.

## References

- https://www.pulumi.com/docs/iac/concepts/resources/components/
- https://www.pulumi.com/docs/iac/using-pulumi/pulumi-packages/
- https://www.pulumi.com/docs/idp/get-started/private-registry/
- https://www.pulumi.com/docs/iac/concepts/inputs-outputs/
- https://www.pulumi.com/docs/iac/concepts/resources/options/aliases/
