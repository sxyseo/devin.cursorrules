// Models/MoodType.swift 文件已留空
// 内容已移至ContentView.swift中，以解决重复定义问题
// 后期重新组织代码时可以恢复此文件

import Foundation
import SwiftUI

enum MoodType: Int16, CaseIterable, Identifiable {
    case happy = 0
    case sad = 1
    case angry = 2
    case anxious = 3
    case calm = 4
    case excited = 5
    case tired = 6
    case neutral = 7
    
    var id: Int16 { self.rawValue }
    
    var localizedName: String {
        switch self {
        case .happy:
            return "Happy".localized
        case .sad:
            return "Sad".localized
        case .angry:
            return "Angry".localized
        case .anxious:
            return "Anxious".localized
        case .calm:
            return "Calm".localized
        case .excited:
            return "Excited".localized
        case .tired:
            return "Tired".localized
        case .neutral:
            return "Neutral".localized
        }
    }
    
    var color: Color {
        switch self {
        case .happy:
            return Color(red: 1.0, green: 0.8, blue: 0.0)
        case .sad:
            return Color(red: 0.3, green: 0.5, blue: 0.8)
        case .angry:
            return Color(red: 0.8, green: 0.2, blue: 0.2)
        case .anxious:
            return Color(red: 0.6, green: 0.4, blue: 0.8)
        case .calm:
            return Color(red: 0.4, green: 0.8, blue: 0.6)
        case .excited:
            return Color(red: 1.0, green: 0.4, blue: 0.4)
        case .tired:
            return Color(red: 0.6, green: 0.6, blue: 0.6)
        case .neutral:
            return Color(red: 0.7, green: 0.7, blue: 0.7)
        }
    }
}
