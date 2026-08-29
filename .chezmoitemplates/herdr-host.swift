import Darwin
import CryptoKit
import Dispatch
import Foundation
import Security
import ServiceManagement
import XPC

private let agentPlistName = "dev.dotfiles-ai.herdr-host-agent.plist"
private let agentLabel = "dev.dotfiles-ai.herdr-host-agent"
private let bundleIdentifier = "dev.dotfiles-ai.herdr-host"
private let controlServiceName = "dev.dotfiles-ai.herdr-host.control"
private let hostVersion = "1"

private enum HostFailure: Error, CustomStringConvertible {
    case configuration(String)
    case operation(String)
    case posix(String, Int32)

    var description: String {
        switch self {
        case .configuration(let message):
            return "configuration error: \(message)"
        case .operation(let message):
            return message
        case .posix(let operation, let code):
            return "\(operation): \(String(cString: strerror(code))) (errno \(code))"
        }
    }
}

private struct HostConfig: Decodable, Sendable {
    let schemaVersion: Int
    let stateRoot: String
    let expectedVolumeUUID: String
    let stateRootExec: String
    let ownerExecutable: String
    let herdrExecutable: String
    let hostWrapper: String
    let healthRoot: String
    let probeIntervalSeconds: Int
    let healthMaxAgeSeconds: Int
    let signingIdentitySHA256: String
    let activationSupported: Bool

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case stateRoot = "state_root"
        case expectedVolumeUUID = "expected_volume_uuid"
        case stateRootExec = "state_root_exec"
        case ownerExecutable = "owner_executable"
        case herdrExecutable = "herdr_executable"
        case hostWrapper = "host_wrapper"
        case healthRoot = "health_root"
        case probeIntervalSeconds = "probe_interval_seconds"
        case healthMaxAgeSeconds = "health_max_age_seconds"
        case signingIdentitySHA256 = "signing_identity_sha256"
        case activationSupported = "activation_supported"
    }

    func validate() throws {
        guard schemaVersion == 1 else {
            throw HostFailure.configuration("unsupported config schema \(schemaVersion)")
        }
        let paths = [stateRoot, stateRootExec, ownerExecutable, herdrExecutable, hostWrapper, healthRoot]
        guard paths.allSatisfy({ $0.hasPrefix("/") }) else {
            throw HostFailure.configuration("all configured paths must be absolute")
        }
        guard !expectedVolumeUUID.isEmpty else {
            throw HostFailure.configuration("expected_volume_uuid is required")
        }
        let fingerprint = signingIdentitySHA256.lowercased()
        let hex = CharacterSet(charactersIn: "0123456789abcdef")
        guard fingerprint.count == 64,
              fingerprint.unicodeScalars.allSatisfy({ hex.contains($0) }) else {
            throw HostFailure.configuration("signing_identity_sha256 must be exactly 64 hexadecimal characters")
        }
        guard probeIntervalSeconds > 0, probeIntervalSeconds <= 300 else {
            throw HostFailure.configuration("probe_interval_seconds must be between 1 and 300")
        }
        guard healthMaxAgeSeconds >= probeIntervalSeconds, healthMaxAgeSeconds <= 3600 else {
            throw HostFailure.configuration("health_max_age_seconds must be at least the probe interval and at most 3600")
        }
        let normalizedState = URL(fileURLWithPath: stateRoot).standardizedFileURL.path
        let normalizedHealth = URL(fileURLWithPath: healthRoot).standardizedFileURL.path
        guard normalizedHealth != normalizedState,
              !normalizedHealth.hasPrefix(normalizedState + "/") else {
            throw HostFailure.configuration("health_root must remain outside the authoritative state root")
        }
    }
}

private enum HealthState: String, Codable, Sendable {
    case starting
    case healthy
    case degradedPermission = "degraded_permission"
    case degradedUnavailable = "degraded_unavailable"
    case recovering

    var isDegraded: Bool {
        self == .degradedPermission || self == .degradedUnavailable
    }
}

private enum ActivationMode: String, Codable, Sendable {
    case probeOnly = "probe_only"
    case active
}

private struct OwnershipRecord: Codable, Sendable {
    let schemaVersion: Int
    let mode: ActivationMode
    let changedAt: String

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case mode
        case changedAt = "changed_at"
    }
}

private struct HealthRecord: Codable, Sendable {
    let schemaVersion: Int
    let hostVersion: String
    let bundleIdentifier: String
    let state: HealthState
    let observedAt: String
    let transitionedAt: String
    let expectedVolumeUUID: String
    let observedVolumeUUID: String?
    let sentinel: Bool
    let writable: Bool
    let errorCategory: String?
    let errnoValue: Int32?
    let activation: ActivationMode
    let childRunning: Bool
    let restartRequired: Bool
    let notificationSent: Bool
    let probeDurationMilliseconds: Int

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case hostVersion = "host_version"
        case bundleIdentifier = "bundle_identifier"
        case state
        case observedAt = "observed_at"
        case transitionedAt = "transitioned_at"
        case expectedVolumeUUID = "expected_volume_uuid"
        case observedVolumeUUID = "observed_volume_uuid"
        case sentinel
        case writable
        case errorCategory = "error_category"
        case errnoValue = "errno"
        case activation
        case childRunning = "child_running"
        case restartRequired = "restart_required"
        case notificationSent = "notification_sent"
        case probeDurationMilliseconds = "probe_duration_ms"
    }

    func replacingRuntime(
        childRunning: Bool,
        restartRequired: Bool,
        notificationSent: Bool? = nil
    ) -> HealthRecord {
        HealthRecord(
            schemaVersion: schemaVersion,
            hostVersion: hostVersion,
            bundleIdentifier: bundleIdentifier,
            state: state,
            observedAt: observedAt,
            transitionedAt: transitionedAt,
            expectedVolumeUUID: expectedVolumeUUID,
            observedVolumeUUID: observedVolumeUUID,
            sentinel: sentinel,
            writable: writable,
            errorCategory: errorCategory,
            errnoValue: errnoValue,
            activation: activation,
            childRunning: childRunning,
            restartRequired: restartRequired,
            notificationSent: notificationSent ?? self.notificationSent,
            probeDurationMilliseconds: probeDurationMilliseconds
        )
    }
}

private struct ProbeOutcome {
    let state: HealthState
    let observedVolumeUUID: String?
    let sentinel: Bool
    let writable: Bool
    let errorCategory: String?
    let errnoValue: Int32?
}

private struct ProcessResult {
    let status: Int32
    let standardOutput: Data
    let standardError: Data
}

private func standardError(_ message: String) {
    FileHandle.standardError.write(Data((message + "\n").utf8))
}

private func writeStandardOutput(_ data: Data) {
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data("\n".utf8))
}

private func timestamp(_ date: Date = Date()) -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return formatter.string(from: date)
}

private func parseTimestamp(_ value: String) -> Date? {
    let fractional = ISO8601DateFormatter()
    fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    if let date = fractional.date(from: value) {
        return date
    }
    return ISO8601DateFormatter().date(from: value)
}

private func executableURL() throws -> URL {
    guard let executable = Bundle.main.executableURL else {
        throw HostFailure.configuration("cannot resolve the host executable")
    }
    return executable.resolvingSymlinksInPath().standardizedFileURL
}

private func contentsURL() throws -> URL {
    try executableURL()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
}

private func appBundleURL() throws -> URL {
    try contentsURL().deletingLastPathComponent()
}

private func loadConfig() throws -> HostConfig {
    _ = try validatedStaticCode(try appBundleURL())
    let configURL = try contentsURL()
        .appendingPathComponent("Resources", isDirectory: true)
        .appendingPathComponent("herdr-host-config.json", isDirectory: false)
    let data: Data
    do {
        data = try Data(contentsOf: configURL, options: [.mappedIfSafe])
    } catch {
        throw HostFailure.configuration("cannot read \(configURL.path): \(error.localizedDescription)")
    }
    let config: HostConfig
    do {
        config = try JSONDecoder().decode(HostConfig.self, from: data)
    } catch {
        throw HostFailure.configuration("invalid herdr-host-config.json: \(error.localizedDescription)")
    }
    try config.validate()
    return config
}

