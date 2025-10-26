import sys
import os

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QGridLayout, QVBoxLayout, QScrollArea, QHBoxLayout, QPushButton, QLabel, QSizePolicy, QStackedLayout
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QTimer

SOURCE_DIR = "/home/danny/Dropbox/Photos/Bigbertha_backup/"
IMAGE_TIMER = 3000  # 3 seconds

# List of URLs to display
def load_urls(filename):
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return []

# class TrustedPage(QWebEnginePage):
#     def certificateError(self, error):
#         # Optionally check the URL before trusting
#         # if error.url().toString().startswith("https://your-site.com"):
#         error.ignoreCertificateError()
#         return True
    
class WebGrid(QWidget):
    def __init__(self, urls):
        super().__init__()
        self.urls = urls[:5]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_image)
        self.is_playing = False  # Track play/pause state        
        self.breadcrumbs = []  # List of folder names
        self.setWindowTitle("Camera Monitoring")
        self.setStyleSheet("background-color: black;")
        self.stack = QStackedLayout(self)
        self.setLayout(self.stack)

        self.grid_widget = QWidget()
        # self.grid_layout = QHBoxLayout(self.grid_widget)
        self.stack.addWidget(self.grid_widget)

        self.fullscreen_widget = QWidget()
        self.fullscreen_layout = QVBoxLayout(self.fullscreen_widget)
        self.stack.addWidget(self.fullscreen_widget)

        self.init_grid()
        self.stack.setCurrentWidget(self.grid_widget)
        self.showFullScreen()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace:
            self.go_up_one_folder()

    def init_grid(self):
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(4)
        
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(10, 10, 10, 10)
        top_layout.setSpacing(20)

        # Image viewer label
        viewer_btn = QPushButton("Image viewer")
        viewer_btn.setStyleSheet("font-size: 20px; padding: 10px; color: white; background-color: #444;")
        viewer_btn.clicked.connect(self.launch_image_viewer)
        top_layout.addWidget(viewer_btn)        
        # top_label = QLabel("Click for Image viewer")
        # top_label.setStyleSheet("color: white; font-size: 28px; padding: 8px;")
        # top_label.setAlignment(Qt.AlignLeft)
        # top_label.setCursor(Qt.PointingHandCursor)
        # top_label.mousePressEvent = lambda event: self.launch_image_viewer()
        # top_layout.addWidget(top_label)
        # Exit button
        exit_btn = QPushButton("Exit")
        exit_btn.setStyleSheet("font-size: 20px; padding: 10px; color: white; background-color: #444;")
        exit_btn.clicked.connect(QApplication.instance().quit)
        top_layout.addWidget(exit_btn)        
        
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

        label1 = QLabel(f"Full screen of {self.urls[0]}")
        label1.setStyleSheet("color: white; font-size: 28px; padding: 8px;")
        label1.setCursor(Qt.PointingHandCursor)
        label1.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        label1.mousePressEvent = lambda event, u=self.urls[0]: self.show_fullscreen(u)

        left_layout.addWidget(browser1)
        left_layout.addWidget(label1)

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

            label = QLabel(f"Full screen of {self.urls[i]}")
            label.setStyleSheet("color: white; font-size: 28px; padding: 8px;")
            label.setCursor(Qt.PointingHandCursor)
            label.setMinimumHeight(40)
            label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            label.mousePressEvent = lambda event, u=self.urls[i]: self.show_fullscreen(u)

            layout.addWidget(browser)
            layout.addWidget(label)

            row, col = divmod(i - 1, 2)
            right_grid.addWidget(container, row, col)

        main_layout.addLayout(left_layout, 1)
        main_layout.addWidget(right_widget, 2)
        
        outer_layout.addLayout(main_layout)
        self.grid_widget.setLayout(outer_layout)        
              
    def show_fullscreen(self, url):
        # Clear fullscreen layout
        while self.fullscreen_layout.count():
            child = self.fullscreen_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        browser = QWebEngineView()
        # host = url.split("//")[1]
        # authUrl = url
        # for domain in self.credentials:
        #     if domain in url:
        #         username, password = self.credentials[domain]
        #         authUrl = f"http://{username}:{password}@{host}"
        #         break
        # # browser.setPage(TrustedPage(profile, browser))
        # print(f"Using auth URL: {authUrl}")
        browser.load(QUrl(url))

        back_button = QPushButton("Back to All Cameras")
        back_button.setStyleSheet("color: white; font-size: 18px; padding: 10px;")
        back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.grid_widget))

        self.fullscreen_layout.addWidget(back_button)
        self.fullscreen_layout.addWidget(browser)

        self.stack.setCurrentWidget(self.fullscreen_widget)

    def launch_image_viewer(self):
        self.timer.stop()
        self.clear_fullscreen()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        back_button = QPushButton("Back to All Cameras")
        back_button.setStyleSheet("font-size: 24px; padding: 10px; color: white;")
        back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.grid_widget))
        layout.addWidget(back_button)

        for folder in os.listdir(SOURCE_DIR):
            folder_path = os.path.join(SOURCE_DIR, folder)
            if os.path.isdir(folder_path):
                btn = QPushButton(folder)
                btn.setStyleSheet("font-size: 24px; padding: 10px; color: white;")
                btn.clicked.connect(lambda _, p=folder_path: self.show_slideshow_or_subfolders(p))
                layout.addWidget(btn)

        scroll.setWidget(container)
        self.fullscreen_layout.addWidget(scroll)
        self.stack.setCurrentWidget(self.fullscreen_widget)

    def show_slideshow_or_subfolders(self, folder_path):
        self.clear_fullscreen()

        # Update breadcrumbs
        self.breadcrumbs = os.path.relpath(folder_path, SOURCE_DIR).split(os.sep)

        entries = os.listdir(folder_path)
        subfolders = [f for f in entries if os.path.isdir(os.path.join(folder_path, f))]
        images = [f for f in entries if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))]

        if images:
            self.slideshow_index = 0
            self.slideshow_images = [os.path.join(folder_path, f) for f in sorted(images)]
            self.show_slideshow(folder_path)
            return

        if subfolders:
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setAlignment(Qt.AlignTop)
            
            # Breadcrumb bar
            breadcrumb_bar = QWidget()
            breadcrumb_layout = QHBoxLayout(breadcrumb_bar)
            breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
            breadcrumb_layout.setSpacing(10)
    
            # Add clickable breadcrumb buttons
            path_so_far = SOURCE_DIR
            for i, crumb in enumerate(self.breadcrumbs):
                path_so_far = os.path.join(path_so_far, crumb)
                btn = QPushButton(crumb)
                btn.setStyleSheet("font-size: 16px; padding: 6px; color: white; background-color: #666;")
                btn.clicked.connect(lambda _, p=path_so_far: self.show_slideshow_or_subfolders(p))
                breadcrumb_layout.addWidget(btn)

                if i < len(self.breadcrumbs) - 1:
                    arrow = QLabel("➔")
                    arrow.setStyleSheet("color: white; font-size: 16px;")
                    breadcrumb_layout.addWidget(arrow)

            layout.addWidget(breadcrumb_bar)
    
            for sub in sorted(subfolders):
                sub_path = os.path.join(folder_path, sub)
                btn = QPushButton(sub)
                btn.setStyleSheet("font-size: 24px; padding: 10px; color: white; background-color: #444;")
                btn.clicked.connect(lambda _, p=sub_path: self.show_slideshow_or_subfolders(p))
                layout.addWidget(btn)

            # Exit button
            exit_btn = QPushButton("Back to Folders")
            exit_btn.setStyleSheet("font-size: 20px; padding: 12px; color: white; background-color: #444;")
            exit_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.grid_widget))
            layout.addWidget(exit_btn)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(container)
            self.fullscreen_layout.addWidget(scroll)
            self.stack.setCurrentWidget(self.fullscreen_widget)
            return

        # If no images or subfolders
        label = QLabel("No images or folders found.")
        label.setStyleSheet("font-size: 24px; color: white;")
        label.setAlignment(Qt.AlignCenter)
        self.fullscreen_layout.addWidget(label)
        self.stack.setCurrentWidget(self.fullscreen_widget)
            
    def go_up_one_folder(self):
        if not self.breadcrumbs:
            return  # Already at top level

        # Remove last breadcrumb and rebuild path
        self.breadcrumbs.pop()
        new_path = os.path.join(SOURCE_DIR, *self.breadcrumbs)
        self.show_slideshow_or_subfolders(new_path)

    def show_slideshow(self, folder_path):
        self.clear_fullscreen()

        image_files = [f for f in os.listdir(folder_path)
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))]

        if not image_files:
            label = QLabel("No images found.")
            label.setStyleSheet("font-size: 24px; color: white;")
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

        # Navigation buttons in horizontal layout
        button_row = QWidget()
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(20)

        prev_btn = QPushButton("Previous")
        prev_btn.setStyleSheet("font-size: 20px; padding: 12px; color: white; background-color: #444;")
        prev_btn.clicked.connect(self.previous_image)
        button_layout.addWidget(prev_btn)
        
        next_btn = QPushButton("Next")
        next_btn.setStyleSheet("font-size: 20px; padding: 12px; color: white; background-color: #444;")
        next_btn.clicked.connect(self.next_image)
        button_layout.addWidget(next_btn)

        # Play/Pause toggle
        self.play_pause_btn = QPushButton("Play")
        self.play_pause_btn.setStyleSheet("font-size: 20px; padding: 12px; color: white; background-color: #444;")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        button_layout.addWidget(self.play_pause_btn)

        back_btn = QPushButton("Back to Folders")
        back_btn.setStyleSheet("font-size: 20px; padding: 12px; color: white; background-color: #444;")
        back_btn.clicked.connect(self.launch_image_viewer)
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
        self.is_playing = False
        self.play_pause_btn.setText("Play")        

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
        if self.is_playing:
            self.timer.stop()
            self.is_playing = False
            self.timer.start(IMAGE_TIMER)  # Restart  countdown
        self.slideshow_index = self.slideshow_index + 1
        if self.slideshow_index > len(self.slideshow_images) - 1:
            self.timer.stop()
            self.is_playing = False
            self.slideshow_index = len(self.slideshow_images) - 1
            self.launch_image_viewer()
        self.show_image()
    
    def previous_image(self):
        if self.is_playing:
            self.timer.stop()
            self.timer.start(IMAGE_TIMER)  # Restart  countdown
        self.slideshow_index = self.slideshow_index - 1
        if self.slideshow_index < 0:
            self.slideshow_index = 0
        self.show_image()

    def toggle_play_pause(self):
        if self.is_playing:
            self.timer.stop()
            self.play_pause_btn.setText("Play")
            self.is_playing = False
        else:
            self.timer.start(IMAGE_TIMER)  # 5 seconds
            self.play_pause_btn.setText("Pause")
            self.is_playing = True    
    # def launch_image_viewer(self):
    #     import subprocess
    #     subprocess.Popen(["feh", "--slideshow-delay","3", "--fullscreen", "--recursive", "/home/danny/Dropbox/Photos/Bigbertha_backup/"])
    
    def restore_grid(self):
        # Clear fullscreen layout
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            self.layout.removeWidget(widget)
            widget.setParent(None)

        # Rebuild grid
        self.init_layout()
        
if __name__ == "__main__":
    urls = load_urls("urls.txt")
    if not urls:
        sys.exit("No URLs to display.")
    # creds = load_credentials("credentials.txt")
    app = QApplication(sys.argv)
    window = WebGrid(urls)
    window.show()
    sys.exit(app.exec_())
    
