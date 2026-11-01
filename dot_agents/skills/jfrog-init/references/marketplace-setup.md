# Optional JFrog marketplace integration

Marketplace registration is separate explicit native client/plugin work. It is
not an init readiness requirement and never follows automatically from catalog
access. Preserve the existing skill/plugin source and installation owner.

The retained upstream helper installs a credential-producing headers helper,
writes Claude marketplace/configuration state, fetches registry content and can
change existing credential/netrc records. These are material effects even when
no new token string is saved. Do not run it during portable skill deployment or
as a read-only probe. Never execute/capture `jfrog-marketplace-headers.mjs` as
agent evidence: it intentionally returns live authorization headers.

An authorized integration reviews the selected client/version, exact platform,
helper provenance, credential handling, changed paths, preimages and recovery
before native-owner mutation. Existing marketplace/authentication entries remain
intact unless the specific change is authorized and concretely reviewed.
