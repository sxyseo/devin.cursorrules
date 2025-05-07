import Foundation

class SyncManager {
    static let shared = SyncManager()
    
    private init() {}
    
    var deviceId: String {
        if let id = UserDefaults.standard.string(forKey: "deviceId") {
            return id
        }
        let newId = UUID().uuidString
        UserDefaults.standard.set(newId, forKey: "deviceId")
        return newId
    }
    
    func sync() {
        // 这里实现同步逻辑
        // 目前只是一个空实现，后续可以添加实际的同步功能
    }
} 