import Foundation
import SwiftUI
import CoreData
import Combine
#if canImport(UIKit)
import UIKit
#endif

class JournalEntryStore: ObservableObject {
    static let shared = JournalEntryStore()
    
    @Published var entries: [JournalEntry] = []
    private var cancellables = Set<AnyCancellable>()
    private let coreDataManager = CoreDataManager.shared
    private let syncManager = SyncManager.shared
    
    private init() {
        loadEntries()
        setupSyncNotifications()
    }
    
    private func setupSyncNotifications() {
        NotificationCenter.default.publisher(for: .NSManagedObjectContextDidSave)
            .sink { [weak self] _ in
                self?.loadEntries()
            }
            .store(in: &cancellables)
    }
    
    func loadEntries() {
        entries = coreDataManager.fetchEntries()
    }
    
    func loadEntries(for date: Date) {
        entries = coreDataManager.fetchEntries(for: date)
    }
    
    func addEntry(mood: Int, moodType: MoodType, content: String, date: Date) {
        _ = coreDataManager.saveEntry(
            mood: Int16(mood),
            moodType: Int16(moodType.rawValue),
            content: content,
            date: date,
            imageData: nil
        )
        
        loadEntries()
        syncManager.sync()
    }
    
    func updateEntry(id: UUID, mood: Int, moodType: MoodType, content: String, date: Date) {
        coreDataManager.updateEntry(
            id: id,
            mood: Int16(mood),
            moodType: Int16(moodType.rawValue),
            content: content,
            date: date,
            imageData: nil
        )
        
        loadEntries()
        syncManager.sync()
    }
    
    func deleteEntry(id: UUID) {
        coreDataManager.deleteEntry(id: id)
        loadEntries()
        syncManager.sync()
    }
    
    func getEntries(for date: Date) -> [JournalEntry] {
        return coreDataManager.fetchEntries(for: date)
    }
    
    func syncWithCloud() {
        syncManager.sync()
    }
} 