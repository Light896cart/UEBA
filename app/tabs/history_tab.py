"""Вкладка истории обнаруженных аномалий с фильтрацией и экспортом"""
import customtkinter as ctk
import json
import os
import csv
import time
from datetime import datetime

HISTORY_FILE = "data/alerts_history.json"


class HistoryTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.alerts = []
        self.filtered_alerts = []
        self.current_filter = "all"
        self._build_ui()
        self._load_history()

    def _build_ui(self):
        # Заголовок
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            header_frame,
            text="📜 История обнаруженных аномалий",
            font=ctk.CTkFont(size=28, weight="bold")
        ).pack(side="left")

        # Панель управления
        control_frame = ctk.CTkFrame(self)
        control_frame.pack(fill="x", pady=10)

        # Фильтры
        filter_label = ctk.CTkLabel(control_frame, text="🔍 Фильтр:", font=ctk.CTkFont(size=14))
        filter_label.pack(side="left", padx=(15, 10), pady=15)

        self.filter_menu = ctk.CTkOptionMenu(
            control_frame,
            values=[
                "Все",
                "🔴 Майнер/ВПО",
                "🔴 Сканирование сети",
                "🔴 Эксфильтрация",
                "🔴 Шифровальщик",
                "🔴 Ботнет",
                "🟠 Неспецифичная"
            ],
            command=self._apply_filter,
            width=200
        )
        self.filter_menu.pack(side="left", padx=5, pady=15)
        self.filter_menu.set("Все")

        # Поиск
        self.search_entry = ctk.CTkEntry(
            control_frame,
            placeholder_text="🔎 Поиск по описанию...",
            width=250
        )
        self.search_entry.pack(side="left", padx=10, pady=15)
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        # Кнопки справа
        buttons_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        buttons_frame.pack(side="right", padx=15, pady=15)

        ctk.CTkButton(
            buttons_frame,
            text="🔄 Обновить",
            command=self._load_history,
            width=120,
            height=32
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            buttons_frame,
            text="📥 Экспорт CSV",
            command=self._export_csv,
            width=120,
            height=32,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            buttons_frame,
            text="🗑️ Очистить",
            command=self._clear_history,
            width=120,
            height=32,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=5)

        # Статистика
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="x", pady=10)

        self.stats_labels = {}
        stats_info = [
            ("Всего алертов", "total", "📊"),
            ("Майнер/ВПО", "miner", "⛏️"),
            ("Сканирование", "scan", "🔍"),
            ("Эксфильтрация", "exfil", "📤"),
            ("Шифровальщик", "ransom", "🔒"),
            ("Другое", "other", "❓"),
        ]

        stats_frame.grid_columnconfigure(tuple(range(len(stats_info))), weight=1)

        for i, (title, key, icon) in enumerate(stats_info):
            card = ctk.CTkFrame(stats_frame)
            card.grid(row=0, column=i, padx=5, pady=10, sticky="nsew")

            ctk.CTkLabel(
                card,
                text=f"{icon} {title}",
                font=ctk.CTkFont(size=11),
                text_color="gray"
            ).pack(pady=(10, 2))

            value_label = ctk.CTkLabel(
                card,
                text="0",
                font=ctk.CTkFont(size=20, weight="bold")
            )
            value_label.pack(pady=(0, 10))

            self.stats_labels[key] = value_label

        # Основная область — список алертов
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, pady=10)

        # Пустое состояние
        self.empty_label = ctk.CTkLabel(
            self.scroll_frame,
            text="📭 История пуста. Запустите мониторинг для обнаружения аномалий.",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        self.empty_label.pack(pady=100)

    def _load_history(self):
        """Загрузка истории из файла"""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.alerts = json.load(f)
            except Exception as e:
                print(f"[ERROR] Не удалось загрузить историю: {e}")
                self.alerts = []
        else:
            self.alerts = []

        self._apply_filter()
        self._update_stats()

    def _apply_filter(self, value=None):
        """Применение фильтра"""
        filter_value = self.filter_menu.get()
        search_text = self.search_entry.get().lower()

        # Фильтрация по типу
        if filter_value == "Все":
            self.filtered_alerts = self.alerts
        else:
            keyword_map = {
                "🔴 Майнер/ВПО": ["майнер", "впо", "miner"],
                "🔴 Сканирование сети": ["сканирование", "scan"],
                "🔴 Эксфильтрация": ["эксфильтрация", "exfil"],
                "🔴 Шифровальщик": ["шифровальщик", "ransom"],
                "🔴 Ботнет": ["ботнет", "botnet"],
                "🟠 Неспецифичная": ["неспецифичная", "неспециф"],
            }
            keywords = keyword_map.get(filter_value, [])
            self.filtered_alerts = [
                a for a in self.alerts
                if any(kw in a.get('threat', '').lower() for kw in keywords)
            ]

        # Фильтрация по поиску
        if search_text:
            self.filtered_alerts = [
                a for a in self.filtered_alerts
                if search_text in a.get('threat', '').lower() or
                   search_text in a.get('time', '').lower() or
                   search_text in str(a.get('score', '')).lower()
            ]

        self._render_alerts()

    def _render_alerts(self):
        """Отрисовка списка алертов"""
        # Очистка
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not self.filtered_alerts:
            ctk.CTkLabel(
                self.scroll_frame,
                text="📭 Нет алертов по выбранным фильтрам",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            ).pack(pady=50)
            return

        # Сортировка: новые сверху
        sorted_alerts = sorted(self.filtered_alerts, key=lambda x: x.get('time', ''), reverse=True)

        for alert in sorted_alerts:
            self._create_alert_card(alert)

    def _create_alert_card(self, alert):
        """Создание карточки алерта"""
        # Определяем цвет по типу угрозы
        threat = alert.get('threat', '')
        if 'майнер' in threat.lower() or 'впо' in threat.lower():
            color = "#e74c3c"
            icon = "⛏️"
        elif 'сканирование' in threat.lower():
            color = "#e67e22"
            icon = "🔍"
        elif 'эксфильтрация' in threat.lower():
            color = "#9b59b6"
            icon = "📤"
        elif 'шифровальщик' in threat.lower():
            color = "#c0392b"
            icon = "🔒"
        elif 'ботнет' in threat.lower():
            color = "#d35400"
            icon = "🤖"
        else:
            color = "#f39c12"
            icon = "⚠️"

        card = ctk.CTkFrame(self.scroll_frame)
        card.pack(fill="x", padx=5, pady=5)

        # Верхняя строка: время + score
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            top_row,
            text=f"{icon}  {alert.get('time', '—')}",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        score = alert.get('score', 0)
        score_color = "#e74c3c" if score > 0.1 else "#f39c12" if score > 0.05 else "#3498db"
        ctk.CTkLabel(
            top_row,
            text=f"Score: {score:.6f}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=score_color
        ).pack(side="right")

        # Тип угрозы
        ctk.CTkLabel(
            card,
            text=threat,
            font=ctk.CTkFont(size=13),
            text_color=color,
            wraplength=800,
            justify="left"
        ).pack(anchor="w", padx=15, pady=5)

        # Детали (если есть)
        if 'details' in alert and alert['details']:
            details_text = "\n".join([f"  • {k}: {v}" for k, v in alert['details'].items()])
            ctk.CTkLabel(
                card,
                text=details_text,
                font=ctk.CTkFont(size=11),
                text_color="gray",
                justify="left"
            ).pack(anchor="w", padx=15, pady=(0, 10))
        else:
            ctk.CTkFrame(card, height=5, fg_color="transparent").pack(pady=2)

    def _update_stats(self):
        """Обновление статистики"""
        total = len(self.alerts)
        miner = sum(
            1 for a in self.alerts if 'майнер' in a.get('threat', '').lower() or 'впо' in a.get('threat', '').lower())
        scan = sum(1 for a in self.alerts if 'сканирование' in a.get('threat', '').lower())
        exfil = sum(1 for a in self.alerts if 'эксфильтрация' in a.get('threat', '').lower())
        ransom = sum(1 for a in self.alerts if 'шифровальщик' in a.get('threat', '').lower())
        other = total - miner - scan - exfil - ransom

        self.stats_labels['total'].configure(text=str(total))
        self.stats_labels['miner'].configure(text=str(miner))
        self.stats_labels['scan'].configure(text=str(scan))
        self.stats_labels['exfil'].configure(text=str(exfil))
        self.stats_labels['ransom'].configure(text=str(ransom))
        self.stats_labels['other'].configure(text=str(other))

    def _export_csv(self):
        """Экспорт истории в CSV"""
        if not self.alerts:
            return

        filename = f"alerts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['time', 'score', 'threat', 'details'])
                writer.writeheader()
                for alert in self.alerts:
                    row = alert.copy()
                    if 'details' in row and isinstance(row['details'], dict):
                        row['details'] = json.dumps(row['details'], ensure_ascii=False)
                    writer.writerow(row)

            self.app.set_status(f"Экспортировано в {filename}", "#2ecc71")
        except Exception as e:
            self.app.set_status(f"Ошибка экспорта: {e}", "#e74c3c")

    def _clear_history(self):
        """Очистка истории"""
        dialog = ctk.CTkInputDialog(
            text="Введите 'DELETE' для подтверждения очистки:",
            title="Подтверждение очистки"
        )
        result = dialog.get_input()

        if result == "DELETE":
            self.alerts = []
            self._save_history()
            self._apply_filter()
            self._update_stats()
            self.app.set_status("История очищена", "#2ecc71")

    def _save_history(self):
        """Сохранение истории в файл"""
        os.makedirs("data", exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.alerts, f, ensure_ascii=False, indent=2)

    def add_alert(self, alert_data):
        """Добавление нового алерта (вызывается из monitor_tab)"""
        self.alerts.append(alert_data)
        self._save_history()
        # Если вкладка активна — обновляем
        if self.app.current_tab == "history":
            self._apply_filter()
            self._update_stats()