private func runProcess(
    _ executable: String,
    _ arguments: [String],
    timeoutSeconds: Double = 5
) throws -> ProcessResult {
    let process = Process()
    let output = Pipe()
    let errors = Pipe()
    process.executableURL = URL(fileURLWithPath: executable)
    process.arguments = arguments
    process.standardOutput = output
    process.standardError = errors
    do {
        try process.run()
    } catch {
        throw HostFailure.operation("cannot run \(executable): \(error.localizedDescription)")
    }
    let timeoutNanoseconds = UInt64(max(0.1, timeoutSeconds) * 1_000_000_000)
    let deadline = DispatchTime.now().uptimeNanoseconds + timeoutNanoseconds
    while process.isRunning && DispatchTime.now().uptimeNanoseconds < deadline {
        usleep(20_000)
    }
    let timedOut = process.isRunning
    if timedOut {
        process.terminate()
        let terminationDeadline = DispatchTime.now().uptimeNanoseconds + 1_000_000_000
        while process.isRunning && DispatchTime.now().uptimeNanoseconds < terminationDeadline {
            usleep(20_000)
        }
        if process.isRunning {
            _ = Darwin.kill(process.processIdentifier, SIGKILL)
        }
    }
    process.waitUntilExit()
    let result = ProcessResult(
        status: process.terminationStatus,
        standardOutput: output.fileHandleForReading.readDataToEndOfFile(),
        standardError: errors.fileHandleForReading.readDataToEndOfFile()
    )
    if timedOut {
        throw HostFailure.operation("\(executable) timed out after \(timeoutSeconds) seconds")
    }
    return result
}

private func deviceName(for descriptor: Int32) throws -> String {
    var filesystem = statfs()
    guard fstatfs(descriptor, &filesystem) == 0 else {
        throw HostFailure.posix("inspect state-root filesystem", errno)
    }
    return withUnsafePointer(to: &filesystem.f_mntfromname) { pointer in
        pointer.withMemoryRebound(to: CChar.self, capacity: Int(MNAMELEN)) {
            String(cString: $0)
        }
    }
}

private func sameFilesystem(_ leftDescriptor: Int32, _ rightDescriptor: Int32) throws -> Bool {
    var left = statfs()
    var right = statfs()
    guard fstatfs(leftDescriptor, &left) == 0 else {
        throw HostFailure.posix("inspect expected filesystem", errno)
    }
    guard fstatfs(rightDescriptor, &right) == 0 else {
        throw HostFailure.posix("inspect candidate filesystem", errno)
    }
    return left.f_fsid.val.0 == right.f_fsid.val.0
        && left.f_fsid.val.1 == right.f_fsid.val.1
}

private func volumeUUID(for descriptor: Int32) throws -> String {
    let device = try deviceName(for: descriptor)
    let result = try runProcess(
        "/usr/sbin/diskutil",
        ["info", "-plist", device],
        timeoutSeconds: 3
    )
    guard result.status == 0 else {
        let message = String(data: result.standardError, encoding: .utf8)?.lowercased() ?? ""
        if message.contains("operation not permitted") || message.contains("permission denied") {
            throw HostFailure.posix("diskutil info", EPERM)
        }
        if message.contains("not found") || message.contains("does not exist") {
            throw HostFailure.posix("diskutil info", ENOENT)
        }
        throw HostFailure.posix("diskutil info", EIO)
    }
    let object: Any
    do {
        object = try PropertyListSerialization.propertyList(from: result.standardOutput, format: nil)
    } catch {
        throw HostFailure.operation("diskutil returned an invalid property list")
    }
    guard let dictionary = object as? [String: Any],
          let identifier = dictionary["VolumeUUID"] as? String,
          !identifier.isEmpty else {
        throw HostFailure.operation("diskutil did not report a volume UUID")
    }
    return identifier
}

private func writeAll(_ fileDescriptor: Int32, data: Data, operation: String) throws {
    try data.withUnsafeBytes { buffer in
        guard let baseAddress = buffer.baseAddress else {
            return
        }
        var offset = 0
        while offset < buffer.count {
            let result = Darwin.write(
                fileDescriptor,
                baseAddress.advanced(by: offset),
                buffer.count - offset
            )
            if result < 0 {
                if errno == EINTR {
                    continue
                }
                throw HostFailure.posix(operation, errno)
            }
            guard result > 0 else {
                throw HostFailure.posix(operation, EIO)
            }
            offset += result
        }
    }
}

private func readExactly(_ fileDescriptor: Int32, byteCount: Int, operation: String) throws -> Data {
    var data = Data(count: byteCount)
    var offset = 0
    try data.withUnsafeMutableBytes { buffer in
        guard let baseAddress = buffer.baseAddress else {
            return
        }
        while offset < byteCount {
            let result = Darwin.read(
                fileDescriptor,
                baseAddress.advanced(by: offset),
                byteCount - offset
            )
            if result < 0 {
                if errno == EINTR {
                    continue
                }
                throw HostFailure.posix(operation, errno)
            }
            guard result > 0 else {
                throw HostFailure.posix(operation, EIO)
            }
            offset += result
        }
    }
    return data
}

private func classify(_ error: Error, observedVolumeUUID: String? = nil, sentinel: Bool = false) -> ProbeOutcome {
    let code: Int32
    if case HostFailure.posix(_, let errorCode) = error {
        code = errorCode
    } else {
        code = EIO
    }
    if code == EPERM || code == EACCES {
        return ProbeOutcome(
            state: .degradedPermission,
            observedVolumeUUID: observedVolumeUUID,
            sentinel: sentinel,
            writable: false,
            errorCategory: "permission",
            errnoValue: code
        )
    }
    let category: String
    switch code {
    case ENOENT, ENXIO, ENODEV:
        category = "unavailable"
    default:
        category = "io"
    }
    return ProbeOutcome(
        state: .degradedUnavailable,
        observedVolumeUUID: observedVolumeUUID,
        sentinel: sentinel,
        writable: false,
        errorCategory: category,
        errnoValue: code
    )
}

#if HERDR_HOST_TESTING
private func faultOutcome() throws -> ProbeOutcome? {
    let environment = ProcessInfo.processInfo.environment
    guard environment["HERDR_HOST_TEST_MODE"] == "1",
          let fault = environment["HERDR_HOST_TEST_FAULT"],
          !fault.isEmpty else {
        return nil
    }
    switch fault {
    case "permission":
        return ProbeOutcome(
            state: .degradedPermission,
            observedVolumeUUID: nil,
            sentinel: false,
            writable: false,
            errorCategory: "permission",
            errnoValue: EPERM
        )
    case "unavailable":
        return ProbeOutcome(
            state: .degradedUnavailable,
            observedVolumeUUID: nil,
            sentinel: false,
            writable: false,
            errorCategory: "unavailable",
            errnoValue: ENOENT
        )
    case "io":
        return ProbeOutcome(
            state: .degradedUnavailable,
            observedVolumeUUID: nil,
            sentinel: false,
            writable: false,
            errorCategory: "io",
            errnoValue: EIO
        )
    case "wrong_volume":
        return ProbeOutcome(
            state: .degradedUnavailable,
            observedVolumeUUID: "00000000-0000-0000-0000-000000000000",
            sentinel: false,
            writable: false,
            errorCategory: "wrong_volume",
            errnoValue: nil
        )
    case "missing_sentinel":
        return ProbeOutcome(
            state: .degradedUnavailable,
            observedVolumeUUID: nil,
            sentinel: false,
            writable: false,
            errorCategory: "missing_sentinel",
            errnoValue: ENOENT
        )
    default:
        throw HostFailure.configuration("unknown HERDR_HOST_TEST_FAULT value")
    }
}
#else
private func faultOutcome() throws -> ProbeOutcome? {
    nil
}
#endif

