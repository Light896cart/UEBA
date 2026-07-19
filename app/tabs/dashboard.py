"""Вкладка Дашборд — общая информация о системе"""
import customtkinter as ctk
import os
import json
from datetime import datetime


class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        # Заголовок
        self.title = ctk.CTkLabel(
            self,
            text="📊 Дашборд",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title.pack(anchor="w", pady=(0, 20))

        # Карточки со статистикой
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.pack(fill="x", pady=10)
        self.cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="card")

        self.card_data = {}
        cards_info = [
            ("Данные", "data_status", "📥"),
            ("Модель", "model_status", "🧠"),
            ("Порог", "threshold", "⚙️"),
            ("Алертов сегодня", "alerts_today", "🚨"),
        ]

        for i, (title, key, icon) in enumerate(cards_info):
            card = ctk.CTkFrame(self.cards_frame)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

            ctk.CTkLabel(
                card,
                text=f"{icon} {title}",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            ).pack(anchor="w", padx=15, pady=(15, 5))

            value_label = ctk.CTkLabel(
                card,
                text="—",
                font=ctk.CTkFont(size=24, weight="bold")
            )
            value_label.pack(anchor="w", padx=15, pady=(0, 15))

            self.card_data[key] = value_label

        # Блок информации
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.pack(fill="both", expand=True, pady=20)

        ctk.CTkLabel(
            self.info_frame,
            text="ℹ️ Информация о системе",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self.info_text = ctk.CTkTextbox(self.info_frame, height=250, font=ctk.CTkFont(size=13))
        self.info_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Кнопка обновления
        ctk.CTkButton(
            self,
            text="🔄 Обновить статистику",
            command=self.refresh_stats,
            height=40
        ).pack(anchor="e", pady=(0, 10))

    def refresh_stats(self):
        """Обновление статистики"""
        # Проверяем наличие данных
        if os.path.exists("data/ueba_training_data.csv"):
            import pandas as pd
            df = pd.read_csv("data/ueba_training_data.csv")
            self.card_data["data_status"].configure(
                text=f"✅ {len(df)} строк",
                text_color="#2ecc71"
            )
        else:
            self.card_data["data_status"].configure(
                text="❌ Нет данных",
                text_color="#e74c3c"
            )

        # Проверяем модель
        if os.path.exists("artifacts/ueba_autoencoder.pth"):
            self.card_data["model_status"].configure(
                text="✅ Обучена",
                text_color="#2ecc71"
            )
        else:
            self.card_data["model_status"].configure(
                text="❌ Не обучена",
                text_color="#e74c3c"
            )

        # Порог
        if os.path.exists("artifacts/threshold.json"):
            with open("artifacts/threshold.json") as f:
                data = json.load(f)
            self.card_data["threshold"].configure(
                text=f"{data['threshold']:.6f}"
            )
        else:
            self.card_data["threshold"].configure(text="—")

        # Алерты (заглушка, потом подключим к логам)
        self.card_data["alerts_today"].configure(text="0")

        # Информация
        self.info_text.delete("1.0", "end")
        info = f"""
UEBA ML Project v1.0
Программный макет для обнаружения аномальной активности

Архитектура:
  • Модель: Автоэнкодер (PyTorch)
  • Признаки: 12 поведенческих метрик
  • Порог: Mean + 3*Std от MSE

Этапы работы:
  1. Сбор данных (collector.py)
  2. Нормализация (MinMaxScaler)
  3. Обучение Автоэнкодера
  4. Непрерывный мониторинг с ИБ-классификацией

Время последнего обновления: {datetime.now().strftime("%H:%M:%S")}
        """.strip()
        self.info_text.insert("1.0", info)