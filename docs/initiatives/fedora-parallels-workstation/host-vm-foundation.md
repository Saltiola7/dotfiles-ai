# Host VM Foundation Slice

## Outcome

The personal configuration source declares Parallels Desktop and provides a
small fail-closed operator command for inspecting prerequisites, preparing the
dedicated APFS volume, creating the Fedora workstation, selecting stopped-VM
resource profiles, and verifying the resulting topology. Operating-system
installation remains interactive.

## Behavior

- Given the exact expected APFS container and existing host external volume,
  when storage preparation is explicitly invoked, then it adds only the missing
  sibling volume with the approved quota and verifies its identity and mount.
- Given any container, volume, quota, mount, free-space, or existing-name
  mismatch, then preparation refuses without deletion, erase, partitioning, or
  fallback.
- Given the official Fedora ARM64 image and signed checksum metadata, when image
  preparation completes, then both signature and image digest pass before the
  image is eligible for VM creation.
- Given Parallels is installed, activated, and its CLI capabilities match the
  source contract, when creation runs, then it creates one stopped ARM64 VM with
  the approved root disk, external data disk, shared NAT, and custom shares.
- Given the VM already exists, creation refuses rather than cloning, replacing,
  unregistering, or deleting it.
- Given a resource profile is requested while the VM is running or suspended,
  the command refuses and reports the required stopped state.
- Given Parallels Tools are installed after Fedora installation, verification
  proves graphics, dynamic resizing, clipboard, and exact read-only/read-write
  share behavior.
- Given a Fedora kernel upgrade breaks integration, recovery boots a retained
  kernel when needed, installs matching build prerequisites, reinstalls the
  vendor Tools image, reboots, and repeats verification.

## Interfaces

The managed operator command exposes only:

```text
doctor
prepare-storage
prepare-image
create
profile lean|daily|heavy
status
verify
```

It does not expose a destructive delete or reset command. Reinstallation first
detaches and preserves the data disk, then uses explicit Parallels UI/CLI removal
review before `create` is run again.

## Validation

- Render the personal source for each existing machine type and prove unchanged
  targets outside the affected scope.
- Unit-test exact command construction, stopped-state refusal, existing-resource
  refusal, APFS identity checks, quota checks, and no destructive subcommands.
- Parse every rendered shell script and run the repository test suite.
- Verify the installed Parallels version and capabilities from installed help,
  rather than assuming syntax from another release.
- Inspect the VM configuration for CPU, memory, architecture, disks, network,
  startup, snapshots, and custom shares.
- Perform read/write probes only against disposable files in the declared Git
  share; the complete external-volume share must reject writes.

## Gate Applicability

Domain, Behavior, Spec, Contract, test-driven implementation, Refactor,
Review/Integrate, Deploy, Operate, and Maintain/Retire are required. Release is
not applicable because the cycle publishes no versioned artifact.