private func filesystemProbe(_ config: HostConfig) -> ProbeOutcome {
    let rootDescriptor = Darwin.open(
        config.stateRoot,
        O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC
    )
    guard rootDescriptor >= 0 else {
        return classify(HostFailure.posix("open state root", errno))
    }
    defer { _ = Darwin.close(rootDescriptor) }

    let openedDevice: String
    let observed: String
    do {
        openedDevice = try deviceName(for: rootDescriptor)
        observed = try volumeUUID(for: rootDescriptor)
    } catch {
        return classify(error)
    }

    guard observed.caseInsensitiveCompare(config.expectedVolumeUUID) == .orderedSame else {
        return ProbeOutcome(
            state: .degradedUnavailable,
            observedVolumeUUID: observed,
            sentinel: false,
            writable: false,
            errorCategory: "wrong_volume",
            errnoValue: nil
        )
    }
    do {
        guard try deviceName(for: rootDescriptor) == openedDevice else {
            throw HostFailure.posix("state-root filesystem changed during probe", ESTALE)
        }
    } catch {
        return classify(error, observedVolumeUUID: observed)
    }

    let sentinelDescriptor = Darwin.openat(
        rootDescriptor,
        ".dotfiles-ai-state",
        O_RDONLY | O_NOFOLLOW | O_CLOEXEC
    )
    guard sentinelDescriptor >= 0 else {
        let code = errno
        if code == EPERM || code == EACCES {
            return classify(
                HostFailure.posix("open state sentinel", code),
                observedVolumeUUID: observed
            )
        }
        return ProbeOutcome(
            state: .degradedUnavailable,
            observedVolumeUUID: observed,
            sentinel: false,
            writable: false,
            errorCategory: "missing_sentinel",
            errnoValue: code
        )
    }
    do {
        guard try sameFilesystem(rootDescriptor, sentinelDescriptor) else {
            _ = Darwin.close(sentinelDescriptor)
            return ProbeOutcome(
                state: .degradedUnavailable,
                observedVolumeUUID: observed,
                sentinel: false,
                writable: false,
                errorCategory: "wrong_volume",
                errnoValue: nil
            )
        }
    } catch {
        _ = Darwin.close(sentinelDescriptor)
        return classify(error, observedVolumeUUID: observed)
    }
    var sentinelStatus = stat()
    let sentinelStatResult = Darwin.fstat(sentinelDescriptor, &sentinelStatus)
    _ = Darwin.close(sentinelDescriptor)
    guard sentinelStatResult == 0 else {
        return classify(
            HostFailure.posix("inspect state sentinel", errno),
            observedVolumeUUID: observed
        )
    }
    guard sentinelStatus.st_mode & S_IFMT == S_IFREG else {
        return ProbeOutcome(
            state: .degradedUnavailable,
            observedVolumeUUID: observed,
            sentinel: false,
            writable: false,
            errorCategory: "missing_sentinel",
            errnoValue: EINVAL
        )
    }

    if Darwin.mkdirat(rootDescriptor, ".herdr-host-health", mode_t(0o700)) != 0,
       errno != EEXIST {
        return classify(
            HostFailure.posix("create probe directory", errno),
            observedVolumeUUID: observed,
            sentinel: true
        )
    }
    let probeDirectory = Darwin.openat(
        rootDescriptor,
        ".herdr-host-health",
        O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC
    )
    guard probeDirectory >= 0 else {
        return classify(
            HostFailure.posix("open probe directory", errno),
            observedVolumeUUID: observed,
            sentinel: true
        )
    }
    defer { _ = Darwin.close(probeDirectory) }
    do {
        guard try sameFilesystem(rootDescriptor, probeDirectory) else {
            return ProbeOutcome(
                state: .degradedUnavailable,
                observedVolumeUUID: observed,
                sentinel: true,
                writable: false,
                errorCategory: "wrong_volume",
                errnoValue: nil
            )
        }
    } catch {
        return classify(error, observedVolumeUUID: observed, sentinel: true)
    }

    let probeName = ".probe-\(getpid())-\(UUID().uuidString)"
    let payload = Data("herdr-host-health-v1\n".utf8)
    let probeDescriptor = Darwin.openat(
        probeDirectory,
        probeName,
        O_CREAT | O_EXCL | O_RDWR | O_NOFOLLOW | O_CLOEXEC,
        mode_t(0o600)
    )
    guard probeDescriptor >= 0 else {
        return classify(
            HostFailure.posix("create probe file", errno),
            observedVolumeUUID: observed,
            sentinel: true
        )
    }
    defer {
        _ = Darwin.close(probeDescriptor)
        _ = Darwin.unlinkat(probeDirectory, probeName, 0)
    }

    do {
        try writeAll(probeDescriptor, data: payload, operation: "write probe file")
        guard Darwin.fsync(probeDescriptor) == 0 else {
            throw HostFailure.posix("sync probe file", errno)
        }
        guard Darwin.lseek(probeDescriptor, 0, SEEK_SET) == 0 else {
            throw HostFailure.posix("rewind probe file", errno)
        }
        let readBack = try readExactly(
            probeDescriptor,
            byteCount: payload.count,
            operation: "read probe file"
        )
        guard readBack == payload else {
            throw HostFailure.posix("verify probe file", EIO)
        }
        guard Darwin.unlinkat(probeDirectory, probeName, 0) == 0 else {
            throw HostFailure.posix("remove probe file", errno)
        }
        guard Darwin.fsync(probeDirectory) == 0 else {
            throw HostFailure.posix("sync probe directory", errno)
        }
    } catch {
        return classify(error, observedVolumeUUID: observed, sentinel: true)
    }

    return ProbeOutcome(
        state: .healthy,
        observedVolumeUUID: observed,
        sentinel: true,
        writable: true,
        errorCategory: nil,
        errnoValue: nil
    )
}

private let healthFileName = "health.json"
private let ownershipFileName = "ownership.json"

private func openHealthDirectory(_ config: HostConfig, create: Bool) throws -> Int32? {
    if create {
        do {
            try FileManager.default.createDirectory(
                at: URL(fileURLWithPath: config.healthRoot, isDirectory: true),
                withIntermediateDirectories: true,
                attributes: [.posixPermissions: NSNumber(value: 0o700)]
            )
        } catch {
            throw HostFailure.operation("cannot create health directory: \(error.localizedDescription)")
        }
    }
    let descriptor = Darwin.open(
        config.healthRoot,
        O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC
    )
    guard descriptor >= 0 else {
        if errno == ENOENT, !create {
            return nil
        }
        throw HostFailure.posix("open health directory", errno)
    }
    var information = stat()
    guard Darwin.fstat(descriptor, &information) == 0 else {
        let code = errno
        _ = Darwin.close(descriptor)
        throw HostFailure.posix("inspect health directory", code)
    }
    guard information.st_mode & S_IFMT == S_IFDIR,
          information.st_uid == geteuid() else {
        _ = Darwin.close(descriptor)
        throw HostFailure.configuration("health_root is not a user-owned real directory")
    }
    if information.st_mode & mode_t(0o777) != mode_t(0o700) {
        guard create, Darwin.fchmod(descriptor, mode_t(0o700)) == 0 else {
            _ = Darwin.close(descriptor)
            throw HostFailure.configuration("health_root permissions are not 0700")
        }
    }
    return descriptor
}

