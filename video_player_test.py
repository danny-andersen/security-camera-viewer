#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path

from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, pyqtSlot, QUrl, QSizeF
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QStackedWidget,
    QToolBar, QAction, QFileIconProvider, QListWidget, QListWidgetItem,
    QGridLayout, QLabel, QScrollArea, QToolButton, QVBoxLayout, QHBoxLayout,
    QMessageBox
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem


# ---- Configure Dropbox root path and token ----
DROPBOX_ACCESS_TOKEN = os.environ.get("DROPBOX_ACCESS_TOKEN", "PASTE_YOUR_TOKEN_HERE")
DROPBOX_ROOT_PATH = "/motion_images"  

# Optional: lazy import for better startup feedback
try:
    import dropbox
    from dropbox.files import FileMetadata, FolderMetadata
except ImportError:
    dropbox = None

class VideoView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.video_item = QGraphicsVideoItem()
        self.scene.addItem(self.video_item)

        # Initial size
        self.video_item.setSize(QSizeF(self.viewport().size()))

        # Styling
        self.setStyleSheet("background-color: black;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.NoFrame)

    def resizeEvent(self, event):
        # Resize video item to fill viewport
        self.video_item.setSize(QSizeF(self.viewport().size()))
        super().resizeEvent(event)

# ---------- Worker threads for Dropbox operations ----------

class DropboxListWorker(QThread):
    """Lists folders or files in a Dropbox path."""
    listed = pyqtSignal(str, list, str)  # path, entries, error

    def __init__(self, dbx, path, list_folders_only=False, parent=None):
        super().__init__(parent)
        self.dbx = dbx
        self.path = path
        self.list_folders_only = list_folders_only

    def run(self):
        try:
            res = self.dbx.files_list_folder(self.path)
            entries = []
            for e in res.entries:
                if isinstance(e, FolderMetadata):
                    entries.append(("folder", e.name, e.path_lower))
                elif isinstance(e, FileMetadata):
                    if self.list_folders_only:
                        continue
                    entries.append(("file", e.name, e.path_lower))
            self.listed.emit(self.path, entries, "")
        except Exception as e:
            self.listed.emit(self.path, [], str(e))


class DropboxDownloadWorker(QThread):
    """Downloads a Dropbox file to a local temp path."""
    downloaded = pyqtSignal(str, str, str)  # dropbox_path, local_path, error

    def __init__(self, dbx, dropbox_path, target_dir=None, parent=None):
        super().__init__(parent)
        self.dbx = dbx
        self.dropbox_path = dropbox_path
        self.target_dir = target_dir or tempfile.gettempdir()

    def run(self):
        try:
            # Derive a safe local filename
            name = Path(self.dropbox_path).name
            local_path = os.path.join(self.target_dir, name)
            # Ensure uniqueness
            base = local_path
            i = 1
            while os.path.exists(local_path):
                stem = Path(base).stem
                suffix = Path(base).suffix
                local_path = os.path.join(self.target_dir, f"{stem}_{i}{suffix}")
                i += 1

            with open(local_path, "wb") as f:
                self.dbx.files_download_to_file(f.name, self.dropbox_path)
            self.downloaded.emit(self.dropbox_path, local_path, "")
        except Exception as e:
            self.downloaded.emit(self.dropbox_path, "", str(e))

# ---------- UI components ----------

class DropboxFolderGridView(QWidget):
    """Grid of folder icons; emits a signal when a folder is clicked."""
    folderClicked = pyqtSignal(str)  # path_lower

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(16)
        self.grid.setContentsMargins(16, 16, 16, 16)
        self.scroll.setWidget(self.container)

        layout = QVBoxLayout(self)
        layout.addWidget(self.scroll)

        # Icon for folders using system icon provider
        self.icon_provider = QFileIconProvider()
        self.folder_icon = self.icon_provider.icon(QFileIconProvider.Folder)

    def setFolders(self, folders):
        # folders: list of tuples (name, path_lower)
        # Clear grid
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        # Populate grid
        cols = 4
        row, col = 0, 0
        for name, path in folders:
            btn = QToolButton()
            btn.setIcon(self.folder_icon)
            btn.setIconSize(QSize(64, 64))
            btn.setText(name)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setMinimumSize(120, 120)
            btn.clicked.connect(lambda checked=False, p=path: self.folderClicked.emit(p))

            self.grid.addWidget(btn, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1


class DropboxFileListView(QWidget):
    """List of files with simple icons. Emits fileClicked(path_lower) on click."""
    fileClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.itemActivated.connect(self.onActivated)
        self.list.itemClicked.connect(self.onActivated)
        layout.addWidget(self.list)

        self.icon_provider = QFileIconProvider()
        self.file_icon = self.icon_provider.icon(QFileIconProvider.File)
        self.video_icon = QIcon.fromTheme("video-x-generic") or self.file_icon
        self.doc_icon = QIcon.fromTheme("text-x-generic") or self.file_icon

    def setFiles(self, files):
        # files: list of tuples (name, path_lower)
        self.list.clear()
        for name, path in files:
            ext = Path(name).suffix.lower()
            if ext in (".mp4", ".mpeg", ".mpg", ".m4v"):
                icon = self.video_icon
            elif ext in (".txt", ".md", ".pdf", ".doc", ".docx"):
                icon = self.doc_icon
            else:
                icon = self.file_icon
            item = QListWidgetItem(icon, name)
            item.setData(Qt.UserRole, path)
            self.list.addItem(item)

    def onActivated(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self.fileClicked.emit(path)

# ---------- Main window ----------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        if dropbox is None:
            QMessageBox.critical(self, "Missing dependency",
                                 "The 'dropbox' package is required. Install with: pip install dropbox")
            sys.exit(1)

        if not DROPBOX_ACCESS_TOKEN or DROPBOX_ACCESS_TOKEN == "PASTE_YOUR_TOKEN_HERE":
            QMessageBox.critical(self, "Access token required",
                                 "Set DROPBOX_ACCESS_TOKEN env var or edit the code to provide your token.")
            sys.exit(1)

        self.dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

        self.setWindowTitle("Dropbox Browser")
        self.setMinimumSize(1024, 600)

        # Stacked views: folders -> files -> video
        self.stack = QStackedWidget()
        self.folderView = DropboxFolderGridView()
        self.fileView = DropboxFileListView()
        # self.videoWidget = QVideoWidget()
        # self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        # self.mediaPlayer.setVideoOutput(self.videoWidget)

        self.stack.addWidget(self.folderView)  # index 0
        self.stack.addWidget(self.fileView)    # index 1
        self.stack.addWidget(self.videoWidget) # index 2
        self.setCentralWidget(self.stack)

        # Toolbar
        tb = QToolBar("Navigation")
        tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, tb)
        self.actionBack = QAction("Back", self)
        self.actionBack.triggered.connect(self.onBack)
        tb.addAction(self.actionBack)

        self.actionToggleFullscreen = QAction("Fullscreen", self)
        self.actionToggleFullscreen.setCheckable(True)
        self.actionToggleFullscreen.setChecked(True)
        self.actionToggleFullscreen.triggered.connect(self.toggleFullscreen)
        tb.addAction(self.actionToggleFullscreen)

        # Connections
        self.folderView.folderClicked.connect(self.openFolder)
        self.fileView.fileClicked.connect(self.openFile)

        # Keyboard shortcuts
        self.actionBack.setShortcut("Backspace")
        self.actionToggleFullscreen.setShortcut("F11")

        # Start in fullscreen
        self.showFullScreen()

        # Load folders
        self.loadFolders(DROPBOX_ROOT_PATH)

    # ---------- Navigation ----------
    def toggleFullscreen(self, checked):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def onBack(self):
        idx = self.stack.currentIndex()
        if idx == 2:
            # From video -> stop and go to files
            self.mediaPlayer.stop()
            self.stack.setCurrentIndex(1)
        elif idx == 1:
            # From files -> go to folders
            self.stack.setCurrentIndex(0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            # Escape exits video or fullscreen if not in video
            if self.stack.currentIndex() == 2:
                self.mediaPlayer.stop()
                self.stack.setCurrentIndex(1)
            else:
                if self.isFullScreen():
                    self.actionToggleFullscreen.setChecked(False)
                    self.showNormal()
        super().keyPressEvent(event)

    # ---------- Dropbox interactions ----------
    def loadFolders(self, path):
        # Shows only folders at the given path
        self.statusBar().showMessage(f"Loading folders in {path}...")
        worker = DropboxListWorker(self.dbx, path, list_folders_only=True, parent=self)
        worker.listed.connect(self.onFoldersListed)
        worker.start()

    @pyqtSlot(str, list, str)
    def onFoldersListed(self, path, entries, error):
        if error:
            QMessageBox.critical(self, "Dropbox error", error)
            self.statusBar().clearMessage()
            return
        # Transform to (name, path) for folders
        folders = [(name, p) for kind, name, p in entries if kind == "folder"]
        self.folderView.setFolders(folders)
        self.stack.setCurrentIndex(0)
        self.statusBar().clearMessage()

    def openFolder(self, path):
        self.statusBar().showMessage(f"Loading files in {path}...")
        worker = DropboxListWorker(self.dbx, path, list_folders_only=False, parent=self)
        worker.listed.connect(self.onFilesListed)
        worker.start()

    @pyqtSlot(str, list, str)
    def onFilesListed(self, path, entries, error):
        if error:
            QMessageBox.critical(self, "Dropbox error", error)
            self.statusBar().clearMessage()
            return
        files = [(name, p) for kind, name, p in entries if kind == "file"]
        self.fileView.setFiles(files)
        self.stack.setCurrentIndex(1)
        self.statusBar().clearMessage()

    def openFile(self, path):
        name = Path(path).name.lower()
        ext = Path(name).suffix
        is_video = ext.lower() in (".mp4", ".mpeg", ".mpg", ".m4v")
        if is_video:
            self.downloadAndPlay(path)
        else:
            QMessageBox.information(self, "File selected", f"Selected file:\n{path}")

    def downloadAndPlay(self, dropbox_path):
        self.statusBar().showMessage(f"Downloading {dropbox_path}...")
        worker = DropboxDownloadWorker(self.dbx, dropbox_path, parent=self)
        worker.downloaded.connect(self.onDownloaded)
        worker.start()

    @pyqtSlot(str, str, str)
    def onDownloaded(self, dropbox_path, local_path, error):
        self.statusBar().clearMessage()
        if error:
            QMessageBox.critical(self, "Download error", error)
            return
        # Play video
        url = QUrl.fromLocalFile(local_path)
        self.mediaPlayer.setMedia(QMediaContent(url))
        self.stack.setCurrentIndex(2)
        self.videoWidget.setMinimumSize(640, 480)
        self.videoWidget.show()
        self.mediaPlayer.error.connect(lambda e: print("Error:", self.mediaPlayer.errorString()))
        self.mediaPlayer.stateChanged.connect(lambda s: print("State:", s))
        self.mediaPlayer.mediaStatusChanged.connect(lambda s: print("Status:", s))
        self.mediaPlayer.play()
        # Ensure fullscreen video
        if not self.isFullScreen():
            self.showFullScreen()
            self.actionToggleFullscreen.setChecked(True)

            self.view = VideoView(self.fullscreen_widget)
            self.fullscreen_layout.addWidget(self.view)

        self.player = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.view.video_item)
        self.player.setMedia(QMediaContent(QUrl(url)))
        self.fullscreen_layout.addWidget(self.view)

        # Debug signals
        self.player.mediaStatusChanged.connect(lambda s: print("Media status:", s))
        self.player.stateChanged.connect(lambda s: print("Player state:", s))
        self.player.error.connect(lambda e: print("Error:", self.player.errorString()))

# ---------- Entrypoint ----------

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()  # Already fullscreen; keeps window object alive
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
