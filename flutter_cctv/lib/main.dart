import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';

import 'cameras.dart';
import 'dropbox-api.dart';
import 'camera_window.dart';
import 'local_settings.dart';

HttpAuthCredentialDatabase httpAuthCredentialDatabase =
    HttpAuthCredentialDatabase.instance();

void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});
  @override
  State createState() => MyAppState();
}

class MyAppState extends State<MyApp> {
  // final HttpClient client = HttpClient();
  String oauthToken = "BLANK";
  String username = "";
  String password = "";
  String extHost = "";
  CameraScreen cameraScreen = CameraScreen();

  @override
  void initState() {
    Future<Secret> secret =
        SecretLoader(secretPath: "assets/api-key.json").load();
    secret.then((Secret secret) {
      // Future<String> keyString = rootBundle.loadString('assets/connect-data');
      // keyString.then((String str) {
      //   LocalSendReceive.setKeys(str);
      // });
      setState(() {
        oauthToken = secret.apiKey;
        username = secret.username;
        password = secret.password;
      });
      DropBoxAPIFn.globalOauthToken = oauthToken;
      //Get the external IP address of the cameras from the dropbox file to override the hardcoded IP address
      DropBoxAPIFn.getDropBoxFile(
        fileToDownload: "/external_ip.txt",
        callback: processIPAddress,
        contentType: ContentType.text,
        timeoutSecs: 30,
      );
    });
    //Check if we are on local LAN
    areWeOnLocalNetwork(
      (onlan) => setState(() {
        CameraEntry.onLocalLan = onlan;
        // cameraScreen.cameraState.refresh();
      }),
    );
    super.initState();
  }

  void processIPAddress(String filename, String contents) {
    setState(() {
      //Read contents of file and set the external IP address
      extHost = contents.trim();
      URLCredential creds = URLCredential(
        username: username,
        password: password,
      );

      //Set the credentials for the external cameras ip
      for (int i = 0; i < 10; i++) {
        httpAuthCredentialDatabase.setHttpAuthCredential(
          protectionSpace: URLProtectionSpace(
            host: extHost,
            protocol: "https",
            realm: "",
            port: extStartPort + i,
          ),
          credential: creds,
        );
      }
      CameraEntry.extHost = extHost;
    });
    prewarmAllCameras();
  }

  Future<void> prewarmAllCameras() async {
    List<Future> futures = [];

    for (int i = 0; i < 10; i++) {
      final port = extStartPort + i;
      final url = "https://$extHost:$port/";

      futures.add(warmCamera(url));
    }

    await Future.wait(futures);
  }

  Future<void> warmCamera(String url) async {
    try {
      final client =
          HttpClient()
            ..badCertificateCallback =
                (cert, host, port) => true; // allow self-signed

      final request = await client.openUrl("HEAD", Uri.parse(url));
      await request.close(); // we don't care about the response body
    } catch (_) {
      // ignore failures — the goal is to trigger auth
    }
  }

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    // ScreenType screenType = FormFactor.getScreenType(context);
    return MaterialApp(
      title: 'CCTV Display',
      theme: ThemeData(
        useMaterial3: true,

        // Define the default brightness and colors.
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.dark,
        ), // This is the theme of your application.
        // primarySwatch: Colors.blue,
        fontFamily: 'Roboto',
      ),
      home: CameraScreen(),
    );
  }

  @override
  void dispose() {
    // client.close();
    super.dispose();
  }
}

class CameraScreen extends StatefulWidget {
  CameraScreen({super.key});
  late _CameraScreenState cameraState;

  @override
  State<CameraScreen> createState() {
    cameraState = _CameraScreenState();
    return cameraState;
  }
}

class _CameraScreenState extends State<CameraScreen> {
  CameraMode mode = CameraMode.allExternal;
  CameraMode previousMode = CameraMode.allExternal;
  int selectedCamera = 0;

  @override
  void initState() {
    super.initState();
  }

  void refresh() {
    setState(() => mode = mode);
  }