private func readPrivateRecord(
    directoryDescriptor: Int32,
    name: String,
    label: String,
    maximumBytes: Int = 65_536
) throws -> Data? {
    let descriptor = Darwin.openat(
        directoryDescriptor,
        name,
        O_RDONLY | O_NOFOLLOW | O_CLOEXEC
    )
    guard descriptor >= 0 else {
        if errno == ENOENT {
            return nil
        }
        throw HostFailure.posix("open \(label)", errno)
    }
    defer { _ = Darwin.close(descriptor) }
    var information = stat()
    guard Darwin.fstat(descriptor, &information) == 0 else {
        throw HostFailure.posix("inspect \(label)", errno)
    }
    guard information.st_mode & S_IFMT == S_IFREG,
          information.st_uid == geteuid(),
          information.st_nlink == 1,
          information.st_mode & mode_t(0o777) == mode_t(0o600),
          information.st_size > 0,
          information.st_size <= maximumBytes else {
        throw HostFailure.configuration("\(label) is not a private bounded regular file")
    }
    return try readExactly(
        descriptor,
        byteCount: Int(information.st_size),
        operation: "read \(label)"
    )
}

private func readHealth(_ config: HostConfig) throws -> HealthRecord? {
    guard let directory = try openHealthDirectory(config, create: false) else {
        return nil
    }
    defer { _ = Darwin.close(directory) }
    guard let data = try readPrivateRecord(
        directoryDescriptor: directory,
        name: healthFileName,
        label: "health record"
    ) else {
        return nil
    }
    do {
        let record = try JSONDecoder().decode(HealthRecord.self, from: data)
        try validateHealthRecord(record, config: config)
        return record
    } catch {
        throw HostFailure.configuration("health record is corrupt")
    }
}

private func validateHealthRecord(_ record: HealthRecord, config: HostConfig) throws {
    guard record.schemaVersion == 1,
          record.hostVersion == hostVersion,
          record.bundleIdentifier == bundleIdentifier,
          record.expectedVolumeUUID.caseInsensitiveCompare(config.expectedVolumeUUID) == .orderedSame,
          parseTimestamp(record.observedAt) != nil,
          parseTimestamp(record.transitionedAt) != nil else {
        throw HostFailure.configuration("health record does not match this host configuration")
    }
    if record.state == .healthy {
        guard record.writable,
              record.sentinel,
              record.errorCategory == nil,
              record.errnoValue == nil,
              let observed = record.observedVolumeUUID,
              observed.caseInsensitiveCompare(config.expectedVolumeUUID) == .orderedSame else {
            throw HostFailure.configuration("healthy record lacks exact-volume proof")
        }
    } else {
        guard !record.writable else {
            throw HostFailure.configuration("non-healthy record cannot be writable")
        }
    }
}

private func activationMode(_ config: HostConfig) throws -> ActivationMode {
    guard let directory = try openHealthDirectory(config, create: false) else {
        throw HostFailure.configuration(
            "ownership marker is missing; run `herdr-host initialize-probe-only` before use"
        )
    }
    defer { _ = Darwin.close(directory) }
    guard let data = try readPrivateRecord(
        directoryDescriptor: directory,
        name: ownershipFileName,
        label: "ownership marker"
    ) else {
        throw HostFailure.configuration(
            "ownership marker is missing; run `herdr-host initialize-probe-only` before use"
        )
    }
    return try decodeOwnership(data, config: config)
}

private func decodeOwnership(_ data: Data, config: HostConfig) throws -> ActivationMode {
    let ownership: OwnershipRecord
    do {
        ownership = try JSONDecoder().decode(OwnershipRecord.self, from: data)
    } catch {
        throw HostFailure.configuration("ownership marker is corrupt: \(error.localizedDescription)")
    }
    guard ownership.schemaVersion == 1 else {
        throw HostFailure.configuration("unsupported ownership marker schema")
    }
    guard ownership.mode != .active || config.activationSupported else {
        throw HostFailure.configuration(
            "active ownership is unsupported by this probe-only build"
        )
    }
    return ownership.mode
}

private func initializeProbeOnly(_ config: HostConfig) throws {
    guard let directory = try openHealthDirectory(config, create: true) else {
        throw HostFailure.operation("cannot open health directory")
    }
    defer { _ = Darwin.close(directory) }
    if let existing = try readPrivateRecord(
        directoryDescriptor: directory,
        name: ownershipFileName,
        label: "ownership marker"
    ) {
        _ = try decodeOwnership(existing, config: config)
        return
    }

    let record = OwnershipRecord(schemaVersion: 1, mode: .probeOnly, changedAt: timestamp())
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
    let data: Data
    do {
        data = try encoder.encode(record)
    } catch {
        throw HostFailure.operation("cannot encode ownership marker: \(error.localizedDescription)")
    }
    let temporaryName = ".ownership.json.\(getpid()).\(UUID().uuidString)"
    let descriptor = Darwin.openat(
        directory,
        temporaryName,
        O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC,
        mode_t(0o600)
    )
    guard descriptor >= 0 else {
        throw HostFailure.posix("create temporary ownership marker", errno)
    }
    var openDescriptor = descriptor
    defer {
        if openDescriptor >= 0 {
            _ = Darwin.close(openDescriptor)
        }
        _ = Darwin.unlinkat(directory, temporaryName, 0)
    }
    try writeAll(descriptor, data: data, operation: "write ownership marker")
    guard Darwin.fsync(descriptor) == 0 else {
        throw HostFailure.posix("sync ownership marker", errno)
    }
    guard Darwin.fchmod(descriptor, mode_t(0o600)) == 0 else {
        throw HostFailure.posix("protect ownership marker", errno)
    }
    guard Darwin.close(descriptor) == 0 else {
        throw HostFailure.posix("close ownership marker", errno)
    }
    openDescriptor = -1

    if Darwin.linkat(directory, temporaryName, directory, ownershipFileName, 0) != 0 {
        if errno == EEXIST {
            guard let existing = try readPrivateRecord(
                directoryDescriptor: directory,
                name: ownershipFileName,
                label: "ownership marker"
            ) else {
                throw HostFailure.configuration("ownership marker disappeared during initialization")
            }
            _ = try decodeOwnership(existing, config: config)
            return
        }
        throw HostFailure.posix("install ownership marker", errno)
    }
    guard Darwin.unlinkat(directory, temporaryName, 0) == 0 else {
        throw HostFailure.posix("finalize ownership marker", errno)
    }
    guard Darwin.fsync(directory) == 0 else {
        throw HostFailure.posix("sync ownership marker directory", errno)
    }
}

private func encodedHealth(_ record: HealthRecord) throws -> Data {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
    do {
        return try encoder.encode(record)
    } catch {
        throw HostFailure.operation("cannot encode health record: \(error.localizedDescription)")
    }
}

private func persistHealth(_ record: HealthRecord, config: HostConfig) throws {
    guard let directory = try openHealthDirectory(config, create: true) else {
        throw HostFailure.operation("cannot open health directory")
    }
    defer { _ = Darwin.close(directory) }
    let temporaryName = ".health.json.\(getpid()).\(UUID().uuidString)"
    let descriptor = Darwin.openat(
        directory,
        temporaryName,
        O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC,
        mode_t(0o600)
    )
    guard descriptor >= 0 else {
        throw HostFailure.posix("create temporary health record", errno)
    }
    var openDescriptor = descriptor
    defer {
        if openDescriptor >= 0 {
            _ = Darwin.close(openDescriptor)
        }
        _ = Darwin.unlinkat(directory, temporaryName, 0)
    }
    let data = try encodedHealth(record)
    try writeAll(descriptor, data: data, operation: "write health record")
    guard Darwin.fsync(descriptor) == 0 else {
        throw HostFailure.posix("sync health record", errno)
    }
    guard Darwin.fchmod(descriptor, mode_t(0o600)) == 0 else {
        throw HostFailure.posix("protect health record", errno)
    }
    guard Darwin.close(descriptor) == 0 else {
        throw HostFailure.posix("close health record", errno)
    }
    openDescriptor = -1
    guard Darwin.renameat(directory, temporaryName, directory, healthFileName) == 0 else {
        throw HostFailure.posix("replace health record", errno)
    }
    guard Darwin.fsync(directory) == 0 else {
        throw HostFailure.posix("sync health directory", errno)
    }
}

