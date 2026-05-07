import 'package:flutter/material.dart';

import 'package:flutter_cctv/cameras.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';

class CameraWindow extends StatefulWidget {
  final CameraEntry entry;
  final VoidCallback onSelect;

  const CameraWindow({required this.entry, required this.onSelect, super.key});
  @override
  _CameraWindowState createState() => _CameraWindowState(
    title: entry.name,
    website: entry.url,
    onSelect: onSelect,
  );
}

class _CameraWindowState extends State<CameraWindow> {
  _CameraWindowState({
    required this.title,
    required this.website,
    required this.onSelect,
  });
  String title;
  String website;
  final VoidCallback onSelect;

  late final InAppWebViewController webViewController;
  final GlobalKey webViewKey = GlobalKey();
  final urlController = TextEditingController();
  double progress = 0;
  InAppWebViewSettings settings = InAppWebViewSettings(
    useShouldOverrideUrlLoading: true,
    mediaPlaybackRequiresUserGesture: false,
    useHybridComposition: true,
    allowsInlineMediaPlayback: true,
  );

  @override
  Widget build(BuildContext context) {
    // return Scaffold(
    // appBar: AppBar(
    //   title: Text(title, style: TextStyle(fontSize: 12)),
    //   titleSpacing: 0,
    //   toolbarHeight: 16,
    // ),
    // body: SafeArea(
    //   child:
    return Column(
      children: <Widget>[
        GestureDetector(
          onTap: onSelect,
          child: Container(
            height: 20,
            // color: Colors.blue,
            alignment: Alignment.centerLeft,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(title, style: const TextStyle(fontSize: 12)),
          ),
        ),
        Expanded(
          child: Stack(
            children: [
              InAppWebView(
                key: webViewKey,
                initialUrlRequest: URLRequest(url: WebUri(website)),
                initialSettings: settings,
                onWebViewCreated: (controller) {
                  webViewController = controller;
                },
                onLoadStart: (controller, url) {
                  setState(() {
                    urlController.text = website;
                  });
                },
                onProgressChanged: (controller, progress) {
                  setState(() {
                    this.progress = progress / 100;
                    urlController.text = website;
                  });
                },
                onPermissionRequest: (controller, origin) async {
                  return PermissionResponse(
                    action: PermissionResponseAction.GRANT,
                  );
                },
                onLoadStop: (controller, url) async {
                  setState(() {
                    // this.url = url.toString();
                    urlController.text = website;
                  });
                },
                onReceivedServerTrustAuthRequest: (
                  controller,
                  challenge,
                ) async {
                  return ServerTrustAuthResponse(
                    action: ServerTrustAuthResponseAction.PROCEED,
                  );
                },
                onReceivedHttpAuthRequest: (controller, challenge) async {
                  return HttpAuthResponse(
                    action:
                        HttpAuthResponseAction.USE_SAVED_HTTP_AUTH_CREDENTIALS,
                  );
                },
              ),
              progress < 1.0
                  ? LinearProgressIndicator(value: progress)
                  : Container(),
            ],
          ),
        ),
      ],
    );
    //   ),
    // );
  }
}
