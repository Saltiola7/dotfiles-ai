# Git identity and commit signing

Configure native Git once for each operator and profile. Normal OpenCode shell
commands and DBSCTR commit commands use those settings when they run with the
same home, environment, and checkout. This guide introduces no DBSCTR policy
flags, identity registry, or runtime enforcement. It also works without the
maintainer's personal dotfiles repository.

## Identity, authentication, and verification

These are separate settings:

| Concern | What controls it |
|---|---|
| Commit author and committer | Git name/email configuration and effective identity variables |
| Commit signature | Git signing configuration and access to the selected private key |
| Push/API authentication | Git transport credentials or the selected GitHub CLI account/token |

An authenticated push does not sign an unsigned commit. GitHub determines its
verification badge using the commit signature and registered public key. A
GitHub-created merge can therefore be verified while its locally created parent
commits remain unsigned. See [GitHub signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification).

Choose your own name, verified account email or supported account-specific
no-reply email, hosting login, and signing key for each profile. For example,
`personal`, `employer`, and `consulting` can represent three identities of the
same person. Use a separate key for each profile. Another operator supplies their
own values, rather than copying someone else's identity or using a bot account.

## Keep configuration local

Use a local directory with this layout:

```text
routing.gitconfig
profiles/personal.gitconfig
profiles/employer.gitconfig
profiles/consulting.gitconfig
trust/personal.allowed-signers
trust/employer.allowed-signers
trust/consulting.allowed-signers
```

With the personal dotfiles integration, keep this directory at `local/git/` in
the stable dotfiles source checkout. The tree is Git-ignored and excluded from
chezmoi deployment. Set the optional machine-local `git_identity_routing_file`
to its absolute `routing.gitconfig` path. The managed `.gitconfig` includes it;
actual identities, client mappings, paths, and public-key selections stay local.

Without that integration, choose your own directory, such as
`~/.config/git/local/`, and add a native include to your existing global Git
configuration after generic identity defaults:

```gitconfig
[include]
    path = ~/.config/git/local/routing.gitconfig
```

Keep the directory outside tracked source, or explicitly ignore it. dotfiles-ai
does not manage your `.gitconfig`. Store no private keys, vault exports, or
tokens in these files.

## Configure native routing

This synthetic `routing.gitconfig` defines folder defaults and then an exact
repository exception. Replace the paths with your actual repository layout:

```gitconfig
[user]
    useConfigOnly = true
[commit]
    gpgSign = true

[includeIf "gitdir:~/src/personal/"]
    path = profiles/personal.gitconfig
[includeIf "gitdir:~/src/employer/"]
    path = profiles/employer.gitconfig
[includeIf "gitdir:~/src/consulting/"]
    path = profiles/consulting.gitconfig

# Employer work stored below the personal folder.
[includeIf "gitdir:~/src/personal/client-workspace/.git"]
    path = profiles/employer.gitconfig
[includeIf "gitdir:~/src/personal/client-workspace/.git/worktrees/"]
    path = profiles/employer.gitconfig
```

