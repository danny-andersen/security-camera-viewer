import sys
import os

from PyQt5.QtGui import QPixmap, QKeyEvent, QMouseEvent
from PyQt5.QtWidgets import (
    QApplication, QWidget, QGridLayout, QVBoxLayout, QScrollArea, QHBoxLayout, QPushButton, QLabel, QSizePolicy, QStackedLayout, QFileIconProvider
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QTimer, QEvent, QPoint, QSize
from enum import Enum, auto

SOURCE_DIR = "/home/danny/Dropbox/Photos/Bigbertha_backup/"
IMAGE_TIMER = 3000  # 3 seconds

class Mode(Enum):
    CAMERA = auto()
    PHOTO_FOLDER = auto()
    SLIDESHOW = auto()
    PLAY = auto()
    
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
        # self.grid_widget.setFocusPolicy(Qt.StrongFocus)
        # self.grid_layout = QHBoxLayout(self.grid_widget)
        self.stack.addWidget(self.grid_widget)

        self.fullscreen_widget = QWidget()
        self.fullscreen_layout = QVBoxLayout(self.fullscreen_widget)
        self.stack.addWidget(self.fullscreen_widget)

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
            else:
                # In CAMERA mode, set focus to image viewer button
                self.viewer_btn.setFocus()
        if self.mode in (Mode.PLAY, Mode.SLIDESHOW):
            if key == Qt.Key_Pause:
                self.toggle_play_pause()
            
        focus_widget = QApplication.focusWidget()

        print(f"Key pressed: {key}, Focus widget: {type(focus_widget)}, Mode: {self.mode}")
        if key in (Qt.Key_Right, Qt.Key_Down, Qt.Key_L, Qt.Key_J):
            if self.mode == Mode.PLAY:
                # Next image in PLAY mode
                print("next image")
                self.next_image()
                return
            elif self.mode == Mode.SLIDESHOW or self.mode == Mode.CAMERA:
                # In SLIDESHOW or CAMERA mode, move focus to next widget
                print("right/down pressed, sending tab")
                QApplication.sendEvent(focus_widget, QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier))
                return
            elif self.mode == Mode.PHOTO_FOLDER:
                if key == Qt.Key_L:
                    # print("L key pressed in PHOTO_FOLDER, move to next widget")
                    QApplication.sendEvent(focus_widget, QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier))
                    return
                elif key == Qt.Key_J:
                    print("J key pressed in PHOTO_FOLDER, move down widget")
                    for r, row in enumerate(self.folder_buttons):
                        for c, btn in enumerate(row):
                            if btn is focus_widget:
                                # Move to next row, same column
                                if r + 1 < len(self.folder_buttons):
                                    next_row = self.folder_buttons[r + 1]
                                    if c < len(next_row):
                                        next_row[c].setFocus()
                                        if self.folder_scroll_area:
                                            self.folder_scroll_area.ensureWidgetVisible(next_row[c])
                                        return                    
        elif key in (Qt.Key_Left, Qt.Key_Up, Qt.Key_H, Qt.Key_K):
            if self.mode == Mode.PLAY:
                print("prev image")
                self.previous_image()
                return
            elif self.mode == Mode.SLIDESHOW or self.mode == Mode.CAMERA:
                print("left/up pressed, sending tab")
                QApplication.sendEvent(focus_widget, QKeyEvent(QEvent.KeyPress, Qt.Key_Backtab, Qt.NoModifier))
                return
            elif self.mode == Mode.PHOTO_FOLDER:
                if key == Qt.Key_H:
                    print("H key pressed in PHOTO_FOLDER, move to prev widget")
                    QApplication.sendEvent(focus_widget, QKeyEvent(QEvent.KeyPress, Qt.Key_Backtab, Qt.NoModifier))
                    return
                elif key == Qt.Key_K:
                    print("K key pressed in PHOTO_FOLDER, move up widget")
                    for r, row in enumerate(self.folder_buttons):
                            for c, btn in enumerate(row):
                                if btn is focus_widget:
                                    if r - 1 >= 0:
                                        prev_row = self.folder_buttons[r - 1]
                                        if c < len(prev_row):
                                            prev_row[c].setFocus()
                                            if self.folder_scroll_area:
                                                self.folder_scroll_area.ensureWidgetVisible(prev_row[c])
                                            return
        if key == Qt.Key_Enter or key == Qt.Key_Return:
            if isinstance(focus_widget, QPushButton):
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

        # Image viewer label
        self.viewer_btn = QPushButton("View Photos")
        self.viewer_btn.setStyleSheet("font-size: 20px; padding: 10px; color: white; background-color: #444;")
        self.viewer_btn.clicked.connect(self.launch_image_viewer)
        self.viewer_btn.setFocusPolicy(Qt.StrongFocus)
        top_layout.addWidget(self.viewer_btn)
        
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
        browser1.load(QUrl(self.urls[0]))
        browser1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        fsbutton0 = QPushButton(self.urlnames[0])
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
        fsbutton0.clicked.connect(lambda event, u=0: self.show_fullscreen(u))
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
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)

            browser = QWebEngineView()
            browser.load(QUrl(self.urls[i]))
            browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            button = QPushButton(self.urlnames[i])
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
            button.clicked.connect(lambda event, u=i: self.show_fullscreen(u))

            layout.addWidget(browser)
            layout.addWidget(button)

            row, col = divmod(i - 1, 2)
            right_grid.addWidget(container, row, col)

        main_layout.addLayout(left_layout, 1)
        main_layout.addWidget(right_widget, 2)
        
        outer_layout.addLayout(main_layout)
        self.grid_widget.setLayout(outer_layout)     
        self.viewer_btn.setFocus()   
              
    def show_fullscreen(self, index):
        # Clear fullscreen layout
        while self.fullscreen_layout.count():
            child = self.fullscreen_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        browser = QWebEngineView()
        browser.load(QUrl(self.urls[index]))

        back_button = QPushButton(f"Back to All Cameras")
        back_button.setFocusPolicy(Qt.StrongFocus)
        back_button.setStyleSheet("color: white; font-size: 28px; padding: 10px;")
        back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.grid_widget))

        self.fullscreen_layout.addWidget(back_button)
        self.fullscreen_layout.addWidget(browser)

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
                back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.grid_widget))
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

            if images:
                photo_btn = QPushButton(f"Photos in this folder ({len(images)})")
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
                layout.addWidget(photo_btn)
                row_buttons.append(photo_btn)

            # Add row of buttons to list of navigable grid buttons
            self.folder_buttons.append(row_buttons)
    
            # Grid for folder buttons
            grid = QGridLayout()
            grid.setSpacing(15)
            cols = 3  # Number of columns in the grid
                
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
                row, col = divmod(i, cols)
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
        print (f"backspace pressed {self.breadcrumbs}")
        self.timer.stop()
        self.mode = Mode.PHOTO_FOLDER
        if not self.breadcrumbs or self.breadcrumbs == ['.']:
            # Already at top level - back to cameras
            self.stack.setCurrentWidget(self.grid_widget)
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
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        label = QLabel(f"Photos from {self.breadcrumbs[len(self.breadcrumbs)-1]}" if self.breadcrumbs and self.breadcrumbs != ['.'] else "Slideshow"
)
        label.setStyleSheet("font-size: 28px; color: white;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        # Navigation buttons in horizontal layout
        button_row = QWidget()
        button_layout = QHBoxLayout(button_row)
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

        layout.addWidget(button_row)

        # Image display
        self.slideshow_label = QLabel()
        self.slideshow_label.setAlignment(Qt.AlignCenter)
        self.slideshow_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.slideshow_label)

        # Add container to fullscreen layout
        self.fullscreen_layout.addWidget(container)

        self.show_image()
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

        # Use label dimensions directly to avoid zero-size issues
        target_width = self.slideshow_label.width()
        target_height = self.slideshow_label.height()

        if target_width > 0 and target_height > 0:
            scaled = pixmap.scaled(
                target_width,
                target_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.slideshow_label.setPixmap(scaled)
        else:
            # Fallback: show original pixmap until layout is ready
            self.slideshow_label.setPixmap(pixmap)

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
    
