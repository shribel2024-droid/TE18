import os
import sys
import sqlite3
import csv
from datetime import datetime

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle

# ==========================================
# 1. EMBEDDED DATABASE MANAGER
# ==========================================
class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    date TEXT NOT NULL,
                    notes TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            conn.commit()

    def add_expense(self, title, amount, category, date, notes):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO expenses (title, amount, category, date, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, float(amount), category, date, notes))
            conn.commit()

    def get_expenses(self, category_filter="All", search_query=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, title, amount, category, date, notes FROM expenses WHERE 1=1"
            params = []

            if category_filter and category_filter != "All":
                query += " AND category = ?"
                params.append(category_filter)

            if search_query:
                query += " AND (title LIKE ? OR notes LIKE ?)"
                params.extend([f"%{search_query}%", f"%{search_query}%"])

            query += " ORDER BY date DESC, id DESC"
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            return [
                {"id": r[0], "title": r[1], "amount": r[2], "category": r[3], "date": r[4], "notes": r[5]}
                for r in rows
            ]

    def delete_expense(self, exp_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM expenses WHERE id = ?", (exp_id,))
            conn.commit()

    def get_category_totals(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
            rows = cursor.fetchall()
            return {r[0]: r[1] for r in rows}

    def get_setting(self, key, default=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def set_setting(self, key, value):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()

    def export_to_csv(self, export_path):
        expenses = self.get_expenses()
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Title", "Amount", "Category", "Date", "Notes"])
            for e in expenses:
                writer.writerow([e["id"], e["title"], e["amount"], e["category"], e["date"], e["notes"]])

# ==========================================
# 2. UI COMPONENTS & WIDGETS
# ==========================================
class BarChartWidget(Widget):
    def update_chart(self, category_data):
        self.canvas.clear()
        if not category_data or self.width < 50 or self.height < 50:
            return

        max_val = max(category_data.values()) if category_data.values() else 1
        num_items = len(category_data)
        padding = 20
        available_width = max(self.width - (padding * 2), 10)
        available_height = max(self.height - (padding * 2), 10)
        bar_width = (available_width / max(num_items, 1)) * 0.6
        spacing = (available_width / max(num_items, 1)) * 0.4

        colors = [
            (0.2, 0.6, 0.86, 1),
            (0.9, 0.3, 0.23, 1),
            (0.18, 0.8, 0.44, 1),
            (0.95, 0.61, 0.07, 1),
            (0.6, 0.35, 0.71, 1)
        ]

        with self.canvas:
            x_pos = self.x + padding
            for idx, (cat, val) in enumerate(category_data.items()):
                bar_height = (val / max_val) * (available_height - 30)
                c = colors[idx % len(colors)]
                Color(*c)
                Rectangle(pos=(x_pos, self.y + padding), size=(bar_width, max(bar_height, 5)))
                x_pos += bar_width + spacing

class EntryScreen(Screen):
    pass

class ListScreen(Screen):
    pass

class ReportsScreen(Screen):
    pass

class SettingsScreen(Screen):
    pass

KV_LAYOUT = """
<EntryScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 16
        spacing: 10

        Label:
            text: "Add New Expense"
            font_size: '22sp'
            size_hint_y: 0.1

        TextInput:
            id: title_in
            hint_text: "Expense Title (e.g. Groceries)"
            multiline: False
            size_hint_y: 0.12

        TextInput:
            id: amount_in
            hint_text: "Amount"
            input_filter: "float"
            multiline: False
            size_hint_y: 0.12

        Spinner:
            id: cat_in
            text: "Food"
            values: ["Food", "Transport", "Bills", "Shopping", "Entertainment", "Other"]
            size_hint_y: 0.12

        TextInput:
            id: date_in
            hint_text: "Date (YYYY-MM-DD)"
            multiline: False
            size_hint_y: 0.12

        TextInput:
            id: notes_in
            hint_text: "Notes (Optional)"
            multiline: True
            size_hint_y: 0.22

        Button:
            text: "Save Entry"
            size_hint_y: 0.12
            on_release: 
                app.save_new_expense(title_in.text, amount_in.text, cat_in.text, date_in.text, notes_in.text)
                title_in.text = ""
                amount_in.text = ""
                notes_in.text = ""

        BoxLayout:
            size_hint_y: 0.1
            spacing: 8
            Button:
                text: "History"
                on_release: root.manager.current = 'list'
            Button:
                text: "Reports"
                on_release: root.manager.current = 'reports'
            Button:
                text: "Settings"
                on_release: root.manager.current = 'settings'

<ListScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 16
        spacing: 8

        Label:
            text: "Expense History"
            font_size: '20sp'
            size_hint_y: 0.08

        BoxLayout:
            size_hint_y: 0.08
            spacing: 8
            TextInput:
                id: search_in
                hint_text: "Search..."
                multiline: False
                on_text: app.refresh_data(filter_cat.text, self.text)
            Spinner:
                id: filter_cat
                text: "All"
                values: ["All", "Food", "Transport", "Bills", "Shopping", "Entertainment", "Other"]
                on_text: app.refresh_data(self.text, search_in.text)

        ScrollView:
            size_hint_y: 0.74
            BoxLayout:
                id: list_container
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: 6

        BoxLayout:
            size_hint_y: 0.1
            spacing: 8
            Button:
                text: "+ Add New"
                on_release: root.manager.current = 'entry'
            Button:
                text: "Reports"
                on_release: root.manager.current = 'reports'
            Button:
                text: "Settings"
                on_release: root.manager.current = 'settings'

<ReportsScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 16
        spacing: 10

        Label:
            text: "Analytics & Breakdown"
            font_size: '20sp'
            size_hint_y: 0.08

        Label:
            id: total_label
            text: "Total Spent: $0.00"
            font_size: '18sp'
            bold: True
            size_hint_y: 0.08

        BarChartWidget:
            id: chart_area
            size_hint_y: 0.74

        BoxLayout:
            size_hint_y: 0.1
            spacing: 8
            Button:
                text: "Back to List"
                on_release: root.manager.current = 'list'

<SettingsScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 16
        spacing: 12

        Label:
            text: "Settings & Backup"
            font_size: '20sp'
            size_hint_y: 0.1

        BoxLayout:
            size_hint_y: 0.15
            spacing: 10
            Label:
                text: "Currency Symbol:"
            Spinner:
                text: app.currency_symbol
                values: ["$", "€", "£", "₹", "¥"]
                on_text: app.set_currency(self.text)

        Button:
            text: "Export Expenses to CSV"
            size_hint_y: 0.15
            on_release: app.export_data()

        Widget:
            size_hint_y: 0.5

        BoxLayout:
            size_hint_y: 0.1
            Button:
                text: "Back to Main"
                on_release: root.manager.current = 'entry'
"""

# ==========================================
# 3. MAIN APPLICATION CLASS
# ==========================================
class ExpenseTrackerApp(App):
    currency_symbol = StringProperty("$")

    def build(self):
        self.title = "Daily Expense Tracker"
        
        # Save DB in app's dedicated internal storage to bypass Android permission limits
        db_path = os.path.join(self.user_data_dir, "expenses.db")
        self.db = DatabaseManager(db_path)
        self.currency_symbol = self.db.get_setting("currency", "$")

        Builder.load_string(KV_LAYOUT)

        sm = ScreenManager()
        sm.add_widget(EntryScreen(name="entry"))
        sm.add_widget(ListScreen(name="list"))
        sm.add_widget(ReportsScreen(name="reports"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm

    def on_start(self):
        Clock.schedule_once(lambda dt: self.refresh_data(), 0.2)

    def refresh_data(self, category_filter="All", search_query=""):
        try:
            list_screen = self.root.get_screen("list")
            container = list_screen.ids.list_container
            container.clear_widgets()

            raw_data = self.db.get_expenses(category_filter, search_query)

            for item in raw_data:
                row = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height='50dp',
                    padding=6,
                    spacing=6
                )

                lbl_box = BoxLayout(orientation='vertical', size_hint_x=0.5)
                lbl_box.add_widget(Label(text=item["title"], bold=True, halign='left', text_size=(200, None)))
                lbl_box.add_widget(Label(text=f"{item['category']} | {item['date']}", font_size='12sp', halign='left', text_size=(200, None)))

                amt_lbl = Label(text=f"{self.currency_symbol}{item['amount']}", bold=True, size_hint_x=0.25)

                btn_del = Button(text="X", size_hint_x=0.15)
                btn_del.bind(on_release=lambda btn, exp_id=item["id"]: self.delete_expense_item(exp_id))

                row.add_widget(lbl_box)
                row.add_widget(amt_lbl)
                row.add_widget(btn_del)

                container.add_widget(row)

            self.update_reports()
        except Exception as e:
            print(f"Refresh error: {e}")

    def save_new_expense(self, title, amount, category, date, notes):
        if not title or not amount:
            return
        try:
            float(amount)
        except ValueError:
            return

        date_str = date if date else datetime.now().strftime("%Y-%m-%d")
        self.db.add_expense(title, amount, category, date_str, notes)
        self.refresh_data()
        self.root.current = "list"

    def delete_expense_item(self, exp_id):
        self.db.delete_expense(exp_id)
        self.refresh_data()

    def update_reports(self):
        try:
            reports_screen = self.root.get_screen("reports")
            totals = self.db.get_category_totals()
            
            total_spent = sum(totals.values())
            reports_screen.ids.total_label.text = f"Total Spent: {self.currency_symbol}{total_spent:.2f}"
            
            chart_widget = reports_screen.ids.chart_area
            chart_widget.update_chart(totals)
        except Exception as e:
            print(f"Report error: {e}")

    def set_currency(self, symbol):
        self.currency_symbol = symbol
        self.db.set_setting("currency", symbol)
        self.refresh_data()

    def export_data(self):
        export_path = os.path.join(self.user_data_dir, "expenses_backup.csv")
        self.db.export_to_csv(export_path)

if __name__ == "__main__":
    ExpenseTrackerApp().run()