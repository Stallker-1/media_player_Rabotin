from PyQt6.QtWidgets import QDialog, QListWidgetItem, QMessageBox
from PyQt6.uic import loadUi
import os
from database.db_manager import DBManager

class PlaylistDialog(QDialog):
    def __init__(self):
        super().__init__()

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(BASE_DIR, "ui", "playlist_dialog.ui")
        loadUi(ui_path, self)

        self.db = DBManager()

        self.load_playlists()

        self.addPlaylistButton.clicked.connect(self.add_playlist)
        self.deletePlaylistButton.clicked.connect(self.delete_playlist)
        self.closeButton.clicked.connect(self.accept)

    def load_playlists(self):
        self.playlistList.clear()
        playlists = self.db.get_playlists()
        for p in playlists:
            item = QListWidgetItem(p[1])
            item.setData(1, p[0])
            self.playlistList.addItem(item)

    def add_playlist(self):
        name = self.playlistNameEdit.text().strip()
        if name:
            self.db.add_playlist(name)
            self.playlistNameEdit.clear()
            self.load_playlists()

    def delete_playlist(self):
        selected = self.playlistList.currentItem()
        if selected:
            playlist_id = selected.data(1)
            playlist_name = selected.text()
            
            # Спрашиваем подтверждение
            reply = QMessageBox.question(
                self, 
                "Удаление плейлиста", 
                f"Удалить плейлист '{playlist_name}'?\nТреки не будут удалены.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.db.delete_playlist(playlist_id)
                self.load_playlists()