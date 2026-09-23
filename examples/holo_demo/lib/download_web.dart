import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';
import 'package:web/web.dart' as web;

void downloadZip(Uint8List bytes, String name) {
  final blob = web.Blob(
    [bytes.toJS].toJS,
    web.BlobPropertyBag(type: 'application/zip'),
  );
  final url = web.URL.createObjectURL(blob);
  final link = web.HTMLAnchorElement()
    ..href = url
    ..download = name;
  web.document.body!.append(link);
  link.click();
  link.remove();
  // Let the browser consume the object URL before releasing its memory.
  Timer(const Duration(seconds: 60), () => web.URL.revokeObjectURL(url));
}
