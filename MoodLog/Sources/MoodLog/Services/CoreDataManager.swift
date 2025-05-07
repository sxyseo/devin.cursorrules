import Foundation
import CoreData
#if canImport(UIKit)
import UIKit
#endif

class CoreDataManager {
    static let shared = CoreDataManager()
    
    lazy var container: NSPersistentContainer = {
        let container = NSPersistentContainer(name: "MoodLog")
        container.loadPersistentStores { description, error in
            if let error = error {
                print("Error loading Core Data: \(error)")
            }
        }
        container.viewContext.automaticallyMergesChangesFromParent = true
        return container
    }()
    
    private init() {}
    
    // MARK: - CRUD Operations
    
    func saveEntry(mood: Int16, moodType: Int16, content: String, date: Date, imageData: Data? = nil) -> JournalEntry {
        let context = container.viewContext
        let entry = JournalEntry.create(in: context)
        
        entry.mood = mood
        entry.moodType = moodType
        entry.content = content
        entry.date = date
        entry.imageData = imageData
        entry.syncStatus = SyncStatus.notSynced.rawValue
        
        do {
            try context.save()
        } catch {
            print("Error saving entry: \(error)")
        }
        
        return entry
    }
    
    func updateEntry(id: UUID, mood: Int16, moodType: Int16, content: String, date: Date, imageData: Data? = nil) {
        let context = container.viewContext
        let fetchRequest: NSFetchRequest<JournalEntry> = JournalEntry.fetchRequest()
        fetchRequest.predicate = NSPredicate(format: "id == %@", id as CVarArg)
        
        do {
            let entries = try context.fetch(fetchRequest)
            if let entry = entries.first {
                entry.mood = mood
                entry.moodType = moodType
                entry.content = content
                entry.date = date
                entry.imageData = imageData
                entry.lastModified = Date()
                entry.syncStatus = SyncStatus.notSynced.rawValue
                
                try context.save()
            }
        } catch {
            print("Error updating entry: \(error)")
        }
    }
    
    func deleteEntry(id: UUID) {
        let context = container.viewContext
        let fetchRequest: NSFetchRequest<JournalEntry> = JournalEntry.fetchRequest()
        fetchRequest.predicate = NSPredicate(format: "id == %@", id as CVarArg)
        
        do {
            let entries = try context.fetch(fetchRequest)
            if let entry = entries.first {
                entry.syncStatus = SyncStatus.failed.rawValue
                try context.save()
            }
        } catch {
            print("Error marking entry for deletion: \(error)")
        }
    }
    
    func fetchEntries(for date: Date? = nil) -> [JournalEntry] {
        let context = container.viewContext
        let fetchRequest: NSFetchRequest<JournalEntry> = JournalEntry.fetchRequest()
        
        if let date = date {
            let calendar = Calendar.current
            let startOfDay = calendar.startOfDay(for: date)
            let endOfDay = calendar.date(byAdding: .day, value: 1, to: startOfDay)!
            
            fetchRequest.predicate = NSPredicate(
                format: "date >= %@ AND date < %@ AND syncStatus != %d",
                startOfDay as NSDate,
                endOfDay as NSDate,
                SyncStatus.failed.rawValue
            )
        } else {
            fetchRequest.predicate = NSPredicate(
                format: "syncStatus != %d",
                SyncStatus.failed.rawValue
            )
        }
        
        fetchRequest.sortDescriptors = [NSSortDescriptor(keyPath: \JournalEntry.date, ascending: false)]
        
        do {
            return try context.fetch(fetchRequest)
        } catch {
            print("Error fetching entries: \(error)")
            return []
        }
    }
} 