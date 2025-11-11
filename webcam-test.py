from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, QTimer

class VideoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HLS Stream Player")
        self.resize(800, 600)

        self.video_widget = QVideoWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.video_widget)

        self.player = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.video_widget)

        url = "https://camsecure.uk/HLS/rhough.m3u8"
        self.player.setMedia(QMediaContent(QUrl(url)))

        # Ensure widget is shown before playback
        self.video_widget.show()

        # Delay play slightly
        QTimer.singleShot(500, self.player.play)

        # Debug signals
        self.player.mediaStatusChanged.connect(lambda s: print("Media status:", s))
        self.player.stateChanged.connect(lambda s: print("Player state:", s))
        self.player.error.connect(lambda e: print("Error:", self.player.errorString()))

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = VideoWindow()
    w.show()
    sys.exit(app.exec_())
