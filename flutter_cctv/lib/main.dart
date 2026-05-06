import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:flutter/services.dart';
import 'package:dart_ping/dart_ping.dart';

import 'cameras.dart';
import 'dropbox-api.dart';
import 'camera_window.dart';
import 'local_settings.dart';

HttpAuthCredentialDatabase httpAuthCredentialDatabase =
    HttpAuthCredentialDatabase.instance();

enum CameraMode { allExternal, front, interior }

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
      CameraEntry.extHost = extHost;
      URLCredential creds = URLCredential(
        username: username,
        password: password,
      );

      //Set the credentials for the external cameras ip
      for (int i = 0; i < 8; i++) {
        httpAuthCredentialDatabase.setHttpAuthCredential(
          protectionSpace: URLProtectionSpace(
            host: extHost,
            protocol: "https",
            realm: "Motion",
            port: extStartPort + i,
          ),
          credential: creds,
        );
      }
    });
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

  @override
  void initState() {
    super.initState();
    // loadCameraList().then((list) {
    //   setState(() => cameras = list);
    // });
  }

  void refresh() {
    setState(() => mode = mode);
  }

  void openFullscreen(CameraEntry entry) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => CameraWindow(entry: entry)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Camera Viewer", style: TextStyle(fontSize: 18)),
        titleSpacing: 0,
        toolbarHeight: 34,

        actions: [
          TextButton(
            onPressed: () => setState(() => mode = CameraMode.allExternal),
            child: const Text(
              "External cameras",
              style: TextStyle(fontSize: 16),
            ),
          ),
          TextButton(
            onPressed: () => setState(() => mode = CameraMode.front),
            child: const Text("Front cameras", style: TextStyle(fontSize: 16)),
          ),
          TextButton(
            onPressed: () => setState(() => mode = CameraMode.interior),
            child: const Text(
              "Interior cameras",
              style: TextStyle(fontSize: 16),
            ),
          ),
        ],
      ),
      body: _buildLayout(),
    );
  }

  Widget _buildLayout() {
    switch (mode) {
      case CameraMode.front:
        return _twoSideBySide(3, 9);

      case CameraMode.interior:
        return _twoSideBySide(5, 8);

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
    return CameraWindow(key: ValueKey(entry.url), entry: entry);
  }
}

class SecretLoader {
  final String? secretPath;

  SecretLoader({this.secretPath});
  Future<Secret> load() {
    return rootBundle.loadStructuredData<Secret>(secretPath!, (jsonStr) async {
      final secret = Secret.fromJson(jsonDecode(jsonStr));
      return secret;
    });
  }
}

class Secret {
  final String apiKey;
  final String username;
  final String password;
  final String controlHost;
  Secret({
    this.apiKey = "",
    this.username = "",
    this.password = "",
    this.controlHost = "",
  });
  factory Secret.fromJson(Map<String, dynamic> jsonMap) {
    return Secret(
      apiKey: jsonMap["api_key"],
      username: jsonMap["username"],
      password: jsonMap["password"],
      controlHost: jsonMap["controlHost"],
    );
  }
}

void areWeOnLocalNetwork(Function callback) {
  NetworkInterface.list().then((interfaces) {
    for (NetworkInterface interface in interfaces) {
      for (InternetAddress addr in interface.addresses) {
        if (addr.address.contains('192.168.')) {
          //On a private network
          //Need to ping local thermostat to check we are on the same lan
          Ping('thermostat-host', count: 1).stream.first
              .then((pingData) {
                if (pingData.error == null) {
                  callback(true);
                } else {
                  callback(false);
                }
              })
              .catchError((onError) {
                callback(false);
              });
          break;
        }
      }
    }
  });
}
