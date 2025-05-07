import SwiftUI
#if os(iOS)
import UIKit
#endif

struct MoodSelector: View {
    @Binding var selectedMood: Int
    
    private let moods: [(value: Int, name: String, icon: String, color: Color)] = [
        (0, "Awful".localized, "😖", .indigo),
        (1, "Bad".localized, "😔", .blue),
        (2, "Okay".localized, "😐", .green),
        (3, "Good".localized, "😀", .orange),
        (4, "Awesome".localized, "😄", .yellow)
    ]
    
    var body: some View {
        VStack(spacing: 10) {
            Text("How are you feeling?".localized)
                .font(.headline)
                .foregroundColor(Color(red: 0.3, green: 0.3, blue: 0.3))
            
            HStack(spacing: 15) {
                ForEach(moods, id: \.value) { mood in
                    Button(action: {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.6)) {
                            selectedMood = mood.value
                        }
                    }) {
                        VStack(spacing: 6) {
                            Text(mood.icon)
                                .font(.system(size: 32))
                                .frame(width: 50, height: 50)
                                .background(selectedMood == mood.value ? mood.color.opacity(0.5) : Color.gray.opacity(0.1))
                                .cornerRadius(25)
                                .overlay(
                                    Circle()
                                        .stroke(selectedMood == mood.value ? mood.color : Color.clear, lineWidth: 2)
                                )
                            
                            Text(mood.name)
                                .font(.caption)
                                .foregroundColor(selectedMood == mood.value ? mood.color : Color.gray)
                        }
                    }
                    .scaleEffect(selectedMood == mood.value ? 1.1 : 1.0)
                }
            }
        }
        .padding(.vertical, 5)
    }
} 