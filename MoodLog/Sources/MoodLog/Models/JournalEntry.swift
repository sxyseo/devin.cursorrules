import Foundation
import CoreData
#if canImport(UIKit)
import UIKit
#endif

// 注意：这个文件只包含 JournalEntry 的扩展方法
// JournalEntry 类由 CoreData 自动生成

@objc(JournalEntry)
public class JournalEntry: NSManagedObject {
    @NSManaged public var id: UUID?
    @NSManaged public var text: String?
    @NSManaged public var deviceId: String?
    @NSManaged public var lastModified: Date?
    @NSManaged public var date: Date?
    @NSManaged public var mood: Int16
    @NSManaged public var moodType: Int16
    @NSManaged public var syncStatus: Int16
    @NSManaged public var imageData: Data?
}

// 注意：类的扩展方法已移至 JournalEntry+Extensions.swift 