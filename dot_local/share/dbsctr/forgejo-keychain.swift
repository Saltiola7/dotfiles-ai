import Foundation
import Darwin
import Security

// Run as its own executable so a Keychain ACL can trust this reader alone.
// The credential protocol subprocess captures stdout in a private pipe.
struct Selection {
    let server: String
    let port: Int
    let account: String
    let path: String

    init?(_ arguments: [String]) {
        guard arguments.count == 4,
              let port = Int(arguments[1]), (0...65535).contains(port),
              arguments[3].hasSuffix(".git"),
              arguments.allSatisfy({
                  !$0.isEmpty && $0.utf8.count <= 4096 &&
                  !$0.utf8.contains(where: { $0 < 32 || $0 == 127 })
              }) else { return nil }
        self.server = arguments[0]
        self.port = port
        self.account = arguments[2]
        self.path = arguments[3]
    }

    var query: [String: Any] {
        [
            kSecClass as String: kSecClassInternetPassword,
            kSecAttrProtocol as String: kSecAttrProtocolHTTPS,
            kSecAttrAuthenticationType as String: kSecAttrAuthenticationTypeDefault,
            kSecAttrServer as String: server,
            kSecAttrPort as String: port,
            kSecAttrAccount as String: account,
            kSecAttrPath as String: path,
            kSecUseAuthenticationUI as String: kSecUseAuthenticationUIFail,
            kSecReturnAttributes as String: true,
        ]
    }

    func matches(_ item: [String: Any]) -> Bool {
        let proto = item[kSecAttrProtocol as String]
        let https = (proto as? String) == (kSecAttrProtocolHTTPS as String) ||
            (proto as? NSNumber)?.uint32Value == 0x68747073 // 'htps'
        return https &&
            (item[kSecAttrPort as String] as? NSNumber)?.intValue == port &&
            (item[kSecAttrServer as String] as? String) == server &&
            (item[kSecAttrAccount as String] as? String) == account &&
            (item[kSecAttrPath as String] as? String) == path
    }
}

func readCredential(_ selection: Selection) -> Data? {
    var metadataQuery = selection.query
    metadataQuery[kSecMatchLimit as String] = kSecMatchLimitAll
    metadataQuery[kSecReturnRef as String] = true
    var metadataResult: CFTypeRef?
    guard SecItemCopyMatching(metadataQuery as CFDictionary, &metadataResult) == errSecSuccess,
          let items = metadataResult as? [[String: Any]], items.count == 1,
          let item = items.first, selection.matches(item),
          let reference = item[kSecValueRef as String],
          CFGetTypeID(reference as CFTypeRef) == SecKeychainItemGetTypeID()
    else { return nil }

    var dataQuery = selection.query
    dataQuery[kSecMatchLimit as String] = kSecMatchLimitOne
    dataQuery[kSecMatchItemList as String] = [reference]
    dataQuery[kSecReturnData as String] = true
    var dataResult: CFTypeRef?
    guard SecItemCopyMatching(dataQuery as CFDictionary, &dataResult) == errSecSuccess,
          let credential = dataResult as? [String: Any], selection.matches(credential),
          let data = credential[kSecValueData as String] as? Data,
          (1...4096).contains(data.count),
          let password = String(data: data, encoding: .utf8),
          !password.utf8.contains(where: { $0 == 0 || $0 == 10 || $0 == 13 }),
          !password.contains("\u{FFFD}")
    else { return nil }
    return data
}

guard isatty(STDOUT_FILENO) == 0,
      let selection = Selection(Array(CommandLine.arguments.dropFirst())),
      SecKeychainSetUserInteractionAllowed(false) == errSecSuccess,
      let credential = readCredential(selection)
else { exit(1) }

FileHandle.standardOutput.write(credential)
