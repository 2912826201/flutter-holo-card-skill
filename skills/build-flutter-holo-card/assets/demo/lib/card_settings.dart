class CardSettings {
  const CardSettings({
    this.mode = 'height',
    this.effect = .8,
    this.foil = 1,
    this.contour = .55,
    this.depth = 2,
    this.motion = 3,
    this.sensitivity = 1,
    this.tilt = .2,
    this.auto = true,
    this.physical = true,
    this.poseX,
    this.poseY,
  });
  final String mode;
  final double effect, foil, contour, depth, motion, sensitivity, tilt;
  final bool auto, physical;
  final double? poseX, poseY;

  factory CardSettings.fromJson(Map<String, dynamic> data) => CardSettings(
    mode: data['mode'] as String,
    effect: (data['effect'] as num).toDouble(),
    foil: (data['foil'] as num).toDouble(),
    contour: (data['contour'] as num).toDouble(),
    depth: (data['depth'] as num).toDouble(),
    motion: (data['motion'] as num).toDouble(),
    sensitivity: (data['sensitivity'] as num).toDouble(),
    tilt: (data['tilt'] as num).toDouble(),
    auto: data['auto'] as bool,
    physical: data['physical'] as bool,
    poseX: (data['poseX'] as num?)?.toDouble(),
    poseY: (data['poseY'] as num?)?.toDouble(),
  );
  Map<String, dynamic> toJson() => {
    'mode': mode,
    'effect': effect,
    'foil': foil,
    'contour': contour,
    'depth': depth,
    'motion': motion,
    'sensitivity': sensitivity,
    'tilt': tilt,
    'auto': auto,
    'physical': physical,
    'poseX': poseX,
    'poseY': poseY,
  };
}
