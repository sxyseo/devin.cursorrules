//import Foundation
//import CoreData
//
//struct PersistenceController {
//    // 单例模式
//    static let shared = PersistenceController()
//
//    // 预览环境的实例
//    static var preview: PersistenceController = {
//        let controller = PersistenceController(inMemory: true)
//
//        /*
//        // 创建10个示例数据
//        for dayOffset in 0..<10 {
//            let newEntry = JournalEntry(context: controller.container.viewContext)
//            newEntry.id = UUID()
//            newEntry.content = "这是第\(dayOffset + 1)天的日记内容。今天过得很充实！"
//            newEntry.title = "日记 \(dayOffset + 1)"
//            newEntry.createdAt = Calendar.current.date(byAdding: .day, value: -dayOffset, to: Date())
//            newEntry.updatedAt = newEntry.createdAt
//            newEntry.moodRawValue = Int16(dayOffset % 5) // 循环使用不同的心情类型
//            newEntry.moodScore = Double.random(in: 0.3...0.9) // 随机心情分数
//        }
//
//        do {
//            try controller.container.viewContext.save()
//        } catch {
//            print("Error creating preview data: \(error)")
//        }
//        */
//
//        return controller
//    }()
//
//    // CoreData容器
//    let container: NSPersistentContainer
//
//    // 初始化方法
//    init(inMemory: Bool = false) {
//        container = NSPersistentContainer(name: "MoodLog")
//
//        if inMemory {
//            container.persistentStoreDescriptions.first?.url = URL(fileURLWithPath: "/dev/null")
//        }
//
//        container.loadPersistentStores { description, error in
//            if let error = error {
//                fatalError("加载CoreData存储失败: \(error.localizedDescription)")
//            }
//        }
//
//        // 合并策略
//        container.viewContext.mergePolicy = NSMergeByPropertyObjectTrumpMergePolicy
//        container.viewContext.automaticallyMergesChangesFromParent = true
//    }
//
//    // 保存上下文
//    func save() {
//        let context = container.viewContext
//        if context.hasChanges {
//            do {
//                try context.save()
//            } catch {
//                print("保存上下文失败: \(error)")
//            }
//        }
//    }
//}