private func performProbe(
    config: HostConfig,
    childRunning: Bool? = nil,
    restartRequired: Bool? = nil
) throws -> HealthRecord {
    let started = Date()
    let prior = try readHealth(config)
    let effectiveChildRunning = childRunning ?? prior?.childRunning ?? false
    let effectiveRestartRequired = restartRequired ?? prior?.restartRequired ?? false
    let mode = try activationMode(config)
    let outcome = try faultOutcome() ?? filesystemProbe(config)
    let observed = Date()
    let observedAt = timestamp(observed)
    let transitionedAt: String
    if prior?.state == outcome.state, let previousTransition = prior?.transitionedAt {
        transitionedAt = previousTransition
    } else {
        transitionedAt = observedAt
    }
    let notificationSent: Bool
    if outcome.state == .healthy || outcome.state == .starting || outcome.state == .recovering {
        notificationSent = false
    } else if prior?.state.isDegraded == true {
        notificationSent = prior?.notificationSent ?? false
    } else {
        notificationSent = false
    }
    let record = HealthRecord(
        schemaVersion: 1,
        hostVersion: hostVersion,
        bundleIdentifier: bundleIdentifier,
        state: outcome.state,
        observedAt: observedAt,
        transitionedAt: transitionedAt,
        expectedVolumeUUID: config.expectedVolumeUUID,
        observedVolumeUUID: outcome.observedVolumeUUID,
        sentinel: outcome.sentinel,
        writable: outcome.writable,
        errorCategory: outcome.errorCategory,
        errnoValue: outcome.errnoValue,
        activation: mode,
        childRunning: effectiveChildRunning,
        restartRequired: effectiveRestartRequired,
        notificationSent: notificationSent,
        probeDurationMilliseconds: max(0, Int(observed.timeIntervalSince(started) * 1_000))
    )
    if outcome.state == .healthy, prior?.state.isDegraded == true {
        let recovering = HealthRecord(
            schemaVersion: 1,
            hostVersion: hostVersion,
            bundleIdentifier: bundleIdentifier,
            state: .recovering,
            observedAt: observedAt,
            transitionedAt: observedAt,
            expectedVolumeUUID: config.expectedVolumeUUID,
            observedVolumeUUID: outcome.observedVolumeUUID,
            sentinel: outcome.sentinel,
            writable: false,
            errorCategory: nil,
            errnoValue: nil,
            activation: mode,
            childRunning: effectiveChildRunning,
            restartRequired: effectiveRestartRequired,
            notificationSent: prior?.notificationSent ?? false,
            probeDurationMilliseconds: record.probeDurationMilliseconds
        )
        try persistHealth(recovering, config: config)
    }
    try persistHealth(record, config: config)
    return record
}

private func startingRecord(config: HostConfig, mode: ActivationMode) -> HealthRecord {
    let now = timestamp()
    return HealthRecord(
        schemaVersion: 1,
        hostVersion: hostVersion,
        bundleIdentifier: bundleIdentifier,
        state: .starting,
        observedAt: now,
        transitionedAt: now,
        expectedVolumeUUID: config.expectedVolumeUUID,
        observedVolumeUUID: nil,
        sentinel: false,
        writable: false,
        errorCategory: nil,
        errnoValue: nil,
        activation: mode,
        childRunning: false,
        restartRequired: false,
        notificationSent: false,
        probeDurationMilliseconds: 0
    )
}

private func printHealth(_ record: HealthRecord) throws {
    writeStandardOutput(try encodedHealth(record))
}

private final class AgentHealthResponse: @unchecked Sendable {
    private let lock = NSLock()
    private var storedData: Data?
    private var storedError: String?

    func store(data: Data?, error: String?) {
        lock.lock()
        storedData = data
        storedError = error
        lock.unlock()
    }

    func value() -> (Data?, String?) {
        lock.lock()
        defer { lock.unlock() }
        return (storedData, storedError)
    }
}

private final class AgentCheckInResponse: @unchecked Sendable {
    private let lock = NSLock()
    private var storedPID: Int64?
    private var storedNonce: String?

    func store(pid: Int64?, nonce: String?) {
        lock.lock()
        storedPID = pid
        storedNonce = nonce
        lock.unlock()
    }

    func value() -> (Int64?, String?) {
        lock.lock()
        defer { lock.unlock() }
        return (storedPID, storedNonce)
    }
}

private final class ControlServiceAuthorization: @unchecked Sendable {
    private let lock = NSLock()
    private var authorized = false

    func authorize() {
        lock.lock()
        authorized = true
        lock.unlock()
    }

    func isAuthorized() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return authorized
    }
}

private final class ProbeCoordinator: @unchecked Sendable {
    private let lock = NSLock()
    private var lastRecord: HealthRecord?
    private var lastProbeUptimeNanoseconds: UInt64?
    private var degradationObserved = false

    func probe(
        config: HostConfig,
        childRunning: Bool? = nil,
        restartRequired: Bool? = nil,
        coalesceBurst: Bool = false
    ) throws -> HealthRecord {
        lock.lock()
        defer { lock.unlock() }
        let now = DispatchTime.now().uptimeNanoseconds
        if coalesceBurst,
           let lastRecord,
           let lastProbeUptimeNanoseconds,
           now >= lastProbeUptimeNanoseconds,
           now - lastProbeUptimeNanoseconds <= 1_000_000_000 {
            return lastRecord
        }
        var record = try performProbe(
            config: config,
            childRunning: childRunning,
            restartRequired: restartRequired
        )
        if record.state.isDegraded {
            degradationObserved = true
            if !record.notificationSent {
                record = record.replacingRuntime(
                    childRunning: record.childRunning,
                    restartRequired: record.restartRequired,
                    notificationSent: true
                )
                try persistHealth(record, config: config)
                sendIncidentNotification(record)
            }
        }
        lastRecord = record
        lastProbeUptimeNanoseconds = DispatchTime.now().uptimeNanoseconds
        return record
    }

    func hasObservedDegradation() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return degradationObserved
    }
}

private func startControlService(
    config: HostConfig,
    probeCoordinator: ProbeCoordinator,
    authorization: ControlServiceAuthorization
) -> xpc_connection_t {
    let queue = DispatchQueue(label: controlServiceName)
    let listener = xpc_connection_create_mach_service(
        controlServiceName,
        queue,
        UInt64(XPC_CONNECTION_MACH_SERVICE_LISTENER)
    )
    xpc_connection_set_event_handler(listener) { event in
        guard xpc_get_type(event) == XPC_TYPE_CONNECTION else {
            return
        }
        let peer: xpc_connection_t = event
        guard xpc_connection_get_euid(peer) == geteuid() else {
            xpc_connection_cancel(peer)
            return
        }
        xpc_connection_set_target_queue(peer, queue)
        xpc_connection_set_event_handler(peer) { message in
            guard xpc_get_type(message) == XPC_TYPE_DICTIONARY,
                  let reply = xpc_dictionary_create_reply(message) else {
                return
            }
            guard let commandPointer = xpc_dictionary_get_string(message, "command") else {
                xpc_dictionary_set_string(reply, "error", "unsupported control request")
                xpc_connection_send_message(peer, reply)
                return
            }
            let command = String(cString: commandPointer)
            if command == "check-in",
               let noncePointer = xpc_dictionary_get_string(message, "nonce") {
                xpc_dictionary_set_string(reply, "nonce", noncePointer)
                xpc_dictionary_set_int64(reply, "pid", Int64(getpid()))
            } else if command == "preflight", authorization.isAuthorized() {
                do {
                    let record = try probeCoordinator.probe(
                        config: config,
                        coalesceBurst: true
                    )
                    let data = try encodedHealth(record)
                    data.withUnsafeBytes { bytes in
                        xpc_dictionary_set_data(reply, "health", bytes.baseAddress, bytes.count)
                    }
                } catch {
                    xpc_dictionary_set_string(reply, "error", "host health could not be encoded")
                }
            } else if command == "preflight" {
                xpc_dictionary_set_string(reply, "error", "host control service is not checked in")
            } else {
                xpc_dictionary_set_string(reply, "error", "unsupported control request")
            }
            xpc_connection_send_message(peer, reply)
        }
        xpc_connection_resume(peer)
    }
    xpc_connection_resume(listener)
    return listener
}

