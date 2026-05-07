import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:dart_ping/dart_ping.dart';

import 'local_settings.dart';

enum CameraMode {
  allExternal,
  all,
  front,
  frontBack,
  interior,
  sides,
  singleWindow,
}

class CameraEntry {
  static String extHost = "";
  static bool onLocalLan = true;
  final String name;
  final String url;

  CameraEntry(this.name, this.url);

  factory CameraEntry.fromStationNumber(int num) {
    String url = "http";
    if (onLocalLan) {
      url += "://";
      url += hostNameById[num] ?? "unknown";
      url += ":$intStartPort";
    } else {
      url += "s://$extHost:";
      url += "${extStartPort + num - 2}";
    }
    String name = extStationNames[num] ?? "Unknown";
    return CameraEntry(name, url);
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
