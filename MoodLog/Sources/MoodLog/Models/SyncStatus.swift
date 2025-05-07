import Foundation

enum SyncStatus: Int16 {
    case notSynced = 0
    case syncing = 1
    case synced = 2
    case failed = 3
} 