# Normative Specification Visuals

Apply this contract to bounded-context READMEs, Product Intent, feature or
decision specifications, and specification templates. BACKLOG, CHANGELOG,
ROADMAP, and machine plan files are not Normative Specifications.

## Visual Evidence Plan

Every Normative Specification has a `## Visual Evidence` section. Classify each
concern below as `required: TYPE` or `not_applicable: REASON`:

| Concern | Use when | Preferred evidence |
|---|---|---|
| Boundary | Actors, adjacent systems, or ownership boundaries affect decisions | Context/container flowchart |
| Interaction | Ordering, retries, async work, failures, or approval handoffs matter | Sequence diagram |
| State | Legal states, transitions, guards, recovery, or terminal states are contractual | State diagram or transition table |
| Data/trust | Data crosses ownership, privacy, retention, transformation, or security boundaries | Directional data-flow diagram |
| Schema | Persistent entities, cardinality, or optionality affect implementation | ER diagram |
| Dependency/deployment | Runtime topology or non-obvious coupling affects delivery or failure | Deployment or dependency diagram |
| Quantitative | A decision depends on comparison, trend, distribution, or threshold evidence | Chart plus source-data table |

Do not add a decorative visual, chart a single value, copy an import graph, or
duplicate canonical schema/configuration. `not_applicable` is correct when prose
or a table answers the review question more clearly.

## Informative Visual Contract

Each required visual:

- answers one stated review question and names its bounded scope;
- uses text labels and directional relationship intent rather than color alone;
- keeps editable source beside the specification, preferring GitHub-supported
  Mermaid for repository-native diagrams;
- includes Mermaid `accTitle` and `accDescr` where Mermaid is used;
- has an adjacent **Text Equivalent** preserving every decision-relevant fact
  without rendering, color, or spatial position;
- names its canonical source, owner, and change trigger; and
- changes in the same pull request when represented interfaces, states,
  relationships, trust boundaries, topology, or metrics change.

For a quantitative chart, an adjacent table provides values, units, period,
source, denominator, and uncertainty or assumptions. Unverified forecasts stay
explicit assumptions and never appear as measured fact.

## Review And Validation

Review scope, labels, direction, source freshness, Text Equivalent parity, and
non-duplication. Check non-trivial Mermaid in the rendered GitHub pull request
because the repository does not control GitHub's Mermaid version. A syntax or
rendering failure blocks the visual evidence; it is not replaced by a claim that
the source probably renders.
