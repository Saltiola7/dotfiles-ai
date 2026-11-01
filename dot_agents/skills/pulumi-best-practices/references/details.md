# Detailed Pulumi practices

Locally modified adaptation of the pinned official skill; see
[upstream attribution](../UPSTREAM.md). Read only the sections needed for the task.

These TypeScript/AWS examples illustrate methods, not a selected provider or
resource API version. Match the project's language, CLI/SDK/provider pins, backend,
stack, dependency authority and resource policy before adapting them. Snippets
with omitted definitions are not standalone runnable programs. Code review,
preview, configuration/state writes and deployment are separate operations.

## Practices

### 1. Prefer Resource Declarations Outside `apply()`

**Why**: An `apply` callback may not run during preview when its input is unknown. Resources declared there can therefore be absent from that preview; if the input is already known they can appear. Prefer direct Output-to-Input dependencies so the resource graph is visible without requiring the callback to run. Do not claim Pulumi can never track resources inside `apply`.

**Detection signals**:

- `new aws.` or other resource constructors inside `.apply()` callbacks
- Resource creation inside `pulumi.all([...]).apply()`
- Dynamic resource counts determined at runtime inside apply

**Wrong**:

```typescript
const bucket = new aws.s3.Bucket("bucket");

bucket.id.apply(bucketId => {
    // Risk: absent from preview when bucket.id is unknown
    new aws.s3.BucketObject("object", {
        bucket: bucketId,
        content: "hello",
    });
});
```

**Right**:

```typescript
const bucket = new aws.s3.Bucket("bucket");

// Pass the output directly - Pulumi handles the dependency
const object = new aws.s3.BucketObject("object", {
    bucket: bucket.id,  // Output<string> works here
    content: "hello",
});
```

**When apply is appropriate**:

- Transforming output values for use in tags, names, or computed strings
- Bounded debugging of non-secret values; never print secret plaintext
- Conditional logic that affects resource properties, not resource existence

**Reference**: https://www.pulumi.com/docs/concepts/inputs-outputs/

---

### 2. Pass Outputs Directly as Inputs

**Why**: Pulumi builds a directed acyclic graph (DAG) based on input/output relationships. Passing outputs directly ensures correct creation order. Unwrapping values manually breaks the dependency chain, causing resources to deploy in wrong order or reference values that don't exist yet.

**Detection signals**:

- Variables extracted from `.apply()` used later as resource inputs
- `await` on output values outside of apply
- String concatenation with outputs instead of `pulumi.interpolate`

**Wrong**:

```typescript
const vpc = new aws.ec2.Vpc("vpc", { cidrBlock: "10.0.0.0/16" });

// WRONG: Extracting the value breaks the dependency chain
let vpcId: string;
vpc.id.apply(id => { vpcId = id; });

const subnet = new aws.ec2.Subnet("subnet", {
    vpcId: vpcId,  // May be undefined, no tracked dependency
    cidrBlock: "10.0.1.0/24",
});
```

**Right**:

```typescript
const vpc = new aws.ec2.Vpc("vpc", { cidrBlock: "10.0.0.0/16" });

const subnet = new aws.ec2.Subnet("subnet", {
    vpcId: vpc.id,  // Pass the Output directly
    cidrBlock: "10.0.1.0/24",
});
```

**For string interpolation**:

```typescript
// VALID: apply transforms the value and retains Output propagation.
const withApply = bucket.id.apply(id => `prefix-${id}-suffix`);

// Often simpler for this string-only transformation:
const withInterpolation = pulumi.interpolate`prefix-${bucket.id}-suffix`;

// Another valid form:
const withConcat = pulumi.concat("prefix-", bucket.id, "-suffix");
```

**Reference**: https://www.pulumi.com/docs/concepts/inputs-outputs/

---

### 3. Use Components for Related Resources

**Why**: ComponentResource classes can group related resources into useful logical units. Use an abstraction when it improves ownership, reuse or the interface; a small program with clear inline resources does not automatically need a new component.

**Detection signals**:

- Repeated related resource patterns with a useful shared ownership/interface
- Repeated resource patterns across stacks that should be abstracted
- Hard to understand resource relationships from the Pulumi console

**Wrong**:

```typescript
// Flat structure - no logical grouping, hard to reuse
const bucket = new aws.s3.Bucket("app-bucket");
const bucketPolicy = new aws.s3.BucketPolicy("app-bucket-policy", {
    bucket: bucket.id,
    policy: policyDoc,
});
const originAccessIdentity = new aws.cloudfront.OriginAccessIdentity("app-oai");
const distribution = new aws.cloudfront.Distribution("app-cdn", { /* ... */ });
```

**Right**:

