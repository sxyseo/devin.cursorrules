import SwiftUI
import CoreData
#if canImport(UIKit)
import UIKit
#endif

struct TimelineView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var journalStore: JournalEntryStore
    @State private var showingNewEntrySheet = false
    @State private var showingDatePicker = false
    @State private var weekDates: [Date] = []
    @State private var entries: [JournalEntry] = []
    @State private var forceRefresh = false
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // 日期选择器
                HStack {
                    Button(action: {
                        showingDatePicker = true
                    }) {
                        Text(dateString(from: appState.selectedDate))
                            .font(.headline)
                            .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                    }
                    .sheet(isPresented: $showingDatePicker) {
                        DatePickerView()
                    }
                    
                    Spacer()
                    
                    Button(action: {
                        showingNewEntrySheet = true
                    }) {
                        Image(systemName: "plus.circle.fill")
                            .font(.title2)
                            .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                    }
                }
                .padding(.horizontal)
                
                // 周视图
                VStack(spacing: 10) {
                    HStack {
                        ForEach(weekDates, id: \.self) { date in
                            VStack(spacing: 8) {
                                Text(dayOfWeek(from: date))
                                    .font(.caption)
                                    .foregroundColor(.gray)
                                
                                Text("\(Calendar.current.component(.day, from: date))")
                                    .font(.system(size: 16, weight: .medium))
                                    .foregroundColor(Calendar.current.isDate(date, inSameDayAs: appState.selectedDate) ? .white : .primary)
                                    .frame(width: 36, height: 36)
                                    .background(
                                        Circle()
                                            .fill(Calendar.current.isDate(date, inSameDayAs: appState.selectedDate) ? Color(red: 0.15, green: 0.35, blue: 0.3) : Color.clear)
                                    )
                            }
                            .onTapGesture {
                                appState.selectedDate = date
                            }
                        }
                    }
                }
                .padding(.vertical, 10)
                .background(Color(UIColor.secondarySystemBackground))
                .cornerRadius(12)
                .padding(.horizontal)
                
                // 日记列表
                LazyVStack(spacing: 15) {
                    ForEach(entries) { entry in
                        JournalEntryCard(entry: entry)
                            .padding(.horizontal)
                    }
                }
                .padding(.vertical)
            }
        }
        .navigationTitle("Timeline".localized)
        .sheet(isPresented: $showingNewEntrySheet) {
            JournalEntryEditorView(isPresented: $showingNewEntrySheet)
        }
        .onAppear {
            updateWeekDates()
            loadEntries()
        }
        .onChange(of: appState.selectedDate) { _, _ in
            updateWeekDates()
            loadEntries()
        }
    }
    
    // MARK: - Helper Methods
    
    private func updateWeekDates() {
        let calendar = Calendar.current
        let sunday = calendar.date(from: calendar.dateComponents([.yearForWeekOfYear, .weekOfYear], from: appState.selectedDate))!
        weekDates = (0..<7).map { calendar.date(byAdding: .day, value: $0, to: sunday)! }
    }
    
    private func loadEntries() {
        entries = journalStore.getEntries(for: appState.selectedDate)
    }
    
    private func dayOfWeek(from date: Date) -> String {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "E"
        dateFormatter.locale = Locale(identifier: LocalizationHelper.shared.currentLanguage)
        return dateFormatter.string(from: date)
    }
    
    private func dateString(from date: Date) -> String {
        let dateFormatter = DateFormatter()
        if LocalizationHelper.shared.currentLanguage.starts(with: "zh") {
            dateFormatter.dateFormat = "yyyy年MM月dd日 EEEE"
        } else if LocalizationHelper.shared.currentLanguage.starts(with: "ja") {
            dateFormatter.dateFormat = "yyyy年MM月dd日 EEEE"
        } else {
            dateFormatter.dateFormat = "MMMM dd, yyyy EEEE"
        }
        dateFormatter.locale = Locale(identifier: LocalizationHelper.shared.currentLanguage)
        return dateFormatter.string(from: date)
    }
} 