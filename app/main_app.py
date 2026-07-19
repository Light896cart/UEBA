"""
UEBA ML Project — Десктопное приложение
Главное окно с боковым меню и вкладками
"""
import customtkinter as ctk
from tabs.dashboard import DashboardTab
from tabs.collect_tab import CollectTab
from tabs.train_tab import TrainTab
from tabs.monitor_tab import MonitorTab
from tabs.history_tab import HistoryTab

# Настройки темы
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class UEBAApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Настройки окна
        self.title("UEBA ML Project — Обнаружение аномальной активности")
        self.geometry("1200x750")
        self.minsize(1000, 650)

        # Иконка (опционально)
        # self.iconbitmap("icon.ico")

        # Настройка сетки: sidebar + main area
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ===== SIDEBAR (левое меню) =====
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_rowconfigure(6, weight=1)

        # Логотип/заголовок
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="🛡️ UEBA ML",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.subtitle_label = ctk.CTkLabel(
            self.sidebar,
            text="Анализ поведения",
            font=ctk.CTkFont(size=12)
        )
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Кнопки навигации
        self.nav_buttons = {}
        nav_items = [
            ("📊 Дашборд", "dashboard"),
            ("📥 Сбор данных", "collect"),
            ("🧠 Обучение", "train"),
            ("🔍 Мониторинг", "monitor"),
            ("📜 История", "history"),
        ]

        for i, (text, key) in enumerate(nav_items, start=2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                anchor="w",
                height=40,
                font=ctk.CTkFont(size=14),
                command=lambda k=key: self.show_tab(k)
            )
            btn.grid(row=i, column=0, padx=15, pady=5, sticky="ew")
            self.nav_buttons[key] = btn

        # Статус-бар внизу sidebar
        self.status_label = ctk.CTkLabel(
            self.sidebar,
            text="Статус: Готов",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_label.grid(row=7, column=0, padx=20, pady=20, sticky="s")

        # ===== MAIN AREA (правая часть) =====
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Инициализация вкладок
        self.tabs = {
            "dashboard": DashboardTab(self.main_frame, self),
            "collect": CollectTab(self.main_frame, self),
            "train": TrainTab(self.main_frame, self),
            "monitor": MonitorTab(self.main_frame, self),
            "history": HistoryTab(self.main_frame, self),
        }

        # Показываем дашборд по умолчанию
        self.current_tab = None
        self.show_tab("dashboard")

    def show_tab(self, tab_key):
        """Переключение между вкладками"""
        # Скрываем текущую
        if self.current_tab and self.current_tab in self.tabs:
            self.tabs[self.current_tab].pack_forget()

        # Показываем новую
        self.current_tab = tab_key
        self.tabs[tab_key].pack(fill="both", expand=True, padx=20, pady=20)

        # Подсвечиваем активную кнопку
        for key, btn in self.nav_buttons.items():
            if key == tab_key:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color=("gray70", "gray30"))

    def set_status(self, text, color="gray"):
        """Обновить статус в sidebar"""
        self.status_label.configure(text=f"Статус: {text}", text_color=color)


if __name__ == "__main__":
    app = UEBAApp()
    app.mainloop()