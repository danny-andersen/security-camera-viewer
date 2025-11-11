from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt5.QtCore import QUrl, QTimer, QSizeF

class VideoWindow(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HLS Stream Player (QGraphicsVideoItem)")
        self.resize(800, 600)

        # Graphics scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Video item
        self.video_item = QGraphicsVideoItem()
        self.video_item.setSize(QSizeF(self.size()))  # convert QSize → QSizeF
        self.scene.addItem(self.video_item)

        # Media player
        self.player = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.video_item)

        # Load HLS stream
        url = "https://camsecure.uk/HLS/rhough.m3u8"
        self.player.setMedia(QMediaContent(QUrl(url)))

        # Debug signals
        self.player.mediaStatusChanged.connect(lambda s: print("Media status:", s))
        self.player.stateChanged.connect(lambda s: print("Player state:", s))
        self.player.error.connect(lambda e: print("Error:", self.player.errorString()))

        # Start playback after a short delay
        QTimer.singleShot(500, self.player.play)

        # Fullscreen
        self.showFullScreen()

    def resizeEvent(self, event):
        # Keep video item scaled to window size
        self.video_item.setSize(QSizeF(self.size()))
        super().resizeEvent(event)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = VideoWindow()
    w.show()
    sys.exit(app.exec_())
