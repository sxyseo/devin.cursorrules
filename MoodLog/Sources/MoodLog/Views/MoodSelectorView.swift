import SwiftUI
#if os(iOS)
import UIKit
#endif

struct MoodSelectorView: View {
    @Binding var selectedMood: Int
    
    private let moods = [
        (emoji: "😭", name: "Terrible".localized),
        (emoji: "😢", name: "Sad".localized),
        (emoji: "😐", name: "Neutral".localized),
        (emoji: "😊", name: "Happy".localized),
        (emoji: "😄", name: "Great".localized)
    ]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("How are you feeling?".localized)
                .font(.headline)
                .foregroundColor(Color(red: 0.3, green: 0.3, blue: 0.3))
            
            HStack(spacing: 20) {
                ForEach(0..<moods.count, id: \.self) { index in
                    Button(action: {
                        selectedMood = index
                    }) {
                        VStack(spacing: 8) {
                            Text(moods[index].emoji)
                                .font(.system(size: 32))
                            
                            Text(moods[index].name)
                                .font(.caption)
                                .foregroundColor(selectedMood == index ? .white : Color(red: 0.3, green: 0.3, blue: 0.3))
                        }
                        .frame(width: 60, height: 80)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(selectedMood == index ? Color(red: 0.15, green: 0.35, blue: 0.3) : Color(.secondarySystemBackground))
                        )
                    }
                }
            }
        }
    }
} 