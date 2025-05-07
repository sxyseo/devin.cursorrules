import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

struct JournalEntryDetailView: View {
    let entry: JournalEntry
    @Environment(\.presentationMode) var presentationMode
    @EnvironmentObject var journalStore: JournalEntryStore
    @State private var showingDeleteAlert = false
    @State private var showingEditView = false
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // 日期和时间
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(formattedDate(from: entry.date ?? Date()))
                                .font(.headline)
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            
                            Text(formattedWeekday(from: entry.date ?? Date()))
                                .font(.subheadline)
                                .foregroundColor(.gray)
                        }
                        
                        Spacer()
                        
                        // 编辑和删除按钮
                        HStack(spacing: 16) {
                            Button(action: {
                                showingEditView = true
                            }) {
                                Image(systemName: "pencil")
                                    .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            }
                            
                            Button(action: {
                                showingDeleteAlert = true
                            }) {
                                Image(systemName: "trash")
                                    .foregroundColor(.red)
                            }
                        }
                    }
                    .padding(.horizontal)
                    
                    // 心情指示器
                    HStack {
                        Circle()
                            .fill(getMoodColor(mood: Int(entry.mood)))
                            .frame(width: 16, height: 16)
                        
                        Text(getMoodName(mood: Int(entry.mood)))
                            .font(.headline)
                            .foregroundColor(.primary)
                        
                        Spacer()
                        
                        Text(formattedTime(from: entry.date ?? Date()))
                            .font(.subheadline)
                            .foregroundColor(.gray)
                    }
                    .padding(.horizontal)
                    
                    Divider()
                        .padding(.horizontal)
                    
                    // 如果有图片，显示图片
                    #if canImport(UIKit)
                    if let image = entry.uiImage {
                        Image(uiImage: image)
                            .resizable()
                            .scaledToFit()
                            .frame(maxWidth: .infinity)
                            .cornerRadius(12)
                            .padding(.horizontal)
                    }
                    #endif
                    
                    // 日记内容
                    Text(entry.content)
                        .font(.body)
                        .padding()
                        .background(Color(UIColor.secondarySystemBackground))
                        .cornerRadius(12)
                        .shadow(color: Color.black.opacity(0.1), radius: 5, x: 0, y: 2)
                        .padding(.horizontal)
                    
                    Spacer()
                }
                .padding(.vertical)
            }
            .navigationBarTitle("Entry Details".localized, displayMode: .inline)
            .navigationBarItems(leading: Button(action: {
                presentationMode.wrappedValue.dismiss()
            }) {
                Text("Close".localized)
            })
            .alert(isPresented: $showingDeleteAlert) {
                Alert(
                    title: Text("Delete Entry".localized),
                    message: Text("Are you sure you want to delete this entry?".localized),
                    primaryButton: .destructive(Text("Delete".localized)) {
                        if let id = entry.id {
                            journalStore.deleteEntry(id: id)
                            presentationMode.wrappedValue.dismiss()
                        }
                    },
                    secondaryButton: .cancel()
                )
            }
            .sheet(isPresented: $showingEditView) {
                JournalEntryEditorView(isPresented: $showingEditView, editingEntry: entry)
            }
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
            return .indigo
        case 1:
            return .blue
        case 2:
            return .green
        case 3:
            return .orange
        case 4:
            return .yellow
        default:
            return .gray
        }
    }
    
    private func formattedDate(from date: Date) -> String {
        let formatter = DateFormatter()
        if LocalizationHelper.shared.currentLanguage.starts(with: "zh") {
            formatter.dateFormat = "yyyy年MM月dd日"
        } else if LocalizationHelper.shared.currentLanguage.starts(with: "ja") {
            formatter.dateFormat = "yyyy年MM月dd日"
        } else {
            formatter.dateFormat = "MMMM dd, yyyy"
        }
        formatter.locale = Locale(identifier: LocalizationHelper.shared.currentLanguage)
        return formatter.string(from: date)
    }
    
    private func formattedWeekday(from date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEEE"
        formatter.locale = Locale(identifier: LocalizationHelper.shared.currentLanguage)
        return formatter.string(from: date)
    }
    
    private func formattedTime(from date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        formatter.locale = Locale(identifier: LocalizationHelper.shared.currentLanguage)
        return formatter.string(from: date)
    }
} 