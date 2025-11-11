from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineSettings
from PyQt5.QtWebEngineWidgets import QWebEnginePage

class DebugPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"JS console: {message} (line {lineNumber}, source {sourceID})")
        

class HLSWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HLS via QWebEngineView")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        self.browser = QWebEngineView()
        self.browser.setPage(DebugPage(self.browser))
        self.browser.settings().setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)

        layout.addWidget(self.browser)

        # Load a simple HTML page with a <video> element
        html = """
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
        </head>
        <body style="margin:0; background:black;">
          <video id="video" controls autoplay style="width:100%; height:100%;"></video>
            <script>
            var video = document.getElementById('video');
            if (Hls.isSupported()) {
                var hls = new Hls();
                hls.on(Hls.Events.ERROR, function(event, data) {
                console.error("HLS.js error:", data.type, data.details, data.fatal);
                });
                hls.on(Hls.Events.MANIFEST_PARSED, function() {
                console.log("Manifest parsed, starting playback");
                video.play().catch(err => console.error("Play failed:", err));
                });
                hls.loadSource('https://camsecure.uk/HLS/rhough.m3u8');
                hls.attachMedia(video);
            } else {
                console.error("HLS not supported in this environment");
            }
            </script>
            </body>
        </html>
        """

        self.browser.setHtml(html, QUrl("https://camsecure.uk"))

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = HLSWindow()
    w.show()
    sys.exit(app.exec_())