private func validateExclusiveControlServiceCheckIn() throws {
    let queue = DispatchQueue(label: controlServiceName + ".check-in")
    let connection = xpc_connection_create_mach_service(controlServiceName, queue, 0)
    xpc_connection_set_event_handler(connection) { _ in }
    xpc_connection_resume(connection)
    defer { xpc_connection_cancel(connection) }

    let nonce = UUID().uuidString
    let message = xpc_dictionary_create(nil, nil, 0)
    xpc_dictionary_set_string(message, "command", "check-in")
    xpc_dictionary_set_string(message, "nonce", nonce)
    let response = AgentCheckInResponse()
    let completed = DispatchSemaphore(value: 0)
    xpc_connection_send_message_with_reply(connection, message, queue) { reply in
        if xpc_get_type(reply) == XPC_TYPE_DICTIONARY,
           let noncePointer = xpc_dictionary_get_string(reply, "nonce") {
            response.store(
                pid: xpc_dictionary_get_int64(reply, "pid"),
                nonce: String(cString: noncePointer)
            )
        } else {
            response.store(pid: nil, nonce: nil)
        }
        completed.signal()
    }
    guard completed.wait(timeout: .now() + .seconds(2)) == .success else {
        throw HostFailure.operation("exclusive launchd control-service check-in timed out")
    }
    let (respondingPID, respondingNonce) = response.value()
    guard respondingPID == Int64(getpid()), respondingNonce == nonce else {
        throw HostFailure.operation(
            "exclusive launchd control-service check-in failed; refusing foreground agent mode"
        )
    }
}

private func requestAgentHealth(config: HostConfig) throws -> HealthRecord {
    let queue = DispatchQueue(label: controlServiceName + ".client")
    let connection = xpc_connection_create_mach_service(controlServiceName, queue, 0)
    xpc_connection_set_event_handler(connection) { _ in }
    xpc_connection_resume(connection)
    defer { xpc_connection_cancel(connection) }

    let message = xpc_dictionary_create(nil, nil, 0)
    xpc_dictionary_set_string(message, "command", "preflight")
    let response = AgentHealthResponse()
    let completed = DispatchSemaphore(value: 0)
    xpc_connection_send_message_with_reply(connection, message, queue) { reply in
        if xpc_get_type(reply) == XPC_TYPE_DICTIONARY {
            var byteCount = 0
            if let bytes = xpc_dictionary_get_data(reply, "health", &byteCount) {
                if byteCount > 0 {
                    response.store(data: Data(bytes: bytes, count: byteCount), error: nil)
                } else {
                    response.store(data: nil, error: "host returned an empty health record")
                }
            } else if let errorPointer = xpc_dictionary_get_string(reply, "error") {
                response.store(data: nil, error: String(cString: errorPointer))
            } else {
                response.store(data: nil, error: "host returned an invalid control reply")
            }
        } else {
            response.store(data: nil, error: "registered host control service is unavailable")
        }
        completed.signal()
    }
    guard completed.wait(timeout: .now() + .seconds(4)) == .success else {
        throw HostFailure.operation("registered host control service timed out after 4 seconds")
    }
    let (data, responseError) = response.value()
    if let responseError {
        throw HostFailure.operation(responseError)
    }
    guard let data else {
        throw HostFailure.operation("registered host returned no health record")
    }
    do {
        let record = try JSONDecoder().decode(HealthRecord.self, from: data)
        try validateHealthRecord(record, config: config)
        return record
    } catch {
        throw HostFailure.operation("registered host returned invalid health JSON")
    }
}

private func preflightFailure(_ record: HealthRecord) -> Never {
    switch record.errorCategory {
    case "permission":
        standardError(
            "Herdr Host cannot access the configured external volume (\(record.state.rawValue)). " +
            "Verify Full Disk Access for ~/Applications/Herdr Host.app, then wait for a healthy probe; " +
            "do not restart Herdr or raise the file-descriptor limit."
        )
    case "wrong_volume":
        standardError(
            "Herdr Host found the wrong external volume UUID. Mount the expected volume; " +
            "no managed state was written and no process was restarted."
        )
    case "missing_sentinel":
        standardError(
            "Herdr Host could not validate the managed state sentinel. Restore the expected volume; " +
            "do not recreate the sentinel on a replacement filesystem."
        )
    default:
        standardError(
            "Herdr Host external-volume health is \(record.state.rawValue). " +
            "Inspect `herdr-host doctor`; existing Herdr and OpenCode processes were left untouched."
        )
    }
    Darwin.exit(75)
}

private func runPreflight(config: HostConfig, arguments: [String]) throws {
    let accepted = Set(["--if-active", "--cached"])
    guard arguments.allSatisfy({ accepted.contains($0) }) else {
        throw HostFailure.configuration("usage: herdr-host preflight --if-active [--cached]")
    }
    let ifActive = arguments.contains("--if-active")
    guard ifActive else {
        throw HostFailure.configuration("preflight requires --if-active")
    }
    guard try activationMode(config) == .active else {
        return
    }

    let record: HealthRecord
    if arguments.contains("--cached") {
        guard let cached = try readHealth(config),
              let observed = parseTimestamp(cached.observedAt),
              Date().timeIntervalSince(observed) >= 0,
              Date().timeIntervalSince(observed) <= Double(config.healthMaxAgeSeconds) else {
            standardError("Herdr Host health is missing or stale; wait for the registered host probe.")
            Darwin.exit(75)
        }
        record = cached
    } else {
        do {
            record = try requestAgentHealth(config: config)
        } catch {
            standardError(
                "Herdr Host is active but its bounded control check failed: \(error). " +
                "Inspect `herdr-host status --json`; do not restart existing panes."
            )
            Darwin.exit(75)
        }
    }
    guard record.activation == .active,
          let observed = parseTimestamp(record.observedAt),
          Date().timeIntervalSince(observed) >= 0,
          Date().timeIntervalSince(observed) <= Double(config.healthMaxAgeSeconds) else {
        standardError("Herdr Host is active but its health record is missing, stale, or pre-activation.")
        Darwin.exit(75)
    }
    guard record.state == .healthy, record.sentinel, record.writable else {
        preflightFailure(record)
    }
}

private func managedService() -> SMAppService {
    SMAppService.agent(plistName: "dev.dotfiles-ai.herdr-host-agent.plist")
}

private func serviceStatusName(_ status: SMAppService.Status) -> String {
    switch status {
    case .notRegistered:
        return "not_registered"
    case .enabled:
        return "enabled"
    case .requiresApproval:
        return "requires_approval"
    case .notFound:
        return "not_found"
    @unknown default:
        return "unknown"
    }
}

private func registrationStatusJSON() throws -> Data {
    let value: [String: Any] = [
        "agent_plist": agentPlistName,
        "bundle_identifier": bundleIdentifier,
        "status": serviceStatusName(managedService().status),
    ]
    return try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
}

private func hexadecimalDigest<D: Sequence>(_ digest: D) -> String where D.Element == UInt8 {
    digest.map { String(format: "%02x", $0) }.joined()
}

private func validatedStaticCode(_ appURL: URL) throws -> SecStaticCode {
    var optionalCode: SecStaticCode?
    var status = SecStaticCodeCreateWithPath(appURL as CFURL, SecCSFlags(), &optionalCode)
    guard status == errSecSuccess, let code = optionalCode else {
        throw HostFailure.operation("cannot inspect Herdr Host signature (status \(status))")
    }
    status = SecStaticCodeCheckValidity(
        code,
        SecCSFlags(rawValue: kSecCSStrictValidate | kSecCSCheckAllArchitectures),
        nil
    )
    guard status == errSecSuccess else {
        throw HostFailure.operation(
            "Herdr Host signature or sealed resources are invalid (status \(status))"
        )
    }
    return code
}

