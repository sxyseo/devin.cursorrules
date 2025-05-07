import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

struct JournalEntryCard: View {
    let entry: JournalEntry
    @State private var showDetailView = false
    
    var body: some View {
        Button(action: {
            showDetailView = true
        }) {
            VStack(alignment: .leading, spacing: 12) {
                // 时间和心情
                HStack {
                    Text(formattedTime(from: entry.date ?? Date()))
                        .font(.headline)
                        .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                    
                    Spacer()
                    
                    // 心情颜色指示器
                    HStack(spacing: 8) {
                        Circle()
                            .fill(getMoodColor(mood: Int(entry.mood)))
                            .frame(width: 12, height: 12)
                        
                        Text(getMoodName(mood: Int(entry.mood)))
                            .font(.subheadline)
                            .foregroundColor(.gray)
                    }
                }
                
                // 日记内容预览
                Text(entry.content)
                    .font(.body)
                    .foregroundColor(.primary)
                    .lineLimit(3)
                    .multilineTextAlignment(.leading)
                
                // 如果有图片，显示图片
                #if canImport(UIKit)
                if let image = entry.uiImage {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFill()
                        .frame(height: 150)
                        .frame(maxWidth: .infinity)
                        .clipped()
                        .cornerRadius(8)
                }
                #endif
            }
            .padding()
            .background(Color(UIColor.secondarySystemBackground))
            .cornerRadius(12)
            .shadow(color: Color.black.opacity(0.1), radius: 5, x: 0, y: 2)
        }
        .buttonStyle(PlainButtonStyle())
        .sheet(isPresented: $showDetailView) {
            JournalEntryDetailView(entry: entry)
        }
    }
    
    // MARK: - Helper Methods
    
    private func getMoodName(mood: Int) -> String {
        switch mood {
        case 0:
            return "Awful".localized
        case 1:
            return "Bad".localized
        case 2:
            return "Okay".localized
        case 3:
            return "Good".localized
        case 4:
            return "Awesome".localized
        default:
            return "Unknown".localized
        }
    }
    
    private func getMoodColor(mood: Int) -> Color {
        switch mood {
        case 0:
            return .indigo  // 糟糕
        case 1:
            return .blue    // 不好
        case 2:
            return .green   // 一般
        case 3:
            return .orange  // 不错
        case 4:
            return .yellow  // 超棒
        default:
            return .gray
        }
    }
    
    private func formattedTime(from date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        formatter.locale = Locale(identifier: LocalizationHelper.shared.currentLanguage)
        return formatter.string(from: date)
    }
} 