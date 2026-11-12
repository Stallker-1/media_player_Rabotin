import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QListWidgetItem, QComboBox, QMessageBox, QInputDialog, QMenu
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.uic import loadUi
from database.db_manager import DBManager
from playlist_dialog import PlaylistDialog

class MediaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(BASE_DIR, "ui", "main_window.ui")
        loadUi(ui_path, self)

        # Медиаплеер
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(self.volumeSlider.value() / 100)

        self.positionSlider.sliderMoved.connect(self.set_position)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)

        # База данных
        self.db = DBManager()
        self.current_playlist_id = None  # None = все треки

        # Кнопки
        self.playButton.clicked.connect(self.play_pause)
        self.stopButton.clicked.connect(self.stop)
        self.openButton.clicked.connect(self.open_file)
        self.playlistButton.clicked.connect(self.open_playlist_dialog)
        self.volumeSlider.valueChanged.connect(self.set_volume)
        self.nextButton.clicked.connect(self.play_next)
        self.prevButton.clicked.connect(self.play_prev)

        # Список треков
        self.trackList.itemDoubleClicked.connect(self.play_selected)
        
        # Контекстное меню
        self.trackList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.trackList.customContextMenuRequested.connect(self.show_context_menu)

        # Горячие клавиши
        QShortcut(QKeySequence("Space"), self, self.play_pause)
        QShortcut(QKeySequence("Delete"), self, self.delete_selected)
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_file)
        QShortcut(QKeySequence("Ctrl+Right"), self, self.play_next)
        QShortcut(QKeySequence("Ctrl+Left"), self, self.play_prev)

        # Комбобокс плейлистов
        self.playlistCombo = QComboBox()
        self.playlistCombo.addItem("Все треки", None)
        self.playlistCombo.currentIndexChanged.connect(self.on_playlist_changed)
        
        self.verticalLayout.insertWidget(0, self.playlistCombo)

        self.load_playlists()
        self.load_tracks()

    def load_playlists(self):
        """Загружает плейлисты в комбобокс"""
        self.playlistCombo.clear()
        self.playlistCombo.addItem("Все треки", None)
        
        playlists = self.db.get_playlists()
        for p in playlists:
            self.playlistCombo.addItem(p[1], p[0])

    def load_tracks(self):
        """Загружает треки в зависимости от выбора"""
        self.trackList.clear()
        
        if self.current_playlist_id is None:
            # "Все треки" - показываем все треки из базы
            tracks = self.db.get_tracks()
        else:
            # Конкретный плейлист - показываем только треки этого плейлиста
            tracks = self.db.get_tracks_in_playlist(self.current_playlist_id)
        
        for t in tracks:
            item = QListWidgetItem(t[1])  # title
            item.setData(Qt.ItemDataRole.UserRole, {
                'id': t[0],
                'title': t[1],
                'file_path': t[2],
                'duration': t[3]
            })
            self.trackList.addItem(item)
        
        if self.trackList.count() > 0:
            self.trackList.setCurrentRow(0)

    def on_playlist_changed(self):
        """Обработчик смены плейлиста"""
        self.current_playlist_id = self.playlistCombo.currentData()
        self.load_tracks()

    def open_file(self):
        """Открывает файл и добавляет в 'Все треки'"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть медиафайл", "", "Media Files (*.mp3 *.wav *.mp4 *.avi)"
        )
        if file_path:
            title = os.path.basename(file_path)
            
            # Добавляем трек в базу (в "Все треки")
            track_id = self.db.add_track(title, file_path, 0)
            
            # Сразу спрашиваем, добавить ли в плейлист?
            reply = QMessageBox.question(
                self,
                "Добавить в плейлист?",
                f"Добавить трек '{title}' в плейлист?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.add_to_playlist_dialog(track_id, title)
            
            # Обновляем список если мы в "Все треки"
            if self.current_playlist_id is None:
                self.load_tracks()
            
            # Автовоспроизведение если список был пуст
            if self.trackList.count() == 1:
                url = QUrl.fromLocalFile(file_path)
                self.player.setSource(url)
                self.player.play()

    def add_to_playlist_dialog(self, track_id, track_title):
        """Диалог выбора плейлиста для добавления трека"""
        playlists = self.db.get_playlists()
        if not playlists:
            QMessageBox.warning(self, "Ошибка", "Сначала создайте плейлист")
            return
        
        # Получаем плейлисты, в которых еще нет этого трека
        available_playlists = []
        for p in playlists:
            if not self.db.is_track_in_playlist(track_id, p[0]):
                available_playlists.append(p)
        
        if not available_playlists:
            QMessageBox.information(self, "Информация", 
                                  "Трек уже во всех плейлистах")
            return
        
        playlist_names = [p[1] for p in available_playlists]
        
        playlist_name, ok = QInputDialog.getItem(
            self,
            "Выбор плейлиста",
            f"В какой плейлист добавить '{track_title}'?",
            playlist_names,
            0,
            False
        )
        
        if ok and playlist_name:
            # Находим ID плейлиста
            playlist_id = None
            for p in available_playlists:
                if p[1] == playlist_name:
                    playlist_id = p[0]
                    break
            
            if playlist_id:
                self.db.add_track_to_playlist(track_id, playlist_id)
                QMessageBox.information(
                    self,
                    "Успешно",
                    f"Трек '{track_title}' добавлен в плейлист '{playlist_name}'"
                )

    def play_selected(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        file_path = data['file_path']
        url = QUrl.fromLocalFile(file_path)
        self.player.setSource(url)
        self.player.play()

    def play_pause(self):
        item = self.trackList.currentItem()
        if self.player.source().isEmpty():
            if item:
                data = item.data(Qt.ItemDataRole.UserRole)
                url = QUrl.fromLocalFile(data['file_path'])
                self.player.setSource(url)
            else:
                return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop(self):
        self.player.stop()

    def set_position(self, position):
        self.player.setPosition(position)

    def update_position(self, position):
        self.positionSlider.setValue(position)

    def update_duration(self, duration):
        self.positionSlider.setMaximum(duration)

    def set_volume(self, value):
        self.audio_output.setVolume(value / 100)

    def open_playlist_dialog(self):
        dialog = PlaylistDialog()
        dialog.exec()
        self.load_playlists()

    def delete_selected(self):
        """Удаляет выбранный трек"""
        item = self.trackList.currentItem()
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            
            if self.current_playlist_id is None:
                # Удаляем из "Все треки" = удаляем из базы полностью
                reply = QMessageBox.question(
                    self,
                    "Удаление трека",
                    f"Удалить трек '{data['title']}' из базы?\n\n"
                    "Трек будет удален из ВСЕХ плейлистов и из 'Все треки'.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.db.delete_track(data['id'])
                    self.trackList.takeItem(self.trackList.row(item))
            else:
                # Удаляем только из текущего плейлиста
                self.db.remove_track_from_playlist(data['id'], self.current_playlist_id)
                self.trackList.takeItem(self.trackList.row(item))
    
    def play_next(self):
        current_row = self.trackList.currentRow()
        if current_row < self.trackList.count() - 1:
            self.trackList.setCurrentRow(current_row + 1)
            self.play_current()

    def play_prev(self):
        current_row = self.trackList.currentRow()
        if current_row > 0:
            self.trackList.setCurrentRow(current_row - 1)
            self.play_current()

    def play_current(self):
        item = self.trackList.currentItem()
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            url = QUrl.fromLocalFile(data['file_path'])
            self.player.setSource(url)
            self.player.play()

    def show_context_menu(self, position):
        """Контекстное меню для трека"""
        item = self.trackList.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        track_data = item.data(Qt.ItemDataRole.UserRole)
        
        # Основные пункты
        play_action = menu.addAction("▶ Воспроизвести")
        menu.addSeparator()
        
        # Добавление в плейлист
        add_to_playlist_action = menu.addAction("➕ Добавить в плейлист...")
        
        # Удаление из плейлиста (только если мы в плейлисте)
        remove_from_playlist_action = None
        if self.current_playlist_id is not None:
            remove_from_playlist_action = menu.addAction("❌ Удалить из этого плейлиста")
        
        menu.addSeparator()
        
        # Удаление из базы (только если мы в "Все треки")
        delete_from_db_action = None
        if self.current_playlist_id is None:
            delete_from_db_action = menu.addAction("🗑️ Удалить из базы (из всех мест)")
        
        action = menu.exec(self.trackList.mapToGlobal(position))
        
        if action == play_action:
            self.play_selected(item)
        elif action == add_to_playlist_action:
            self.add_to_playlist_dialog(track_data['id'], track_data['title'])
        elif remove_from_playlist_action and action == remove_from_playlist_action:
            self.remove_from_current_playlist(track_data['id'], track_data['title'])
        elif delete_from_db_action and action == delete_from_db_action:
            self.delete_from_database(track_data['id'], track_data['title'])

    def remove_from_current_playlist(self, track_id, track_title):
        """Удаляет трек из текущего плейлиста"""
        self.db.remove_track_from_playlist(track_id, self.current_playlist_id)
        self.trackList.takeItem(self.trackList.currentRow())
        QMessageBox.information(
            self,
            "Успешно",
            f"Трек '{track_title}' удален из плейлиста"
        )

    def delete_from_database(self, track_id, track_title):
        """Удаляет трек из базы полностью"""
        reply = QMessageBox.question(
            self,
            "Удаление трека",
            f"Удалить трек '{track_title}' из базы?\n\n"
            "Трек будет удален из ВСЕХ плейлистов и из 'Все треки'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_track(track_id)
            self.load_tracks()

def main():
    app = QApplication([])
    window = MediaPlayer()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()