  @override
  Widget build(BuildContext context) {
    if (CameraEntry.extHost == "") {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return PopScope(
      //Go to previous display mode if in singleWindow mode
      canPop: mode != CameraMode.singleWindow,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop && mode == CameraMode.singleWindow) {
          setState(() {
            mode = previousMode;
            selectedCamera = 0;
          });
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text("Camera Viewer", style: TextStyle(fontSize: 18)),
          titleSpacing: 0,
          toolbarHeight: 34,

          actions: [
            TextButton(
              onPressed: () => setState(() => mode = CameraMode.all),
              child: const Text("All", style: TextStyle(fontSize: 16)),
            ),
            TextButton(
              onPressed: () => setState(() => mode = CameraMode.allExternal),
              child: const Text("Ext", style: TextStyle(fontSize: 16)),
            ),
            TextButton(
              onPressed: () => setState(() => mode = CameraMode.interior),
              child: const Text("Int", style: TextStyle(fontSize: 16)),
            ),
            TextButton(
              onPressed: () => setState(() => mode = CameraMode.front),
              child: const Text("Front", style: TextStyle(fontSize: 16)),
            ),
            TextButton(
              onPressed: () => setState(() => mode = CameraMode.frontBack),
              child: const Text("F&B", style: TextStyle(fontSize: 16)),
            ),
            TextButton(
              onPressed: () => setState(() => mode = CameraMode.sides),
              child: const Text("Sides", style: TextStyle(fontSize: 16)),
            ),
          ],
        ),
        body: _buildLayout(),
      ),
    );
  }

  Widget _buildLayout() {
    switch (mode) {
      case CameraMode.singleWindow:
        return _cameraBox(selectedCamera);

      case CameraMode.front:
        return _twoSideBySide(3, 9);

      case CameraMode.frontBack:
        return Column(
          children: [
            Expanded(child: _cameraBox(6)),
            Expanded(child: _cameraBox(9)),
          ],
        );

      case CameraMode.interior:
        return _twoSideBySide(5, 8);

      case CameraMode.sides:
        return Row(
          children: [
            Expanded(child: _cameraBox(3)),
            Expanded(child: _cameraBox(2)),
            Expanded(child: _cameraBox(4)),
            Expanded(child: _cameraBox(7)),
          ],
        );

      case CameraMode.allExternal:
        return Column(
          children: [
            Expanded(child: _twoSideBySide(6, 9)),
            Expanded(
              child: Row(
                children: [
                  Expanded(child: _cameraBox(3)),
                  Expanded(child: _cameraBox(2)),
                  Expanded(child: _cameraBox(4)),
                  Expanded(child: _cameraBox(7)),
                ],
              ),
            ),
          ],
        );
      case CameraMode.all:
        return Column(
          children: [
            Expanded(
              child: Row(
                children: [
                  Expanded(child: _cameraBox(6)),
                  Expanded(child: _cameraBox(9)),
                  Expanded(child: _cameraBox(5)),
                  Expanded(child: _cameraBox(8)),
                ],
              ),
            ),

            Expanded(
              child: Row(
                children: [
                  Expanded(child: _cameraBox(3)),
                  Expanded(child: _cameraBox(2)),
                  Expanded(child: _cameraBox(4)),
                  Expanded(child: _cameraBox(7)),
                ],
              ),
            ),
          ],
        );
    }
  }

  Widget _twoSideBySide(int a, int b) {
    return Row(
      children: [
        Expanded(child: _cameraBox(a)),
        Expanded(child: _cameraBox(b)),
      ],
    );
  }

  Widget _cameraBox(int a) {
    CameraEntry entry = CameraEntry.fromStationNumber(a);
    return CameraWindow(
      key: ValueKey(entry.url),
      entry: entry,
      onSelect:
          () => setState(() {
            previousMode = mode;
            mode = CameraMode.singleWindow;
            selectedCamera = a; // which camera was tapped
          }),
    );
  }
}
