import 'local_settings.dart';

enum CameraMode { allExternal, front, interior }

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
