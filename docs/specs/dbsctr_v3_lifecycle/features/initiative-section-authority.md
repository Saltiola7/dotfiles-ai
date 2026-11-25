# Approve a stable section of a shared document

Discovery contract, INT-126. Owner: lifecycle maintainer. A slice may choose
its own feature document or explicitly approve named sections of a shared
Markdown document. Whole-file authority remains the default. The manifest,
plan and Engineering Profile remain whole-file authorities.

Extend the slice's versioned artifact selection with a repository-relative
Markdown path and a nonempty, unique set of section IDs. A section starts and
ends on dedicated delimiter lines `<!-- dbsctr:begin ID -->` and
`<!-- dbsctr:end ID -->`. IDs use lowercase letters, digits and hyphens, beginning
with a letter. Select the delimiter lines and enclosed bytes from the committed
Git blob, without whitespace, newline or prose normalization. Require a regular
file, unchanged mode, unique pairs, no nesting and no overlap. Reject invalid,
missing, duplicated or ambiguous markers. These reserved complete-line tokens
are delimiters, not Markdown headings or fuzzy text search.

For a same-repository GitHub Initiative, add the optional slice field:

```json
"section_artifacts": {
  "schema_version": 1,
  "documents": [
    {"path": "docs/specs/example/shared.md", "sections": ["delivery"]}
  ]
}
```

Leave that path out of the slice's whole-file `artifacts` list to select only
the named sections. An explicit whole-file selection on the slice or one of
its requirements takes precedence. Receipt `section_authority` records the
selection version and exact document path, mode, source blob and selected
SHA-256 digests; a whole-file override uses the blob without section digests.
Managed Auto and cross-repository selection are not qualified for this source
slice. Exact Discovery imports still use whole blobs; section selection does
not authorize a partial import.

| Event | Decision |
|---|---|
| New receipt and Gate Commit checkpoint | Bind path, mode, section IDs and exact content digests, the source blob/commit for provenance, and the selector version. Verify the same projection at completion. Retain existing whole-blob history and import checks. |
| Accepted protected-base merge changes only unowned text | With a verified target import and the approved projection unchanged, keep the Gate Commit authority and its approval. Do not mint a replacement approval or stamp a new execution. |
| Selected bytes, path, mode, or ownership change, even via the target | Show which selector failed; require the ordinary digest-bound amendment. A matching branch name or a claim that an edit was editorial cannot establish authority. |
| Cycle edits out-of-scope content | Section selection grants no extra write or import scope. Keep existing review, Gate Commit and actual-file change accounting. |

Test changes above, below and within a section; multiple IDs in one file;
marker deletion/duplication, mode and path changes; and historical whole-file
receipts. A requirement selecting the whole file wins over a narrower slice
selector. The slice cannot drop requirements by declaring only what it edited.
Keep [amendment history](initiative-authority-amendment.md) immutable; enrolling
an active legacy cycle into narrower authority itself needs explicit approval.

## Visual Evidence

State, interaction and schema: **required**, the decision table distinguishes
approved projections, historical blobs and checkpoint outcomes. Boundary and
data/trust: **required**, the same table separates approved Discovery from
target and cycle edits. Dependency/deployment: **not applicable**, no topology
change. Quantitative: **not applicable**, no measured claim.

**Text Equivalent:** Exact selected bytes at an approved path/mode can survive
an unrelated accepted upstream edit. An affected or ambiguous selection blocks;
old receipts remain whole-file. The lifecycle maintainer updates this table
with selector grammar, custody or approval changes.