```typescript
interface StaticSiteArgs {
    domain: pulumi.Input<string>;
    content: pulumi.Input<pulumi.asset.Archive>;
}

class StaticSite extends pulumi.ComponentResource {
    public readonly url: pulumi.Output<string>;

    constructor(name: string, args: StaticSiteArgs, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:components:StaticSite", name, args, opts);

        // Resources created here - see practice 4 for parent setup
        const bucket = new aws.s3.Bucket(`${name}-bucket`, {}, { parent: this });
        // ...

        this.url = distribution.domainName;
        this.registerOutputs({ url: this.url });
    }
}

// Reusable across stacks
const site = new StaticSite("marketing", {
    domain: "marketing.example.com",
    content: new pulumi.asset.FileArchive("./dist"),
});
```

**Component best practices**:

- Use a consistent resource type token pattern: `organization:module:ComponentName`
- Call `registerOutputs()` at the end of the constructor
- Expose outputs as class properties for consumers
- Accept `ComponentResourceOptions` to allow callers to set providers, aliases, etc.

For in-depth component authoring guidance (args design, multi-language support, testing, distribution), use skill `pulumi-component`.

**Reference**: https://www.pulumi.com/docs/concepts/resources/components/

---

### 4. Always Set `parent: this` in Components

**Why**: When you create resources inside a ComponentResource without setting `parent: this`, those resources appear at the root level of your stack's state. This breaks the logical hierarchy, makes the Pulumi console hard to navigate, and can cause issues with aliases and refactoring. The parent relationship is what makes the component actually group its children.

**Detection signals**:

- ComponentResource classes that don't pass `{ parent: this }` to child resources
- Resources inside a component appearing at root level in the console
- Unexpected behavior when adding aliases to components

**Wrong**:

```typescript
class MyComponent extends pulumi.ComponentResource {
    constructor(name: string, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:components:MyComponent", name, {}, opts);

        // WRONG: No parent set - this bucket appears at root level
        const bucket = new aws.s3.Bucket(`${name}-bucket`);
    }
}
```

**Right**:

```typescript
class MyComponent extends pulumi.ComponentResource {
    constructor(name: string, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:components:MyComponent", name, {}, opts);

        // RIGHT: Parent establishes hierarchy
        const bucket = new aws.s3.Bucket(`${name}-bucket`, {}, {
            parent: this
        });

        const policy = new aws.s3.BucketPolicy(`${name}-policy`, {
            bucket: bucket.id,
            policy: policyDoc,
        }, {
            parent: this
        });
    }
}
```

**What parent: this provides**:

- Resources appear nested under the component in Pulumi console
- Component removal can schedule owned children for deletion; protection, retention, dependencies and provider behavior still apply
- Aliases on the component automatically apply to children
- Clear ownership in state files

**Reference**: https://www.pulumi.com/docs/concepts/resources/components/

---

### 5. Preserve Secret Boundaries

**Why**: Use the selected secrets provider and secret-marked configuration so
sensitive values are encrypted in state and secret marking propagates through
Outputs. Plaintext can still exist in the program/provider process and be exposed
by application logs, subprocesses or external systems. CLI masking is not a license
to print values. If exposure is confirmed, follow the project's rotation and
history-handling policy rather than assuming changing one config flag removes it.

**Detection signals**:

- Plaintext passwords, API keys or private keys in config/source
- Connection strings crossing an unapproved log or output boundary
- Secret marking removed or a secret decrypted for debugging

For an authorized config write, use the existing secret injection path or an
available protected prompt; do not place a real secret in command arguments or
shell history. The following prompts only when supported by the selected CLI:

```bash
pulumi config set --secret databasePassword
```

**In code**:

```typescript
const config = new pulumi.Config();

// Retrieves a secret-marked Output; plaintext can exist during execution
const dbPassword = config.requireSecret("databasePassword");

// Creating outputs from secrets preserves secrecy
const connectionString = pulumi.interpolate`postgres://user:${dbPassword}@host/db`;
// connectionString is also a secret Output

// Explicitly mark values as secret
const computed = pulumi.secret(someValue);
```

**If the project already selects Pulumi ESC**: preserve its environment bindings
and existing access. Adding an ESC environment, changing its secrets or switching
secrets providers is a separate task; this guidance does not select ESC or create
accounts/credentials. Otherwise retain the project's current secret authority.

**What qualifies as a secret**:

- Passwords and passphrases
- API keys and tokens
- Private keys and certificates
- Connection strings with credentials
- OAuth client secrets
- Encryption keys

**References**:

- https://www.pulumi.com/docs/concepts/secrets/
- https://www.pulumi.com/docs/esc/

---

### 6. Use Aliases When Refactoring

**Why**: Renaming resources, moving them into components, or changing parents causes Pulumi to see them as new resources. Without suitable identity mapping a refactor can plan a delete/create. An alias can map a prior identity to the new declaration; it does not prevent replacement required by changed provider properties. Verify the actual plan and data protection.

**Detection signals**:

- Resource rename without alias
- Moving resource into or out of a ComponentResource
- Changing the parent of a resource
- Preview shows delete+create when update was intended

**Wrong**:

```typescript
// Before: resource named "my-bucket"
const bucket = new aws.s3.Bucket("my-bucket");