Git processes includes in place; later applicable values win. `gitdir` follows
the Git directory, including linked-worktree metadata, rather than merely the
visible checkout folder. Inspect primary and linked checkouts, and adapt the
conditions for separately located Git directories. A new client needs only a
new local profile and routing entries. See [Git configuration](https://git-scm.com/docs/git-config).

`user.useConfigOnly=true` prevents Git from guessing a missing identity. It does
not reject an explicitly configured wrong identity. If unmatched repositories
should fail instead of using a generic fallback, deliberately remove obsolete
generic name/email settings after inspecting their origins. Local configuration
and environment overrides still require review.

## Configure signing

For SSH signing, an example `profiles/employer.gitconfig` is:

```gitconfig
[user]
    name = Example Operator
    email = operator@example.com
    signingKey = "ssh-ed25519 REPLACE_WITH_COMPLETE_PUBLIC_KEY"
[gpg]
    format = ssh
[gpg "ssh"]
    allowedSignersFile = /absolute/path/to/local/git/trust/employer.allowed-signers
```

The public key placeholder is intentionally incomplete. Replace it before use.
Add the same email and public key to the local allowed-signers file:

```text
operator@example.com ssh-ed25519 REPLACE_WITH_COMPLETE_PUBLIC_KEY
```

That file contains public trust material, not private keys. Set the signing
program for your chosen provider. Git also supports OpenPGP and X.509 signing;
those use their corresponding key selectors, programs, and public trust stores.
This setup does not require 1Password. Initial live qualification for this
workflow covers SSH signing on macOS, not remote hosts or unattended servers.

### Optional 1Password setup on macOS

Create or select a separate SSH key for each profile in your own 1Password
account. Keep its private key there and copy only its public key into the
corresponding local profile. Add this setting to each applicable profile:

```gitconfig
[gpg "ssh"]
    program = "/Applications/1Password.app/Contents/MacOS/op-ssh-sign"
```

Confirm the path for your installation. Use scoped configuration rather than
automatically replacing all profiles with one global signing key. Follow
[1Password's signing setup](https://www.1password.dev/ssh/git-commit-signing)
for supported versions and app settings.

Per-key application or terminal-session approval caching avoids a prompt for
every commit. A locked vault still needs unlocking before its key can sign.
Approve the normal provider request when appropriate; if signing fails, preserve
the work and restore key availability. Do not retry with signing disabled. See
[1Password's authorization model](https://www.1password.dev/ssh/agent/security).
This desktop signing route does not need a 1Password CLI token or service account.

## Register the public key with the intended account

Add the SSH public key to the matching GitHub account as a **Signing key**.
Authentication-key registration is a separate use, even for the same key. Verify
the displayed account before saving. See [GitHub key enrollment](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account).

CLI enrollment needs `write:ssh_signing_key` permission. If the saved token lacks
it, use GitHub's settings page, or select the intended account with
`gh auth switch --user <login>` and run
`gh auth refresh --hostname github.com --scopes write:ssh_signing_key`.
Complete authorization as that account and restore the previously active CLI
account afterward. Do not confuse missing permission with a missing key.

For CLI registration with multiple saved accounts, select the account's token
explicitly instead of relying on the globally active account. This example
checks the token's account before the external key-registration write. Replace
the synthetic login, public-key path, and title before running it. The supported
interfaces are [account token selection](https://cli.github.com/manual/gh_auth_token),
[environment credentials](https://cli.github.com/manual/gh_help_environment), and
[signing-key registration](https://cli.github.com/manual/gh_ssh-key_add).

```sh
(
    set +x
    unset GH_DEBUG DEBUG
    expected_account=example-operator
    signing_token=$(env -u GH_TOKEN -u GITHUB_TOKEN gh auth token \
        --hostname github.com --user "$expected_account") || exit 1
    actual_account=$(GH_TOKEN="$signing_token" GH_HOST=github.com \
        gh api user --jq .login) || exit 1
    test "$actual_account" = "$expected_account" || exit 1
    GH_TOKEN="$signing_token" GH_HOST=github.com \
        gh ssh-key add /absolute/path/to/signing-key.pub \
        --type signing --title 'Workstation employer signing'
)
```

The token is scoped to this subshell and its child commands; do not print it or store it in
profile files. This does not switch the globally active `gh` account. Git's
author name/email still come from Git, not from this token. DBSCTR's existing
explicit GitHub delivery account remains a separate selection.

## Inspect before committing

Run these commands in each real primary and linked checkout. They display local
identity information, so keep their results local:

```sh
git config --includes --show-origin --get user.name
git config --includes --show-origin --get user.email
git config --includes --show-origin --get user.signingKey
git config --includes --show-origin --get commit.gpgSign
git config --includes --show-origin --get gpg.format
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
```

Compare the values and their file origins with the intended profile. Old
repository-local values can override only part of a profile. Inherited
`GIT_AUTHOR_*` or `GIT_COMMITTER_*` variables can change the effective identity;
[Git's logical variables](https://git-scm.com/docs/git-var) show the result.
Neither Git nor DBSCTR performs an automatic same-profile consistency check.
Configuration inspection also cannot prove that a locked key is ready to sign.

For an optional signing probe, create a disposable local repository with no
remote. Explicitly include the chosen profile there, enable `commit.gpgSign`,
and confirm `git rev-parse --show-toplevel` points to that temporary repository
before creating an empty test commit. Clear inherited repository-selection
variables such as `GIT_DIR` and `GIT_WORK_TREE` first. This tests the signer
without adding commits to real project history; it does not test the real
repository's routing. Never run an empty probe commit in the real project.

After a probe or an ordinary intended commit, verify its signature and metadata:

```sh
git verify-commit HEAD
git show -s --format='author=%an <%ae>%ncommitter=%cn <%ce>%ncommit=%H' HEAD
git log -1 --format='signature=%G? signer=%GF'
```

Check the signer fingerprint against the intended public key; a shared trust
file can trust more than one profile. Use the existing authorized delivery route
for real work, then inspect the exact new commit's hosting attribution and badge.
Local verification alone does not prove the hosting account recognizes the key.

## Limits and recovery

These are native defaults, not an unbypassable policy. Higher-precedence settings,
identity environment variables, or explicit flags such as `--no-gpg-sign` can
change the result. Keep those overrides out of normal agent and operator commit
commands. A Git signing failure should be investigated, not worked around by
creating an unsigned commit.

If local verification fails, distinguish a missing signature from unavailable
public trust material or a wrong signer. If hosting verification fails, check the
exact commit, account email, and signing-key registration. Preserve files and
inspect HEAD before retrying after an uncertain command result.

Existing commits and contributor identities stay unchanged. Do not amend, rebase,
or force-push merely to change old badges. Configure and verify future commits;
rotate or revoke keys through their owner-controlled interfaces and retain
appropriate historical public verification material.
