import sys
import os
import tempfile
import datetime
from pathlib import Path

from PyQt5.QtGui import QPixmap, QKeyEvent, QMouseEvent
from PyQt5.QtWidgets import (
    QApplication, QWidget, QGridLayout, QVBoxLayout, QScrollArea, QHBoxLayout, QPushButton, QLabel, QSizePolicy, QStackedLayout, QFileIconProvider, QToolButton, QListWidget, QListWidgetItem, QMessageBox, QSlider, QStyle
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, Qt, QTimer, QEvent, QPoint, QSize, QThread, pyqtSignal, pyqtSlot, QSizeF

from PyQt5.QtGui import QIcon

from enum import Enum, auto

import dropbox
from dropbox.files import FileMetadata, FolderMetadata

import resources_rc  # ensures resources are loaded

SOURCE_DIR = "/home/danny/Dropbox/Photos/Bigbertha_backup/"
IMAGE_TIMER = 3000  # 3 seconds

DROPBOX_ACCESS_TOKEN = os.environ.get("DROPBOX_ACCESS_TOKEN", "PASTE_YOUR_TOKEN_HERE")
DROPBOX_ROOT_PATH = "/motion_images"  

class Mode(Enum):
    CAMERA = auto()
    CAMERA_FULLSCREEN = auto()
    PHOTO_FOLDER = auto()
    SLIDESHOW = auto()
    PLAY = auto()
    SECURITY_CAMERA_FOLDER = auto()
    SECURITY_VIDEO = auto()
    
    
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt5.QtCore import QUrl, QTimer, QSizeF

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
        

class VideoPlayerWidget(QWidget):
    def __init__(self, player, parent=None):
        super().__init__(parent)

        self.view = VideoView()
        self.player = player

        # --- Controls ---
        self.playButton = QPushButton("Play")
        self.playButton.setFixedHeight(60)   # ensure visible size
        self.playButton.setFocusPolicy(Qt.StrongFocus)
        self.playButton.setMinimumWidth(240)
        self.playButton.clicked.connect(self.togglePlay)
        self.playButton.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 28px;
                padding: 8px;
            }
            QPushButton:focus {
                border: 2px solid #00ffff;
                background-color: #222;
            }
        """)

        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.setFixedHeight(60)
        self.positionSlider.sliderMoved.connect(self.setPosition)
        
        # Layout for controls
        controlLayout = QHBoxLayout()
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.positionSlider)

        # Main layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        layout.addLayout(controlLayout)

        # Connect signals
        self.player.stateChanged.connect(self.updatePlayButton)
        self.player.positionChanged.connect(self.updatePosition)
        self.player.durationChanged.connect(self.updateDuration)
        self.player.mediaStatusChanged.connect(self.handleMediaStatus)

    def handleMediaStatus(self, status):
        if status == QMediaPlayer.EndOfMedia:
            # Reset pipeline immediately
            current_media = self.player.media()
            self.player.setMedia(current_media)
            self.player.setPosition(0)
                
    def togglePlay(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            # If at end, reload media before playing
            if self.player.mediaStatus() == QMediaPlayer.EndOfMedia:
                current_media = self.player.media()
                self.player.setMedia(current_media)   # reload
                self.player.setPosition(0)
            self.player.play()
        
    def updatePlayButton(self, state):
        if state == QMediaPlayer.PlayingState:
            self.playButton.setText("Pause")
        else:
            self.playButton.setText("Play")

    def updatePosition(self, position):
        self.positionSlider.setValue(position)

    def updateDuration(self, duration):
        self.positionSlider.setRange(0, duration)

    def setPosition(self, position):
        self.player.setPosition(position)
        
# ---------- Dropbox worker threads ----------
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

    def __init__(self, owning_widget, top_row_buttons, parent=None):
        super().__init__(parent)
        self.owning_widget = owning_widget
        self.top_row_buttons = top_row_buttons
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.owning_widget.folder_scroll_area = self.scroll
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

    def parse_date_from_folder(self, name: str):
        """Extract datetime from folder name like YYYY-MM-DD"""
        try:
            return datetime.datetime.strptime(name, "%Y-%m-%d")
        except Exception:
            return datetime.datetime.min  # fallback if parsing fails
    
    def setFolders(self, folders):
        # folders: list of tuples (name, path_lower)
        # Sort descending by date (most recent first)
        folders_sorted = sorted(folders, key=lambda f: self.parse_date_from_folder(f[0]), reverse=True)        

        # Clear grid
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        self.owning_widget.folder_buttons = [self.top_row_buttons]
        
        # Populate grid
        cols = 4
        row, col = 0, 0
        row_buttons = []
        for name, path in folders_sorted:
            btn = QToolButton()
            btn.setIcon(self.folder_icon)
            btn.setIconSize(QSize(64, 64))
            btn.setText(name)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            # Apply white text + 28px font
            btn.setStyleSheet("""
                QToolButton {
                    color: white;
                    font-size: 28px;
                }
                QToolButton:focus {
                    border: 2px solid #00ffff;
                    background-color: #222;
                }
            """)
            btn.setMinimumSize(120, 120)
            btn.clicked.connect(lambda checked=False, p=path: self.folderClicked.emit(p))

            self.grid.addWidget(btn, row, col)
            row_buttons.append(btn)
            col += 1
            if col >= cols:
                self.owning_widget.folder_buttons.append(row_buttons)
                row_buttons = []
                col = 0
                row += 1

        if row_buttons:
            self.owning_widget.folder_buttons.append(row_buttons)


class DropboxFileGridView(QWidget):
    """Grid of files with icons. Video files show parsed date/time labels."""
    fileClicked = pyqtSignal(str)

    def __init__(self, owning_widget, top_row_buttons, parent=None):
        super().__init__(parent)
        self.owning_widget = owning_widget
        self.top_row_buttons = top_row_buttons
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(16)
        self.grid.setContentsMargins(16, 16, 16, 16)
        self.scroll.setWidget(self.container)

        layout = QVBoxLayout(self)
        layout.addWidget(self.scroll)

        # Icons 
        # Provided by Icons 8 <a target="_blank" href="https://icons8.com/icon/35090/video">Video</a> icon by <a target="_blank" href="https://icons8.com">Icons8</a>
        self.icon_provider = QFileIconProvider()
        self.file_icon = self.icon_provider.icon(QFileIconProvider.File)
        # self.video_icon = QIcon.fromTheme("video-x-generic") or self.video_icon = QIcon(":/icons/video.png")
        self.video_icon = QIcon(":/icons/icons/icons8-video-100.png")
        self.doc_icon = QIcon.fromTheme("text-x-generic") or self.file_icon

    def parse_datetime_from_name(self, name: str):
        """Extract datetime from filename like YYYYMMDD'T'HHMISS-cameraname.ext"""
        try:
            stem = Path(name).stem
            datepart = stem.split("-", 1)[0]
            return datetime.datetime.strptime(datepart, "%Y%m%dT%H%M%S")
        except Exception:
            return datetime.datetime.min  # fallback for non-matching names

    def setFiles(self, files):
        files_sorted = sorted(files, key=lambda f: self.parse_datetime_from_name(f[0]), reverse=True)        
        # Clear grid
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        self.owning_widget.folder_buttons = [self.top_row_buttons]

        # Populate grid
        cols = 4
        row, col = 0, 0
        row_buttons = []
        for name, path in files_sorted:
            ext = Path(name).suffix.lower()

            # Decide icon + label
            if ext in (".mp4", ".mpeg", ".mpg", ".m4v"):
                icon = self.video_icon
                label_text = name
                try:
                    stem = Path(name).stem
                    # Split into datepart and camera name
                    datepart, cameraname = stem.split("-", 1)
                    dt = datetime.datetime.strptime(datepart, "%Y%m%dT%H%M%S")
                    # label_text = f"{cameraname} at {dt.strftime('%d %b %Y, %H:%M:%S')}"
                    label_text = f"{cameraname} at {dt.strftime('%H:%M:%S')}"
                except Exception:
                    pass
            elif ext in (".txt", ".md", ".pdf", ".doc", ".docx"):
                icon = self.doc_icon
                label_text = name
            else:
                icon = self.file_icon
                label_text = name

            # Create button
            btn = QToolButton()
            btn.setIcon(icon)
            btn.setIconSize(QSize(64, 64))
            btn.setText(label_text)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setMinimumSize(160, 140)
            btn.setStyleSheet("""
                QToolButton {
                    color: white;
                    font-size: 28px;
                }
            """)
            btn.clicked.connect(lambda checked=False, p=path: self.fileClicked.emit(p))

            self.grid.addWidget(btn, row, col)
            row_buttons.append(btn)
            col += 1
            if col >= cols:
                self.owning_widget.folder_buttons.append(row_buttons)
                row_buttons = []
                col = 0
                row += 1
        if row_buttons:
            self.owning_widget.folder_buttons.append(row_buttons)

    def onActivated(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self.fileClicked.emit(path)

class SecurityVideoWindow(QWidget):
    def __init__(self, owning_widget, parent=None):
        super().__init__(parent)

        self.owning_widget = owning_widget
        self.owning_widget.folder_buttons = []
        
        self.parent_layout = owning_widget.fullscreen_layout


        dropbox_token = self.read_dropbox_token()
        self.dbx = dropbox.Dropbox(dropbox_token)
        owning_widget.mode = Mode.SECURITY_CAMERA_FOLDER

        self.top_row_buttons = []
        # Breadcrumb bar
        breadcrumb_bar = QWidget()
        breadcrumb_layout = QHBoxLayout(breadcrumb_bar)
        breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        breadcrumb_layout.setSpacing(10)
        
        camera_button = QPushButton("Back to All Cameras")
        camera_button.setFocusPolicy(Qt.StrongFocus)
        camera_button.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 28px;
                padding: 8px;
            }
            QPushButton:focus {
                border: 2px solid #00ffff;
                background-color: #222;
            }
        """)
        camera_button.clicked.connect(lambda: self.owning_widget.showCameras())
        self.top_row_buttons.append(camera_button)
        breadcrumb_layout.addWidget(camera_button)

        back_button = QPushButton("Back to Previous Folder")
        back_button.setFocusPolicy(Qt.StrongFocus)
        back_button.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 28px;
                padding: 8px;
            }
            QPushButton:focus {
                border: 2px solid #00ffff;
                background-color: #222;
            }
        """)
        back_button.clicked.connect(lambda: self.onBack())
        breadcrumb_layout.addWidget(back_button)
        self.top_row_buttons.append(back_button)
        
        self.parent_layout.addWidget(breadcrumb_bar)
        self.owning_widget.folder_buttons.append(self.top_row_buttons)
        
        self.folderView = DropboxFolderGridView(self.owning_widget, self.top_row_buttons)
        self.fileView = DropboxFileGridView(self.owning_widget, self.top_row_buttons)
        self.stack = QStackedLayout()

        self.parent_layout.addLayout(self.stack)

        self.stack.addWidget(self.folderView)  # index 0
        self.stack.addWidget(self.fileView)    # index 1
        self.stack.addWidget(self.owning_widget.playerview) # index 2

        # Connections
        self.folderView.folderClicked.connect(self.openFolder)
        self.fileView.fileClicked.connect(self.openFile)

        # Keyboard shortcuts
        # self.actionBack.setShortcut("Backspace")
        # self.actionToggleFullscreen.setShortcut("F11")

        # Start in fullscreen
        # self.showFullScreen()

        camera_button.setFocus()
        # Load folders
        
        self.loadFolders(DROPBOX_ROOT_PATH)

    def read_dropbox_token(self):
        """Read Dropbox auth token from a file."""
        file_path="./dropbox_token.txt"
        try:
            with open(file_path, "r") as f:
                token = f.read().strip()
            return token
        except FileNotFoundError:
            raise RuntimeError(f"Token file not found: {file_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading token: {e}")

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
            self.owning_widget.player.stop()
            self.owning_widget.mode = Mode.SECURITY_CAMERA_FOLDER
            self.stack.setCurrentIndex(1)
        elif idx == 1:
            # From files -> go to folders
            self.stack.setCurrentIndex(0)
        elif idx == 0:
            #Top level, go back to camera grid
            self.owning_widget.showCameras()

    # def keyPressEvent(self, event):
    #     if event.key() == Qt.Key_Escape:
    #         # Escape exits video or fullscreen if not in video
    #         if self.stack.currentIndex() == 2:
    #             self.mediaPlayer.stop()
    #             self.stack.setCurrentIndex(1)
    #         else:
    #             if self.isFullScreen():
    #                 self.actionToggleFullscreen.setChecked(False)
    #                 self.showNormal()
    #     super().keyPressEvent(event)

    # ---------- Dropbox interactions ----------
    def loadFolders(self, path):
        # Shows only folders at the given path
        # self.statusBar().showMessage(f"Loading folders in {path}...")
        worker = DropboxListWorker(self.dbx, path, list_folders_only=True, parent=self)
        worker.listed.connect(self.onFoldersListed)
        worker.start()

    @pyqtSlot(str, list, str)
    def onFoldersListed(self, path, entries, error):
        if error:
            QMessageBox.critical(self, "Dropbox error", error)
            # self.statusBar().clearMessage()
            return
        # Transform to (name, path) for folders
        folders = [(name, p) for kind, name, p in entries if kind == "folder"]
        self.folderView.setFolders(folders)
        self.stack.setCurrentIndex(0)
        # self.statusBar().clearMessage()

    def openFolder(self, path):
        # self.statusBar().showMessage(f"Loading files in {path}...")
        worker = DropboxListWorker(self.dbx, path, list_folders_only=False, parent=self)
        worker.listed.connect(self.onFilesListed)
        worker.start()

    @pyqtSlot(str, list, str)
    def onFilesListed(self, path, entries, error):
        if error:
            QMessageBox.critical(self, "Dropbox error", error)
            # self.statusBar().clearMessage()
            return
        files = [(name, p) for kind, name, p in entries if kind == "file"]
        self.fileView.setFiles(files)
        self.stack.setCurrentIndex(1)
        # self.statusBar().clearMessage()

    def openFile(self, path):
        name = Path(path).name.lower()
        ext = Path(name).suffix
        is_video = ext.lower() in (".mp4", ".mpeg", ".mpg", ".m4v")
        if is_video:
            self.downloadAndPlay(path)
        else:
            QMessageBox.information(self, "File selected", f"Selected file:\n{path}")

    def downloadAndPlay(self, dropbox_path):
        # self.statusBar().showMessage(f"Downloading {dropbox_path}...")
        worker = DropboxDownloadWorker(self.dbx, dropbox_path, parent=self)
        worker.downloaded.connect(self.onDownloaded)
        worker.start()

    @pyqtSlot(str, str, str)
    def onDownloaded(self, dropbox_path, local_path, error):
        # self.statusBar().clearMessage()
        if error:
            QMessageBox.critical(self, "Download error", error)
            return
        # Play video
        url = QUrl.fromLocalFile(local_path)
        self.owning_widget.player.setMedia(QMediaContent(url))
        self.owning_widget.playerview.playButton.setFocus()
        # self.owning_widget.fullscreen_layout.addWidget(self.owning_widget.view)

        QTimer.singleShot(500, self.owning_widget.player.play)
        # self.stack.setCurrentWidget(self.fullscreen_widget)
        self.owning_widget.mode = Mode.SECURITY_VIDEO
        self.stack.setCurrentIndex(2)

        # self.videoWidget.setMinimumSize(640, 480)
        # self.videoWidget.show()
        # self.mediaPlayer.error.connect(lambda e: print("Error:", self.mediaPlayer.errorString()))
        # self.mediaPlayer.stateChanged.connect(lambda s: print("State:", s))
        # self.mediaPlayer.mediaStatusChanged.connect(lambda s: print("Status:", s))
        # self.mediaPlayer.play()
        # # Ensure fullscreen video
        # if not self.isFullScreen():
        #     self.showFullScreen()
        #     self.actionToggleFullscreen.setChecked(True)

        #     self.view = VideoView(self.fullscreen_widget)
        #     self.fullscreen_layout.addWidget(self.view)

        # self.player = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        # self.player.setVideoOutput(self.view.video_item)
        # self.player.setMedia(QMediaContent(QUrl(url)))
        # self.fullscreen_layout.addWidget(self.view)

        # # Debug signals
        # self.player.mediaStatusChanged.connect(lambda s: print("Media status:", s))
        # self.player.stateChanged.connect(lambda s: print("Player state:", s))
        # self.player.error.connect(lambda e: print("Error:", self.player.errorString()))


class WebGrid(QWidget):
    def __init__(self):
        super().__init__()
        self.load_urls("urls.txt")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_image)
        self.mode = Mode.CAMERA  # Track current mode
        self.icon_provider = QFileIconProvider()
        self.breadcrumbs = []  # List of folder names
        self.setWindowTitle("Camera Monitoring")
        self.setStyleSheet("background-color: black;")
        self.stack = QStackedLayout(self)
        self.setLayout(self.stack)

        self.grid_widget = QWidget()
        self.grid_widget.setCursor(Qt.BlankCursor)
        self.stack.addWidget(self.grid_widget)

        self.fullscreen_widget = QWidget()
        self.fullscreen_layout = QVBoxLayout(self.fullscreen_widget)
        self.stack.addWidget(self.fullscreen_widget)

        # Video view and player
        self.player = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        self.playerview = VideoPlayerWidget(self.player)
        self.player.setVideoOutput(self.playerview.view.video_item)

        # Debug signals
        self.player.mediaStatusChanged.connect(lambda s: print("Media status:", s))
        self.player.stateChanged.connect(lambda s: print("Player state:", s))
        self.player.error.connect(lambda e: print("Error:", self.player.errorString()))

        self.init_grid()
        self.stack.setCurrentWidget(self.grid_widget)
        self.showFullScreen()

    # List of URLs to display
    def load_urls(self, filepath):
        self.urls = []  
        self.urlnames = []

        try:
            with open(filepath, "r") as f:
                for line in f:
                    parts = line.strip().split(",", 1)  # Split into 2 parts: name and URL
                    if len(parts) == 2:
                        name, url = parts
                        self.urls.append(url.strip())
                        self.urlnames.append(name)
        except Exception as e:
            print(f"Error loading URLs: {e}")

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Backspace:
            if self.mode in (Mode.PHOTO_FOLDER, Mode.SLIDESHOW, Mode.PLAY):
                self.go_up_one_folder()
                return
            elif self.mode == Mode.CAMERA:
                # In CAMERA mode, set focus to image viewer button
                self.viewer_btn.setFocus()
                return
            elif self.mode == Mode.CAMERA_FULLSCREEN:
                # Go back to grid view
                self.showCameras()
                return
            elif self.mode == Mode.SECURITY_VIDEO or self.mode == Mode.SECURITY_CAMERA_FOLDER:
                self.security_video_window.onBack()
                return

        if self.mode in (Mode.PLAY, Mode.SLIDESHOW, Mode.SECURITY_VIDEO):
            if key == Qt.Key_Pause:
                self.toggle_play_pause()
            
        focus_widget = QApplication.focusWidget()
        
        if self.mode == Mode.CAMERA:
            if key == Qt.Key_1:
                self.show_fullscreen(self.urls[0])
            elif key == Qt.Key_2:
                self.show_fullscreen(self.urls[1])
            elif key == Qt.Key_3:
                self.show_fullscreen(self.urls[2])
            elif key == Qt.Key_4:
                self.show_fullscreen(self.urls[3])
            elif key == Qt.Key_5:
                self.show_fullscreen(self.urls[4])

        # print(f"Key pressed: {key}, Focus widget: {type(focus_widget)}, Mode: {self.mode}")
        if key in (Qt.Key_Right, Qt.Key_Down, Qt.Key_L, Qt.Key_J):
            if self.mode == Mode.PLAY:
                # Next image in PLAY mode
                print("next image")
                self.next_image()
                return
            elif self.mode == Mode.SLIDESHOW or self.mode == Mode.CAMERA or self.mode == Mode.SECURITY_VIDEO:
                # In SLIDESHOW or CAMERA mode, move focus to next widget
                print("right/down pressed, sending tab")
                QApplication.sendEvent(focus_widget, QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier))
                return
            elif self.mode == Mode.PHOTO_FOLDER or self.mode == Mode.SECURITY_CAMERA_FOLDER:
                if key == Qt.Key_L:
                    # print("L key pressed in PHOTO_FOLDER, move to next widget")
                    QApplication.sendEvent(focus_widget, QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier))
                    return
                elif key == Qt.Key_J:
                    print("J key pressed in FOLDER, move down widget")
                    for r, row in enumerate(self.folder_buttons):
                        for c, btn in enumerate(row):
                            if btn is focus_widget:
                                # Move to next row, same column
                                if r + 1 < len(self.folder_buttons):
                                    next_row = self.folder_buttons[r + 1]
                                    if c >= len(next_row):
                                        c = len(next_row) - 1
                                    next_row[c].setFocus()
                                    if self.folder_scroll_area:
                                        self.folder_scroll_area.ensureWidgetVisible(next_row[c])
                                    return                    
        elif key in (Qt.Key_Left, Qt.Key_Up, Qt.Key_H, Qt.Key_K):
            if self.mode == Mode.PLAY:
                print("prev image")
                self.previous_image()
                return
            elif self.mode == Mode.SLIDESHOW or self.mode == Mode.CAMERA or self.mode == Mode.SECURITY_VIDEO:
                print("left/up pressed, sending tab")
                QApplication.sendEvent(focus_widget, QKeyEvent(QEvent.KeyPress, Qt.Key_Backtab, Qt.NoModifier))
                return
            elif self.mode == Mode.PHOTO_FOLDER or self.mode == Mode.SECURITY_CAMERA_FOLDER:
                if key == Qt.Key_H:
                    print("H key pressed in FOLDER, move to prev widget")
                    QApplication.sendEvent(focus_widget, QKeyEvent(QEvent.KeyPress, Qt.Key_Backtab, Qt.NoModifier))
                    return
                elif key == Qt.Key_K:
                    print("K key pressed in FOLDER, move up widget")
                    for r, row in enumerate(self.folder_buttons):
                            for c, btn in enumerate(row):
                                if btn is focus_widget:
                                    if r - 1 >= 0:
                                        prev_row = self.folder_buttons[r - 1]
                                        if c >= len(prev_row):
                                            c = len(prev_row) - 1
                                        prev_row[c].setFocus()
                                        if self.folder_scroll_area:
                                            self.folder_scroll_area.ensureWidgetVisible(prev_row[c])
                                        return
        if key == Qt.Key_Enter or key == Qt.Key_Return:
            if isinstance(focus_widget, QPushButton) or isinstance(focus_widget, QToolButton):
                focus_widget.click()
            elif isinstance(focus_widget, QLabel):
                # Simulate mouse click on QLabel
                fake_event = QMouseEvent(QEvent.MouseButtonPress, QPoint(1, 1), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
                QApplication.sendEvent(focus_widget, fake_event)
                fake_release = QMouseEvent(QEvent.MouseButtonRelease, QPoint(1, 1), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
                QApplication.sendEvent(focus_widget, fake_release)

    def init_grid(self):
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(4)
        
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(10, 10, 10, 10)
        top_layout.setSpacing(20)

        self.viewer_btn = QPushButton("Security Videos")
        self.viewer_btn.setStyleSheet("font-size: 20px; padding: 10px; color: white; background-color: #444;")
        self.viewer_btn.clicked.connect(self.launch_security_video_viewer)
        self.viewer_btn.setFocusPolicy(Qt.StrongFocus)
        top_layout.addWidget(self.viewer_btn)

        self.viewer_btn = QPushButton("View Photos")
        self.viewer_btn.setStyleSheet("font-size: 20px; padding: 10px; color: white; background-color: #444;")
        self.viewer_btn.clicked.connect(self.launch_image_viewer)
        self.viewer_btn.setFocusPolicy(Qt.StrongFocus)
        top_layout.addWidget(self.viewer_btn)

        self.open_webcam_btn = QPushButton("Winsford Flash Webcam")
        self.open_webcam_btn.setStyleSheet("font-size: 20px; padding: 10px; color: white; background-color: #444;")
        self.open_webcam_btn.setFocusPolicy(Qt.StrongFocus)
        self.open_webcam_btn.clicked.connect(lambda event, u="https://camsecure.uk/HLS/rhough.m3u8": self.show_fullscreen(u, video_mode=True))

        top_layout.addWidget(self.open_webcam_btn)        
        outer_layout.addWidget(top_row)

        # Main horizontal layout: left + right
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        # Screen 1 (left side)
        browser1 = QWebEngineView()
        browser1.setCursor(Qt.BlankCursor)
        browser1.retry_count = 0
        browser1.max_retries = 100
        browser1.url_to_load = QUrl(self.urls[0])
        browser1.load(browser1.url_to_load)
        browser1.loadFinished.connect(lambda success, b=browser1: self.handle_load_finished(b, success))        
        browser1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        fsbutton0 = QPushButton(f"1 {self.urlnames[0]}")
        fsbutton0.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 28px;
                padding: 8px;
            }
            QPushButton:focus {
                border: 2px solid #00ffff;
                background-color: #222;
            }
        """)
        fsbutton0.setCursor(Qt.PointingHandCursor)
        fsbutton0.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        fsbutton0.setFocusPolicy(Qt.StrongFocus)
        fsbutton0.clicked.connect(lambda event, u=self.urls[0]: self.show_fullscreen(u))
        # fsbutton0.mousePressEvent = lambda event, u=self.urls[0]: self.show_fullscreen(u)
        # fsbutton0.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Optional: allows mouse + keyboard

        left_layout.addWidget(browser1)
        left_layout.addWidget(fsbutton0)

        # Screens 2–5 (right grid)
        right_widget = QWidget()
        right_grid = QGridLayout(right_widget)
        right_grid.setContentsMargins(0, 0, 0, 0)
        right_grid.setSpacing(2)

        for i in range(1, 5):
            container = QWidget()
            container.setCursor(Qt.BlankCursor)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)

            browser = QWebEngineView()
            browser.setCursor(Qt.BlankCursor)
            browser.retry_count = 0
            browser.max_retries = 1000
            browser.url_to_load = QUrl(self.urls[i])
            browser.load(browser.url_to_load)
            browser.loadFinished.connect(lambda success, b=browser: self.handle_load_finished(b, success))        
            browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            button = QPushButton(f"{i+1} {self.urlnames[i]}")
            button.setStyleSheet("""
                QPushButton {
                    color: white;
                    font-size: 28px;
                    padding: 8px;
                }
                QPushButton:focus {
                    border: 2px solid #00ffff;
                    background-color: #222;
                }
            """)
            button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.StrongFocus)
            button.setMinimumHeight(40)
            button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            button.clicked.connect(lambda event, u=self.urls[i]: self.show_fullscreen(u))

            layout.addWidget(browser)
            layout.addWidget(button)

            row, col = divmod(i - 1, 2)
            right_grid.addWidget(container, row, col)

        main_layout.addLayout(left_layout, 1)
        main_layout.addWidget(right_widget, 2)
        
        outer_layout.addLayout(main_layout)
        self.grid_widget.setLayout(outer_layout)     
        self.viewer_btn.setFocus()   
    
    def handle_load_finished(self, browser, success):
        if success:
            browser.retry_count = 0  # Reset on success
        else:
            if browser.retry_count < browser.max_retries:
                browser.retry_count += 1
                print(f"Retrying {browser.url_to_load.toString()} (attempt {browser.retry_count})")
                QTimer.singleShot(10000, lambda: browser.load(browser.url_to_load))  # Retry after 1s
            else:
                print(f"Failed to load {browser.url_to_load.toString()} after {browser.retry_count} attempts")
                # Optional: show error page or placeholder

    def show_fullscreen(self, url, video_mode=False):
        # Clear fullscreen layout
        self.mode = Mode.CAMERA_FULLSCREEN
        while self.fullscreen_layout.count():
            child = self.fullscreen_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


        back_button = QPushButton(f"Back to All Cameras")
        back_button.setFocusPolicy(Qt.StrongFocus)
        back_button.setStyleSheet("color: white; font-size: 28px; padding: 10px;")
        back_button.clicked.connect(lambda: self.showCameras())

        self.fullscreen_layout.addWidget(back_button)

        if not video_mode:
            browser = QWebEngineView()
            browser.load(QUrl(url))
            self.fullscreen_layout.addWidget(browser)
            self.stack.setCurrentWidget(self.fullscreen_widget)
        else:
            self.player.setMedia(QMediaContent(QUrl(url)))
            self.fullscreen_layout.addWidget(self.playerview)

            QTimer.singleShot(500, self.player.play)
            self.stack.setCurrentWidget(self.fullscreen_widget)

        back_button.setFocus()

    def resizeEvent(self, event):
        # Ensure video item fills the graphics view’s viewport
        if hasattr(self, "video_item") and hasattr(self, "view"):
            print("Resizing video item to fill viewport")
            viewport_size = self.playerview.viewport().size()
            self.video_item.setSize(QSizeF(viewport_size))
        super().resizeEvent(event)
    
    def handle_player_error(self, error):
        print("Playback error:", self.player.errorString())
        if self.player.error() != QMediaPlayer.NoError:
            # Retry logic
            QTimer.singleShot(2000, lambda: self.player.play())
        
    def showCameras(self):
        self.mode = Mode.CAMERA
        self.stack.setCurrentWidget(self.grid_widget)
        self.viewer_btn.setFocus()


    def launch_security_video_viewer(self):
        self.timer.stop()
        self.clear_fullscreen()
        self.security_video_window = SecurityVideoWindow(self)
        self.stack.setCurrentWidget(self.fullscreen_widget)        
        
    def launch_image_viewer(self):
        self.timer.stop()
        self.clear_fullscreen()
        self.mode = Mode.PHOTO_FOLDER
        self.show_slideshow_or_subfolders(SOURCE_DIR)


    def show_images(self, folder_path, images):
        self.slideshow_index = 0
        self.slideshow_images = [os.path.join(folder_path, f) for f in sorted(images)]
        self.show_slideshow(folder_path)

    def show_slideshow_or_subfolders(self, folder_path):
        self.clear_fullscreen()

        # Update breadcrumbs
        self.breadcrumbs = os.path.relpath(folder_path, SOURCE_DIR).split(os.sep)

        entries = os.listdir(folder_path)
        subfolders = [f for f in entries if os.path.isdir(os.path.join(folder_path, f))]
        images = [f for f in entries if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))]

        if images and not subfolders:
            self.show_images(folder_path, images)
            return

        if subfolders:
            self.folder_buttons = []
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setAlignment(Qt.AlignTop)
    
            label = QLabel(f"{self.breadcrumbs[-1]} Folder" if self.breadcrumbs and self.breadcrumbs != ['.'] else "Top Level Folder")
            label.setStyleSheet("font-size: 28px; color: white;")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            row_buttons = []

            if self.breadcrumbs:
                # Breadcrumb bar
                breadcrumb_bar = QWidget()
                breadcrumb_layout = QHBoxLayout(breadcrumb_bar)
                breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
                breadcrumb_layout.setSpacing(10)

                back_button = QPushButton("Back to All Cameras")
                back_button.setFocusPolicy(Qt.StrongFocus)
                back_button.setStyleSheet("""
                    QPushButton {
                        color: white;
                        font-size: 28px;
                        padding: 8px;
                    }
                    QPushButton:focus {
                        border: 2px solid #00ffff;
                        background-color: #222;
                    }
                """)
                back_button.clicked.connect(lambda: self.showCameras())
                breadcrumb_layout.addWidget(back_button)
                row_buttons.append(back_button)

                if folder_path != SOURCE_DIR:
                    root_button = QPushButton("Back to Top Level")
                    root_button.setFocusPolicy(Qt.StrongFocus)
                    root_button.setStyleSheet("""
                        QPushButton {
                            color: white;
                            font-size: 28px;
                            padding: 8px;
                        }
                        QPushButton:focus {
                            border: 2px solid #00ffff;
                            background-color: #222;
                        }
                    """)
                    root_button.clicked.connect(lambda: self.show_slideshow_or_subfolders(SOURCE_DIR))
                    breadcrumb_layout.addWidget(root_button)
                    row_buttons.append(root_button)
        
                # Add clickable breadcrumb buttons
                path_so_far = SOURCE_DIR
                for i, crumb in enumerate(self.breadcrumbs):
                    path_so_far = os.path.join(path_so_far, crumb)
                    if path_so_far == folder_path or crumb == '.':
                        continue # Skip current folder
                    btn = QPushButton(f"Back to {crumb}")
                    btn.setFocusPolicy(Qt.StrongFocus)
                    btn.setStyleSheet("""
                        QPushButton {
                            color: white;
                            font-size: 28px;
                            padding: 8px;
                        }
                        QPushButton:focus {
                            border: 2px solid #00ffff;
                            background-color: #222;
                        }
                    """)
                    btn.clicked.connect(lambda _, p=path_so_far: self.show_slideshow_or_subfolders(p))
                    breadcrumb_layout.addWidget(btn)
                    row_buttons.append(btn)

                layout.addWidget(breadcrumb_bar)

            # Add row of buttons to list of navigable grid buttons
            self.folder_buttons.append(row_buttons)

            # Grid for folder buttons
            grid = QGridLayout()
            grid.setSpacing(15)
            count = 0
            if images:
                photo_btn = QPushButton(f"Show photos in this folder ({len(images)})")
                photo_btn.setFocusPolicy(Qt.StrongFocus)
                photo_btn.setStyleSheet("""
                    QPushButton {
                        color: white;
                        font-size: 28px;
                        padding: 8px;
                    }
                    QPushButton:focus {
                        border: 2px solid #00ffff;k
                        background-color: #222;
                    }
                """)
                photo_btn.clicked.connect(lambda: self.show_images(folder_path, images))
                icon = self.icon_provider.icon(QFileIconProvider.File)
                photo_btn.setIcon(icon)
                photo_btn.setIconSize(QSize(32, 32))
                photo_btn.setMinimumSize(120, 60)
                #Add as first button in grid
                grid.addWidget(photo_btn, 0, 0)
                row_buttons = [photo_btn]
                count = 1
  
            if len(subfolders) > 20:
                cols = 3  # Number of columns in the grid
            else:
                cols = 1  # Single column
            for i, sub in enumerate(sorted(subfolders)):
                sub_path = os.path.join(folder_path, sub)
                btn = QPushButton(sub)
                btn.setStyleSheet("""
                    QPushButton {
                        color: white;
                        font-size: 28px;
                        padding: 8px;
                    }
                    QPushButton:focus {
                        border: 2px solid #00ffff;
                        background-color: #222;
                    }
                """)
                btn.setFocusPolicy(Qt.StrongFocus)
                btn.clicked.connect(lambda _, p=sub_path: self.show_slideshow_or_subfolders(p))
                icon = self.icon_provider.icon(QFileIconProvider.Folder)
                btn.setIcon(icon)
                btn.setIconSize(QSize(32, 32))
                btn.setMinimumSize(120, 60)                
                row, col = divmod(i+count, cols)
                if col == 0:
                    if row > 0:
                        self.folder_buttons.append(row_buttons)
                    row_buttons = []
                row_buttons.append(btn)
                # print(f"Adding button for {sub} at row {row}, col {col}")
                grid.addWidget(btn, row, col)

            if row_buttons:
                self.folder_buttons.append(row_buttons)
            layout.addLayout(grid)

            self.folder_scroll_area = QScrollArea()
            self.folder_scroll_area.setWidgetResizable(True)
            self.folder_scroll_area.setWidget(container)
            self.fullscreen_layout.addWidget(self.folder_scroll_area)
            self.stack.setCurrentWidget(self.fullscreen_widget)
            back_button.setFocus()
            return

        # If no images or subfolders
        label = QLabel("No images or folders found.")
        label.setStyleSheet("font-size: 32px; color: red;")
        label.setAlignment(Qt.AlignCenter)
        self.fullscreen_layout.addWidget(label)
        self.stack.setCurrentWidget(self.fullscreen_widget)
            
    def go_up_one_folder(self):
        # print (f"backspace pressed {self.breadcrumbs}")
        self.timer.stop()
        self.mode = Mode.PHOTO_FOLDER
        if not self.breadcrumbs or self.breadcrumbs == ['.']:
            # Already at top level - back to cameras
            self.showCameras()
        else:
            # Remove last breadcrumb and rebuild path
            self.breadcrumbs.pop()
            new_path = os.path.join(SOURCE_DIR, *self.breadcrumbs)
            self.show_slideshow_or_subfolders(new_path)

    def show_slideshow(self, folder_path):
        self.clear_fullscreen()
        self.mode = Mode.SLIDESHOW

        image_files = [f for f in os.listdir(folder_path)
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))]

        if not image_files:
            label = QLabel("No images found!")
            label.setStyleSheet("font-size: 32px; color: red;")
            label.setAlignment(Qt.AlignCenter)
            self.fullscreen_layout.addWidget(label)
            self.stack.setCurrentWidget(self.fullscreen_widget)
            return

        self.slideshow_index = 0
        self.slideshow_images = [os.path.join(folder_path, f) for f in sorted(image_files)]

        # Create a container widget with its own layout
        container = QWidget()
        container.setCursor(Qt.BlankCursor)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        label = QLabel(f"Photos from {self.breadcrumbs[len(self.breadcrumbs)-1]}" if self.breadcrumbs and self.breadcrumbs != ['.'] else "Slideshow"
)
        label.setStyleSheet("font-size: 28px; color: white;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        # Navigation buttons in horizontal layout
        self.slideshow_controls = QWidget()
        button_layout = QHBoxLayout(self.slideshow_controls)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(20)

        prev_btn = QPushButton("Previous")
        prev_btn.setFocusPolicy(Qt.StrongFocus)
        prev_btn.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 28px;
                padding: 8px;
            }
            QPushButton:focus {
                border: 2px solid #00ffff;
                background-color: #222;
            }
        """)
        prev_btn.clicked.connect(self.previous_image)
        button_layout.addWidget(prev_btn)
        
        next_btn = QPushButton("Next")
        next_btn.setFocusPolicy(Qt.StrongFocus)
        next_btn.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 28px;
                padding: 8px;
            }
            QPushButton:focus {
                border: 2px solid #00ffff;
                background-color: #222;
            }
        """)
        next_btn.clicked.connect(self.next_image)
        button_layout.addWidget(next_btn)

        # Play/Pause toggle
        self.play_pause_btn = QPushButton("Play")
        self.play_pause_btn.setFocusPolicy(Qt.StrongFocus)
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 28px;
                padding: 8px;
            }
            QPushButton:focus {
                border: 2px solid #00ffff;
                background-color: #222;
            }
        """)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        button_layout.addWidget(self.play_pause_btn)

        back_btn = QPushButton("Back to Previous Folder")
        back_btn.setFocusPolicy(Qt.StrongFocus)
        back_btn.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 28px;
                padding: 8px;
            }
            QPushButton:focus {
                border: 2px solid #00ffff;
                background-color: #222;
            }
        """)
        back_btn.clicked.connect(self.go_up_one_folder)
        button_layout.addWidget(back_btn)

        layout.addWidget(self.slideshow_controls)

        # Image display
        self.slideshow_label = QLabel()
        self.slideshow_label.setAlignment(Qt.AlignCenter)
        self.slideshow_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.slideshow_label)

        # Add container to fullscreen layout
        self.fullscreen_layout.addWidget(container)

        self.show_image()
        QTimer.singleShot(0, lambda: self.show_image()) # Refresh image after layout
        self.stack.setCurrentWidget(self.fullscreen_widget)
        self.play_pause_btn.setFocus()

    def clear_fullscreen(self):
        self.timer.stop()
        while self.fullscreen_layout.count():
            child = self.fullscreen_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def show_image(self):
        path = self.slideshow_images[self.slideshow_index]
        pixmap = QPixmap(path)

        if self.mode == Mode.PLAY:
            # Hide control buttons
            self.slideshow_controls.hide()

            # Resize image to fullscreen
            screen_size = QApplication.primaryScreen().size()
            scaled = pixmap.scaled(screen_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.slideshow_label.setPixmap(scaled)
            self.slideshow_label.setAlignment(Qt.AlignCenter)
        else:
            # Show controls
            self.slideshow_controls.show()

            # Fit image to label size
            scaled = pixmap.scaled(self.slideshow_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.slideshow_label.setPixmap(scaled)
        
        # # Use label dimensions directly to avoid zero-size issues
        # target_width = self.slideshow_label.width()
        # target_height = self.slideshow_label.height()

        # if target_width > 0 and target_height > 0:
        #     scaled = pixmap.scaled(
        #         target_width,
        #         target_height,
        #         Qt.KeepAspectRatio,
        #         Qt.SmoothTransformation
        #     )
        #     self.slideshow_label.setPixmap(scaled)
        # else:
        #     # Fallback: show original pixmap until layout is ready
        #     self.slideshow_label.setPixmap(pixmap)

    def next_image(self):
        if self.mode == Mode.PLAY:
            self.timer.stop()
            self.timer.start(IMAGE_TIMER)  # Restart  countdown
        self.slideshow_index = self.slideshow_index + 1
        if self.slideshow_index > len(self.slideshow_images) - 1:
            self.timer.stop()
            self.mode = Mode.PHOTO_FOLDER
            self.slideshow_index = len(self.slideshow_images) - 1
            self.go_up_one_folder()
        self.show_image()
    
    def previous_image(self):
        if self.mode == Mode.PLAY:
            self.timer.stop()
            self.timer.start(IMAGE_TIMER)  # Restart  countdown
        self.slideshow_index = self.slideshow_index - 1
        if self.slideshow_index < 0:
            self.slideshow_index = len(self.slideshow_images) - 1
        self.show_image()

    def toggle_play_pause(self):
        # Only allow play/pause if slideshow is active
        if self.mode not in (Mode.PLAY, Mode.SLIDESHOW):
            return  # Not in slideshow mode
        if self.mode == Mode.PLAY:
            self.timer.stop()
            self.play_pause_btn.setText("Play")
            self.mode = Mode.SLIDESHOW
        else:
            self.timer.start(IMAGE_TIMER)
            self.play_pause_btn.setText("Pause")
            self.mode = Mode.PLAY
    
    def restore_grid(self):
        # Clear fullscreen layout
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            self.layout.removeWidget(widget)
            widget.setParent(None)

        # Rebuild grid
        self.init_layout()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QPushButton:focus, QLabel:focus {
            border: 2px solid #00ffff;
            background-color: #333;
            color: white;
        }
        QPushButton:hover {
            background-color: #444;
        }
        QLabel:focus {
            border: 2px solid #00ffff;
            background-color: #222;
        }
    """) 
    window = WebGrid()
    window.show()
    sys.exit(app.exec_())
    