private func validateRegistrationIdentity(config: HostConfig) throws {
    let appURL = try appBundleURL().resolvingSymlinksInPath().standardizedFileURL
    let applicationsURL = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Applications", isDirectory: true)
        .standardizedFileURL
    let expectedAppURL = applicationsURL
        .appendingPathComponent("Herdr Host.app", isDirectory: true)
        .standardizedFileURL
    for (url, label) in [
        (applicationsURL, "~/Applications"),
        (expectedAppURL, "~/Applications/Herdr Host.app"),
    ] {
        var information = stat()
        guard Darwin.lstat(url.path, &information) == 0,
              information.st_mode & S_IFMT == S_IFDIR,
              information.st_uid == geteuid(),
              information.st_mode & mode_t(0o022) == 0 else {
            throw HostFailure.configuration(
                "\(label) must be a real user-owned directory without group/world write access"
            )
        }
    }
    guard appURL.path == expectedAppURL.path else {
        throw HostFailure.configuration(
            "registration requires ~/Applications/Herdr Host.app; refusing \(appURL.path)"
        )
    }
    guard try executableURL().path == URL(fileURLWithPath: config.hostWrapper)
        .resolvingSymlinksInPath().standardizedFileURL.path else {
        throw HostFailure.configuration("host_wrapper does not identify this app executable")
    }

    let code = try validatedStaticCode(appURL)
    var optionalInformation: CFDictionary?
    let status = SecCodeCopySigningInformation(
        code,
        SecCSFlags(rawValue: kSecCSSigningInformation),
        &optionalInformation
    )
    guard status == errSecSuccess,
          let information = optionalInformation as? [String: Any],
          information[kSecCodeInfoIdentifier as String] as? String == bundleIdentifier,
          let certificates = information[kSecCodeInfoCertificates as String] as? [SecCertificate],
          let leaf = certificates.first else {
        throw HostFailure.operation("Herdr Host signing information is incomplete or has the wrong identifier")
    }
    let certificateData = SecCertificateCopyData(leaf) as Data
    let sha256 = hexadecimalDigest(SHA256.hash(data: certificateData))
    guard sha256.caseInsensitiveCompare(config.signingIdentitySHA256) == .orderedSame else {
        throw HostFailure.operation("Herdr Host leaf certificate does not match the configured SHA-256")
    }
    let sha1 = hexadecimalDigest(Insecure.SHA1.hash(data: certificateData))
    let expectedRequirement = "designated => identifier \"\(bundleIdentifier)\" and certificate leaf = H\"\(sha1)\""
    let requirement = try runProcess(
        "/usr/bin/codesign",
        ["--display", "--requirements", "-", appURL.path]
    )
    let requirementText = String(
        data: requirement.standardError + requirement.standardOutput,
        encoding: .utf8
    ) ?? ""
    guard requirement.status == 0,
          requirementText.split(separator: "\n").contains(Substring(expectedRequirement)) else {
        throw HostFailure.operation("Herdr Host designated requirement is not the exact stable requirement")
    }
}

private func operatorProbe(config: HostConfig) throws -> (HealthRecord, String) {
    _ = try activationMode(config)
    switch managedService().status {
    case .enabled:
        return (try requestAgentHealth(config: config), "registered_agent")
    case .requiresApproval:
        throw HostFailure.operation(
            "Herdr Host requires Login Items approval; refusing a foreground probe as host evidence"
        )
    case .notRegistered, .notFound:
        throw HostFailure.operation(
            "Herdr Host is not registered; refusing a foreground probe as host evidence"
        )
    @unknown default:
        throw HostFailure.operation(
            "Herdr Host registration status is unknown; refusing foreground health overwrite"
        )
    }
}

private func registerAgent(config: HostConfig) throws {
    try initializeProbeOnly(config)
    guard try activationMode(config) == .probeOnly else {
        throw HostFailure.operation("refusing to register while the ownership marker is active")
    }
    do {
        try managedService().register()
    } catch {
        throw HostFailure.operation("SMAppService registration failed: \(error.localizedDescription)")
    }
    writeStandardOutput(try registrationStatusJSON())
}

private func unregisterAgent(config: HostConfig) throws {
    guard try activationMode(config) == .probeOnly else {
        throw HostFailure.operation(
            "refusing to unregister an active owner because SMAppService would terminate it"
        )
    }
    do {
        try managedService().unregister()
    } catch {
        throw HostFailure.operation("SMAppService unregistration failed: \(error.localizedDescription)")
    }
    writeStandardOutput(try registrationStatusJSON())
}

