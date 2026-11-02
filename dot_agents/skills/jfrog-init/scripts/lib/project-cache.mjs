#!/usr/bin/env node
// Project enumeration deliberately has no persistent cache. The former cache
// stored a fast credential-derived fingerprint. Fresh enumeration under the
// current identity avoids retaining a password/token verifier or stale project
// visibility. Keep these exports compatible with existing discovery callers.
// Neither helper inspects arguments, reads legacy files or creates cache state.

export function readCachedProjectList(_serverId, _creds) {
  return null;
}

export function writeCachedProjectList(_serverId, _creds, _body) {
  // Intentionally empty: enumeration results and credentials remain unretained.
}