// Renaming without an identity mapping can plan replacement
const bucket = new aws.s3.Bucket("application-bucket");
```

**Right**:

```typescript
// Map the prior identity; verify the selected preview for replacement
const bucket = new aws.s3.Bucket("application-bucket", {}, {
    aliases: [{ name: "my-bucket" }],
});
```

**Moving into a component**:

```typescript
// Before: top-level resource
const bucket = new aws.s3.Bucket("my-bucket");

// After: inside a component - needs alias with old parent
class MyComponent extends pulumi.ComponentResource {
    constructor(name: string, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:components:MyComponent", name, {}, opts);

        const bucket = new aws.s3.Bucket("bucket", {}, {
            parent: this,
            aliases: [{
                name: "my-bucket",
                parent: pulumi.rootStackResource,  // Was at root
            }],
        });
    }
}
```

**Alias types**:

```typescript
// Simple name change
aliases: [{ name: "old-name" }]

// Parent change
aliases: [{ name: "resource-name", parent: oldParent }]

// Full URN (when you know the exact previous URN)
aliases: ["urn:pulumi:stack::project::aws:s3/bucket:Bucket::old-name"]
```

**Lifecycle**:

1. Add the appropriate prior identity during the refactor.
2. Review a preview for the selected stack and input revision under the existing workflow.
3. Apply only within existing explicit deployment authority; record which supported stacks migrated.
4. Retain aliases while old stack states or consumers still need them; remove only under the compatibility policy.

**Reference**: https://www.pulumi.com/docs/iac/concepts/resources/options/aliases/

---

### 7. Review the Selected Preview Before Deployment

A preview reports proposed resource changes for the selected program, config,
state, provider versions and environment. Unknowns, resource callbacks and later
external drift can limit it. It executes program code and provider reads; arbitrary
programs can have their own side effects. Inspect the project before executing it.

Where authorized and supported by the selected CLI, a targeted example is:

```bash
pulumi preview --stack "$stack"
```

`stack` must already identify the intended backend/project/stack; it is not a new
default. Preview is distinct from `pulumi up`, state refresh/import, configuration
writes and deployment health. Do not run them merely because this example exists.

Review creates, updates, deletes and replacements, particularly unexpected
identity changes, immutable-property changes, persistent data and dependent
resources. Preserve missing/unknown values and actual command failures.

For CI work, retain the existing runner, credentials, action pins, stack selection,
permissions and acceptance gates. Match preview evidence to the source/config
revision being deployed and protect any published diagnostic artifact. A PR
comment, new workflow, deployment-on-main or universal manual approval is not
required by this skill; use the project's delivery contract. Do not copy moving
example action tags or introduce an automatic deploy job.

**References**:

- https://www.pulumi.com/docs/iac/cli/commands/pulumi_preview/
- https://www.pulumi.com/docs/iac/packages-and-automation/continuous-delivery/github-actions/

---

## Quick Reference

| Practice | Key Signal | Fix |
|----------|-----------|-----|
| Resource declarations in apply | Unknown callback inputs can hide preview resources | Prefer outside declarations and direct Inputs |
| Pass outputs directly | Extracted values used as inputs | Use Output objects, `pulumi.interpolate` |
| Useful components | Repeated ownership or interface concern | Introduce an abstraction only when justified |
| Set parent: this | Component children at root level | Pass `{ parent: this }` to all child resources |
| Secrets from day one | Plaintext passwords/keys in config | Preserve selected secret authority and marking |
| Aliases when refactoring | Delete+create in preview | Add alias with old name/parent |
| Preview before deploy | Unreviewed resource changes | Use selected workflow and target-bound preview evidence |

## Validation Checklist

When reviewing Pulumi code, verify:

- [ ] Resource declarations remain previewable where possible; unknown callback limits are visible
- [ ] Outputs passed directly to dependent resources
- [ ] Components serve a useful ownership/reuse/interface boundary
- [ ] Child resources have `{ parent: this }`
- [ ] Sensitive values use `config.requireSecret()` or `--secret`
- [ ] Refactored resources have aliases preserving identity
- [ ] Deployment process includes preview step

## Related Guidance

The managed `pulumi-component` skill can help with a substantive component API or
packaging task. Other upstream routers, Automation API and ESC skills are optional
external material, not required or assumed installed dependencies. Keep the current
primary; do not fetch/install another bundle merely to read this guidance.

## Primary references

- https://www.pulumi.com/docs/iac/concepts/inputs-outputs/apply/
- https://www.pulumi.com/docs/iac/concepts/components/
- https://www.pulumi.com/docs/iac/concepts/secrets/
- https://www.pulumi.com/docs/iac/concepts/resources/options/aliases/
