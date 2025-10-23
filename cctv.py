import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy, QStackedLayout
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt

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

    def init_grid(self):
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(4)
        
        top_label = QLabel("Click for Image viewer")
        top_label.setStyleSheet("""
            color: white;
            font-size: 28px;
            padding: 8px;
        """)
        top_label.setAlignment(Qt.AlignCenter)
        top_label.setCursor(Qt.PointingHandCursor)
        top_label.mousePressEvent = lambda event: self.launch_image_viewer()
        
        outer_layout.addWidget(top_label)

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

        label1 = QLabel(f"Click for full screen of {self.urls[0]}")
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

            label = QLabel(f"Click for full screen of {self.urls[i]}")
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
        import subprocess
        subprocess.Popen(["feh --slideshow-delay 5 --fullscreen --recursive --tap-zones /home/danny/Dropbox/Photos/Bigbertha_backup/"])
    
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
    