private func codesignResult(_ appURL: URL) -> (valid: Bool, requirement: String?) {
    let verify = try? runProcess("/usr/bin/codesign", ["--verify", "--strict", appURL.path])
    let requirement = try? runProcess("/usr/bin/codesign", ["--display", "--requirements", "-", appURL.path])
    let requirementText = requirement.flatMap {
        let combined = $0.standardError + $0.standardOutput
        let value = String(data: combined, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
        return value?.isEmpty == false ? value : nil
    }
    return (verify?.status == 0, requirementText)
}

private func runDoctor(config: HostConfig) throws {
    let (health, probeResponsibility) = try operatorProbe(config: config)
    let appURL = try appBundleURL()
    let signing = codesignResult(appURL)
    let healthObject = try JSONSerialization.jsonObject(with: encodedHealth(health))
    let values: [String: Any] = [
        "agent_plist": agentPlistName,
        "app_bundle": appURL.path,
        "bundle_identifier": bundleIdentifier,
        "configured_signing_identity_sha256": config.signingIdentitySHA256.lowercased(),
        "designated_requirement": signing.requirement ?? NSNull(),
        "health": healthObject,
        "herdr_executable_present": FileManager.default.isExecutableFile(atPath: config.herdrExecutable),
        "probe_responsibility": probeResponsibility,
        "registration_status": serviceStatusName(managedService().status),
        "signature_valid": signing.valid,
        "state_root": config.stateRoot,
    ]
    writeStandardOutput(
        try JSONSerialization.data(withJSONObject: values, options: [.sortedKeys, .withoutEscapingSlashes])
    )
}

private func sendIncidentNotification(_ record: HealthRecord) {
#if HERDR_HOST_TESTING
    if let logPath = ProcessInfo.processInfo.environment["HERDR_HOST_TEST_NOTIFICATION_LOG"],
       let line = (record.state.rawValue + "\n").data(using: .utf8) {
        let descriptor = Darwin.open(
            logPath,
            O_WRONLY | O_CREAT | O_APPEND | O_NOFOLLOW | O_CLOEXEC,
            mode_t(0o600)
        )
        if descriptor >= 0 {
            try? writeAll(descriptor, data: line, operation: "write test notification log")
            _ = Darwin.close(descriptor)
        }
        return
    }
#endif
    let state = record.state.rawValue
    let script = "display notification \"New managed starts are paused; existing processes were not restarted.\" " +
        "with title \"Herdr Host: \(state)\""
    _ = try? runProcess("/usr/bin/osascript", ["-e", script])
}

private final class AgentController {
    private let config: HostConfig
    private let probeCoordinator = ProbeCoordinator()
    private var child: Process?
    private var childWasStarted = false
    private var hadDegradation: Bool {
        probeCoordinator.hasObservedDegradation()
    }
    private var restartRequired = false

    init(config: HostConfig) {
        self.config = config
    }

    private func startChild() throws {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: config.stateRootExec)
        process.arguments = [config.ownerExecutable]
        let inherited = ProcessInfo.processInfo.environment
        let allowedEnvironmentKeys = [
            "HOME", "LANG", "LC_ALL", "LC_CTYPE", "LOGNAME", "PATH", "SHELL", "SSH_AUTH_SOCK", "TMPDIR", "USER",
        ]
        var environment: [String: String] = [:]
        for key in allowedEnvironmentKeys {
            if let value = inherited[key] {
                environment[key] = value
            }
        }
        environment["HOME"] = environment["HOME"] ?? NSHomeDirectory()
        environment["LANG"] = environment["LANG"] ?? "en_US.UTF-8"
        environment["LC_CTYPE"] = environment["LC_CTYPE"] ?? "en_US.UTF-8"
        environment["PATH"] = environment["PATH"]
            ?? (NSHomeDirectory() + "/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
        environment["DOTFILES_AI_STATE_ROOT"] = config.stateRoot
        environment["XDG_DATA_HOME"] = config.stateRoot + "/xdg/data"
        environment["XDG_STATE_HOME"] = config.stateRoot + "/xdg/state"
        environment["DBSCTR_STATE_ROOT"] = config.stateRoot + "/dbsctr"
        environment["DBSCTR_WORKTREE_ROOT"] = config.stateRoot + "/dbsctr/worktrees"
        environment["DBSCTR_RND_STATE"] = config.stateRoot + "/dbsctr/rnd/dbsctr-rnd.sqlite3"
        environment["DBSCTR_RND_RECEIPTS"] = config.stateRoot + "/dbsctr/rnd/receipts"
        environment["HERMES_HOME"] = config.stateRoot + "/hermes"
        environment["HERDR_HOST_ACTIVE"] = "1"
        environment["HERDR_HOST_BIN"] = config.hostWrapper
        process.environment = environment
        do {
            try process.run()
        } catch {
            throw HostFailure.operation("cannot start the managed Herdr owner: \(error.localizedDescription)")
        }
        child = process
        childWasStarted = true
    }

    private func stopChild() {
        guard let child else {
            return
        }
        if child.isRunning {
            child.terminate()
            child.waitUntilExit()
        }
        self.child = nil
    }

    func run() throws -> Int32 {
        Darwin.signal(SIGTERM, SIG_IGN)
        Darwin.signal(SIGINT, SIG_IGN)
        let controlAuthorization = ControlServiceAuthorization()
        let controlService = startControlService(
            config: config,
            probeCoordinator: probeCoordinator,
            authorization: controlAuthorization
        )
#if !HERDR_HOST_TESTING
        do {
            try validateExclusiveControlServiceCheckIn()
            controlAuthorization.authorize()
        } catch {
            xpc_connection_cancel(controlService)
            throw error
        }
#else
        controlAuthorization.authorize()
#endif
        let stop = DispatchSemaphore(value: 0)
        let termination = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .global())
        let interrupt = DispatchSource.makeSignalSource(signal: SIGINT, queue: .global())
        termination.setEventHandler { stop.signal() }
        interrupt.setEventHandler { stop.signal() }
        termination.resume()
        interrupt.resume()
        defer {
            xpc_connection_cancel(controlService)
            termination.cancel()
            interrupt.cancel()
            stopChild()
        }

        var degradedAttempt = 0
        while true {
            var record = try probeCoordinator.probe(
                config: config,
                childRunning: child?.isRunning ?? false,
                restartRequired: restartRequired
            )

            if record.state != .healthy {
                degradedAttempt = min(degradedAttempt + 1, 6)
            } else {
                degradedAttempt = 0
            }

            if let runningChild = child, !runningChild.isRunning {
                child = nil
                if hadDegradation {
                    restartRequired = true
                    record = record.replacingRuntime(
                        childRunning: false,
                        restartRequired: true
                    )
                    try persistHealth(record, config: config)
                } else {
                    return 1
                }
            }

            if record.activation == .active, record.state == .healthy, child == nil {
                if childWasStarted && hadDegradation {
                    restartRequired = true
                    record = record.replacingRuntime(
                        childRunning: false,
                        restartRequired: true
                    )
                    try persistHealth(record, config: config)
                } else {
                    try startChild()
                    record = record.replacingRuntime(
                        childRunning: true,
                        restartRequired: false
                    )
                    try persistHealth(record, config: config)
                }
            }

            let multiplier = 1 << degradedAttempt
            let delay = min(60, config.probeIntervalSeconds * multiplier)
            if stop.wait(timeout: .now() + .seconds(delay)) == .success {
                return 0
            }
        }
    }
}

private func usage() {
    let text = """
    usage: herdr-host <command>

      agent                         run the registered probe-only/active host agent
      probe                         request one registered host-owned read/write probe
      preflight --if-active [--cached]
                                    fail closed only after durable ownership is active
      status --json                 print the last completed probe
      doctor                        inspect registration, signing, and live volume health
      initialize-probe-only         create the fail-closed staging ownership marker once
      register                      register the probe-only bundled LaunchAgent
      unregister                    unregister only while ownership is probe_only
      registration-status [--json]  print the SMAppService state
      open-login-items              open the macOS Login Items settings pane
    """
    FileHandle.standardOutput.write(Data((text + "\n").utf8))
}

private func runCommand() throws -> Int32 {
    let arguments = Array(CommandLine.arguments.dropFirst())
    if arguments.isEmpty || arguments == ["--help"] || arguments == ["help"] {
        usage()
        return 0
    }

    let config = try loadConfig()
#if !HERDR_HOST_TESTING && !HERDR_HOST_ORIGIN_TESTING
    try validateRegistrationIdentity(config: config)
#endif
    switch arguments[0] {
    case "agent":
        guard arguments.count == 1 else {
            throw HostFailure.configuration("agent takes no arguments")
        }
#if !HERDR_HOST_TESTING
        let serviceName = ProcessInfo.processInfo.environment["XPC_SERVICE_NAME"]
        guard getppid() == 1,
              serviceName == agentLabel || serviceName == controlServiceName else {
            throw HostFailure.operation(
                "agent mode requires launchd provenance diagnostics; direct agent execution is refused"
            )
        }
#endif
        return try AgentController(config: config).run()
    case "probe":
        guard arguments.count == 1 else {
            throw HostFailure.configuration("probe takes no arguments")
        }
#if HERDR_HOST_TESTING
        try printHealth(performProbe(config: config))
#else
        try printHealth(operatorProbe(config: config).0)
#endif
        return 0
    case "preflight":
        try runPreflight(config: config, arguments: Array(arguments.dropFirst()))
        return 0
    case "status":
        guard arguments.count == 1 || arguments == ["status", "--json"] else {
            throw HostFailure.configuration("usage: herdr-host status [--json]")
        }
        let mode = try activationMode(config)
        let record = try readHealth(config) ?? startingRecord(config: config, mode: mode)
        if arguments.contains("--json") {
            try printHealth(record)
        } else {
            print("state=\(record.state.rawValue) activation=\(record.activation.rawValue) " +
                  "writable=\(record.writable) restart_required=\(record.restartRequired)")
        }
        return 0
    case "doctor":
        guard arguments.count == 1 else {
            throw HostFailure.configuration("doctor takes no arguments")
        }
        try runDoctor(config: config)
        return 0
    case "initialize-probe-only":
        guard arguments.count == 1 else {
            throw HostFailure.configuration("initialize-probe-only takes no arguments")
        }
        try initializeProbeOnly(config)
        return 0
    case "register":
        guard arguments.count == 1 else {
            throw HostFailure.configuration("register takes no arguments")
        }
        try registerAgent(config: config)
        return 0
    case "unregister":
        guard arguments.count == 1 else {
            throw HostFailure.configuration("unregister takes no arguments")
        }
        try unregisterAgent(config: config)
        return 0
    case "registration-status":
        guard arguments.count == 1 || arguments == ["registration-status", "--json"] else {
            throw HostFailure.configuration("usage: herdr-host registration-status [--json]")
        }
        writeStandardOutput(try registrationStatusJSON())
        return 0
    case "open-login-items":
        guard arguments.count == 1 else {
            throw HostFailure.configuration("open-login-items takes no arguments")
        }
        SMAppService.openSystemSettingsLoginItems()
        return 0
    default:
        throw HostFailure.configuration("unknown command \(arguments[0])")
    }
}

do {
    Darwin.exit(try runCommand())
} catch {
    standardError("herdr-host: \(error)")
    Darwin.exit(78)
}
