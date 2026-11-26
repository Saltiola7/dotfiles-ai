# Leave declared later-slice documents out of the current import

Discovery contract, INT-128. Owner: lifecycle maintainer. A shared
same-repository Discovery commit may contain a cross-context documentation
change owned by a later slice. The current slice can launch without shipping
that change or first merging a docs-only PR.

| Stage | Exact contract |
|---|---|
| Declare | The versioned manifest names a regular documentation path and one later owning slice in the same Initiative and repository. The path must be in that owner's declared artifacts. No wildcard, directory, symlink, deletion, executable, code/configuration or implied owner. |
| Preflight | Derive path, mode and blob from the exact receipt source commit. Classify changes as imported, explicitly deferred, or refused. Display both path lists and bind the owner and exact Git identities in the launch digest. A deferred path is excluded even if it is inside an otherwise auto-carried namespace. |
| Reject overlap | A current requirement, selected document section, profile, plan, manifest or import dependency cannot be deferred. Reject conflicting ownership, drift, unclassified changes or unsafe paths before approval. The existing publication/privacy authority still checks the full committed candidate. |
| Register and follow up | Import only the current exact artifacts; never stage the deferred file or attribute it to this cycle. Preserve its source commit and owner in the approved launch provenance. The later owner obtains its own fresh receipt, comparison-base conflict check and approval. A prior deferral is not import authority. |

Test a cross-context pointer edit mixed with a required spec: first path is
deferred, second is imported, and only the second enters the current import
commit. Change the deferred blob between preview and apply and require fresh
approval. Test undeclared changes, owner missing/unrelated, overlap, a symlink
and a protected-base conflict when the later owner imports it. Old manifest
and receipt versions retain the [existing import rules](initiative-discovery.md).

For an explicit same-repository GitHub Initiative launch, set this optional
field on the current slice:

```json
"deferred_documents": {
  "schema_version": 1,
  "documents": [
    {"path": "docs/specs/later/pointer.md", "owner": "later-slice"}
  ]
}
```

The later slice must depend on the current one, directly or transitively,
and list the Markdown path in its whole-file `artifacts`. Receipt and launch
`deferred_documents` entries include the exact mode and blob. The launch
`artifacts` array lists only imports. The full committed source, including
deferred bytes, is checked against the public-tree identifier policy.
Managed Auto and cross-repository deferral are not qualified.

## Visual Evidence

Boundary, interaction, state, data/trust and schema: **required**, the table
tracks current and later owners, Git identities, the approved launch digest
and the import decision. Dependency/deployment: **not applicable**, no runtime
topology change. Quantitative: **not applicable**, no measured claim.

**Text Equivalent:** Preflight proves and lists each deferred path but grants
the current slice no right to import it. Later receipt and approval establish
the later slice's authority. The lifecycle maintainer updates this table when
manifest, selection or import ownership changes.
