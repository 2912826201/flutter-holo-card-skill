import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import 'holographic_card_painter.dart';

enum HolographicCardMode { height, medium, low }

/// Pose uses x right and y up, each in [-1, 1]. Internal depth is independent
/// of material sensitivity and optional physical rotation.
class HolographicCard extends StatefulWidget {
  const HolographicCard({
    required this.cardImage,
    required this.backgroundImage,
    required this.foregroundImage,
    this.depth = 1,
    this.backgroundMotionStrength = 1,
    this.backgroundSourceRect = const Rect.fromLTWH(
      8 / 116,
      8 / 116,
      100 / 116,
      100 / 116,
    ),
    required this.foregroundContourImage,
    required this.foregroundBloomImage,
    this.foilImage = const AssetImage(
      'assets/holographic_foil.png',
      package: 'build_flutter_holo_card_template',
    ),
    this.shaderAssetPath,
    this.effectStrength = 0.65,
    this.foilStrength = 1,
    this.contourGlowStrength = 0.55,
    this.idleEffectStrength = 0.22,
    this.viewSensitivity = 1,
    this.maxTiltRadians = 0.24,
    this.applyPhysicalTilt = true,
    this.autoPlay = false,
    this.controlledTilt,
    this.controlledActivation,
    this.onError,
    this.semanticLabel = 'Interactive holographic card',
    super.key,
  }) : mode = HolographicCardMode.height,
       assert(
         depth >= 0 && depth <= 3,
         'Negative depth is no longer supported; migrate to background distance 0–3.',
       ),
       assert(effectStrength >= 0 && effectStrength <= 1),
       assert(foilStrength >= 0 && foilStrength <= 1),
       assert(contourGlowStrength >= 0 && contourGlowStrength <= 1),
       assert(maxTiltRadians >= 0 && maxTiltRadians <= 0.35);

  const HolographicCard.height({
    required this.cardImage,
    required this.backgroundImage,
    required this.foregroundImage,
    this.depth = 1,
    this.backgroundMotionStrength = 1,
    this.backgroundSourceRect = const Rect.fromLTWH(
      8 / 116,
      8 / 116,
      100 / 116,
      100 / 116,
    ),
    required this.foregroundContourImage,
    required this.foregroundBloomImage,
    this.foilImage = const AssetImage(
      'assets/holographic_foil.png',
      package: 'build_flutter_holo_card_template',
    ),
    this.shaderAssetPath,
    this.effectStrength = 0.65,
    this.foilStrength = 1,
    this.contourGlowStrength = 0.55,
    this.idleEffectStrength = 0.22,
    this.viewSensitivity = 1,
    this.maxTiltRadians = 0.24,
    this.applyPhysicalTilt = true,
    this.autoPlay = false,
    this.controlledTilt,
    this.controlledActivation,
    this.onError,
    this.semanticLabel = 'Interactive holographic card',
    super.key,
  }) : mode = HolographicCardMode.height,
       assert(
         depth >= 0 && depth <= 3,
         'Negative depth is no longer supported; migrate to background distance 0–3.',
       ),
       assert(effectStrength >= 0 && effectStrength <= 1),
       assert(foilStrength >= 0 && foilStrength <= 1),
       assert(contourGlowStrength >= 0 && contourGlowStrength <= 1),
       assert(maxTiltRadians >= 0 && maxTiltRadians <= 0.35);

  const HolographicCard.medium({
    required this.cardImage,
    required this.foregroundContourImage,
    required this.foregroundBloomImage,
    this.foilImage = const AssetImage(
      'assets/holographic_foil.png',
      package: 'build_flutter_holo_card_template',
    ),
    this.shaderAssetPath,
    this.effectStrength = 0.65,
    this.foilStrength = 1,
    this.contourGlowStrength = 0.55,
    this.idleEffectStrength = 0.22,
    this.viewSensitivity = 1,
    this.maxTiltRadians = 0.24,
    this.applyPhysicalTilt = true,
    this.autoPlay = false,
    this.controlledTilt,
    this.controlledActivation,
    this.onError,
    this.semanticLabel = 'Interactive holographic card',
    super.key,
  }) : mode = HolographicCardMode.medium,
       backgroundImage = null,
       foregroundImage = null,
       depth = 0,
       backgroundMotionStrength = 0,
       backgroundSourceRect = const Rect.fromLTWH(0, 0, 1, 1),
       assert(effectStrength >= 0 && effectStrength <= 1),
       assert(foilStrength >= 0 && foilStrength <= 1),
       assert(contourGlowStrength >= 0 && contourGlowStrength <= 1),
       assert(maxTiltRadians >= 0 && maxTiltRadians <= 0.35);

  const HolographicCard.low({
    required this.cardImage,
    this.foilImage = const AssetImage(
      'assets/holographic_foil.png',
      package: 'build_flutter_holo_card_template',
    ),
    this.shaderAssetPath,
    this.effectStrength = 0.65,
    this.foilStrength = 1,
    this.contourGlowStrength = 0.55,
    this.idleEffectStrength = 0.22,
    this.viewSensitivity = 1,
    this.maxTiltRadians = 0.24,
    this.applyPhysicalTilt = true,
    this.autoPlay = false,
    this.controlledTilt,
    this.controlledActivation,
    this.onError,
    this.semanticLabel = 'Interactive holographic card',
    super.key,
  }) : mode = HolographicCardMode.low,
       backgroundImage = null,
       foregroundImage = null,
       depth = 0,
       backgroundMotionStrength = 0,
       backgroundSourceRect = const Rect.fromLTWH(0, 0, 1, 1),
       foregroundContourImage = null,
       foregroundBloomImage = null,
       assert(effectStrength >= 0 && effectStrength <= 1),
       assert(foilStrength >= 0 && foilStrength <= 1),
       assert(contourGlowStrength >= 0 && contourGlowStrength <= 1),
       assert(maxTiltRadians >= 0 && maxTiltRadians <= 0.35);

  final HolographicCardMode mode;
  final ImageProvider cardImage;
  final ImageProvider foilImage;
  final ImageProvider? backgroundImage, foregroundImage;
  final ImageProvider? foregroundContourImage, foregroundBloomImage;
  final String? shaderAssetPath;
  final Rect backgroundSourceRect;

  /// Foil-only intensity. Zero keeps contour light; effectStrength zero disables both.
  final double foilStrength;

  /// Multiplier for height background recession, capped to valid overscan.
  final double backgroundMotionStrength;
  final double depth, effectStrength, contourGlowStrength, idleEffectStrength;
  final double viewSensitivity, maxTiltRadians;
  final bool applyPhysicalTilt, autoPlay;
  final Offset? controlledTilt;
  final double? controlledActivation;
  final void Function(Object error, StackTrace stack)? onError;
  final String semanticLabel;

  @override
  State<HolographicCard> createState() => _HolographicCardState();
}

class _HolographicCardState extends State<HolographicCard>
    with TickerProviderStateMixin, WidgetsBindingObserver {
  late final AnimationController _returnController;
  late final AnimationController _autoController;
  bool _foreground = true;
  late final AnimationController _effectController;

  _Resources? _resources;
  final Set<void Function()> _cancelLoads = {};
  bool get _reduceMotion => MediaQuery.disableAnimationsOf(context);
  Offset _tilt = Offset.zero;
  Offset? _dragStartPosition;
  Offset? _dragStartTilt;
  int? _activePointer;
  bool _hovering = false;
  Animation<Offset>? _returnAnimation;
  double _effectActivation = 0;
  double _effectStartActivation = 0;
  double _effectTargetActivation = 0;
  Curve _effectCurve = Curves.linear;
  int _loadGeneration = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _autoController =
        AnimationController(vsync: this, duration: const Duration(seconds: 8))
          ..addListener(() {
            if (mounted) setState(() {});
          });
    _returnController =
        AnimationController(
            vsync: this,
            duration: const Duration(milliseconds: 240),
          )
          ..addListener(_handleReturn)
          ..addStatusListener((status) {
            if (status == AnimationStatus.completed && mounted) _syncAutoPlay();
          });
    _effectController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 180),
    )..addListener(_handleEffectTransition);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncAutoPlay();
    if (_loadGeneration == 0) {
      _startLoading();
    }
  }

  @override
  void didUpdateWidget(HolographicCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    _syncAutoPlay();
    if (oldWidget.backgroundSourceRect != widget.backgroundSourceRect ||
        oldWidget.mode != widget.mode ||
        oldWidget.foilImage != widget.foilImage ||
        oldWidget.cardImage != widget.cardImage ||
        oldWidget.backgroundImage != widget.backgroundImage ||
        oldWidget.foregroundImage != widget.foregroundImage ||
        oldWidget.foregroundContourImage != widget.foregroundContourImage ||
        oldWidget.foregroundBloomImage != widget.foregroundBloomImage ||
        oldWidget.shaderAssetPath != widget.shaderAssetPath) {
      _startLoading();
    }
  }

  void _syncAutoPlay() {
    final active =
        widget.autoPlay &&
        widget.controlledTilt == null &&
        !_hovering &&
        _activePointer == null &&
        !_returnController.isAnimating &&
        !_reduceMotion &&
        _foreground &&
        TickerMode.valuesOf(context).enabled;
    if (active) {
      if (!_autoController.isAnimating) _autoController.repeat();
    } else {
      _autoController.stop();
    }
    if (_reduceMotion || !_foreground) {
      _returnController.stop();
      _effectController.stop();
      _tilt = Offset.zero;
      _effectActivation = 0;
      _returnAnimation = null;
      if (!_foreground) {
        _activePointer = null;
        _hovering = false;
        _dragStartPosition = null;
        _dragStartTilt = null;
      }
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _foreground = state == AppLifecycleState.resumed;
    _syncAutoPlay();
    if (mounted) setState(() {});
  }

  void _startLoading() {
    final int generation = ++_loadGeneration;
    for (final cancel in _cancelLoads.toList()) {
      cancel();
    }
    _resources?.dispose();
    _resources = null;
    final ImageConfiguration configuration = createLocalImageConfiguration(
      context,
    );
    unawaited(
      _loadResources(configuration).then(
        (resources) {
          if (!mounted || generation != _loadGeneration) {
            resources.dispose();
            return;
          }
          setState(() => _resources = resources);
        },
        onError: (Object error, StackTrace stackTrace) {
          if (!mounted || generation != _loadGeneration) {
            return;
          }
          if (widget.onError != null) {
            widget.onError!(error, stackTrace);
            return;
          }
          FlutterError.reportError(
            FlutterErrorDetails(
              exception: error,
              stack: stackTrace,
              library: 'holographic card',
            ),
          );
        },
      ),
    );
  }

  Future<_Resources> _loadResources(ImageConfiguration configuration) async {
    final config = widget;
    final generation = _loadGeneration;
    final List<ui.Image> loadedImages = [];
    try {
      Future<ui.Image> load(ImageProvider provider) async {
        final ui.Image image = await _loadImage(provider, configuration);
        loadedImages.add(image);
        if (!mounted || generation != _loadGeneration)
          throw StateError('Superseded load');
        return image;
      }

      final ui.Image cardMaskImage = await load(config.cardImage);
      if (config.depth < 0 || config.depth > 3) {
        throw ArgumentError(
          'Migrate depth to background distance 0–3; negative depth was removed.',
        );
      }
      final foil = await load(config.foilImage);
      final images = <ui.Image>[cardMaskImage, foil];
      if (config.mode != HolographicCardMode.low) {
        images.add(await load(config.foregroundContourImage!));
        images.add(await load(config.foregroundBloomImage!));
      }
      if (config.mode == HolographicCardMode.height) {
        images.add(await load(config.backgroundImage!));
        images.add(await load(config.foregroundImage!));
        final rect = config.backgroundSourceRect;
        final bg = images[4];
        if ((rect.width * bg.width - cardMaskImage.width).abs() > 1.5 ||
            (rect.height * bg.height - cardMaskImage.height).abs() > 1.5 ||
            rect.left < 0.06 ||
            rect.top < 0.06 ||
            rect.right > 0.94 ||
            rect.bottom > 0.94) {
          throw ArgumentError(
            'height requires an extended background and its source rectangle (8% per side).',
          );
        }
      }
      for (var i = 2; i < images.length; i++) {
        if (i == 4) continue;
        if (images[i].width != cardMaskImage.width ||
            images[i].height != cardMaskImage.height) {
          throw ArgumentError(
            'Card, foreground, contour and bloom must share the exact source canvas.',
          );
        }
      }
      final name = config.mode == HolographicCardMode.height
          ? 'holographic_card'
          : config.mode.name;
      final program = await ui.FragmentProgram.fromAsset(
        config.shaderAssetPath ??
            'packages/build_flutter_holo_card_template/shaders/$name.frag',
      );
      return _Resources(images, program.fragmentShader());
    } catch (_) {
      for (final ui.Image image in loadedImages) {
        image.dispose();
      }
      rethrow;
    }
  }

  Future<ui.Image> _loadImage(
    ImageProvider provider,
    ImageConfiguration configuration,
  ) {
    final Completer<ui.Image> completer = Completer<ui.Image>();
    final ImageStream stream = provider.resolve(configuration);
    late final ImageStreamListener listener;
    late final void Function() cancel;
    cancel = () {
      stream.removeListener(listener);
      _cancelLoads.remove(cancel);
      if (!completer.isCompleted)
        completer.completeError(
          StateError('Image load superseded or disposed'),
        );
    };
    listener = ImageStreamListener(
      (ImageInfo info, bool synchronousCall) {
        stream.removeListener(listener);
        _cancelLoads.remove(cancel);
        if (!completer.isCompleted) completer.complete(info.image.clone());
        info.dispose();
      },
      onError: (Object error, StackTrace? stackTrace) {
        stream.removeListener(listener);
        _cancelLoads.remove(cancel);
        if (!completer.isCompleted) completer.completeError(error, stackTrace);
      },
    );
    _cancelLoads.add(cancel);
    stream.addListener(listener);
    return completer.future;
  }

  void _updateHover(Offset localPosition, Size size) {
    if (size.isEmpty || _activePointer != null) {
      return;
    }
    _returnController.stop();
    _returnAnimation = null;
    final Offset next = Offset(
      (localPosition.dx / size.width * 2 - 1).clamp(-1.0, 1.0),
      -(localPosition.dy / size.height * 2 - 1).clamp(-1.0, 1.0),
    );
    if (next != _tilt) {
      setState(() => _tilt = next);
    }
  }

  void _stopAutoForInteraction() {
    if (_autoController.isAnimating) {
      if (_tilt.distance < .001) {
        final phase = _autoController.value * math.pi * 2;
        _tilt = Offset(math.sin(phase) * .55, math.sin(phase * 2) * .35);
      }
      _autoController.stop();
      _autoController.value = 0;
    }
  }

  void _beginDrag(int pointer, Offset localPosition, Size size) {
    if (size.isEmpty || _activePointer != null) {
      return;
    }
    _stopAutoForInteraction();
    _returnController.stop();
    _returnAnimation = null;
    _activePointer = pointer;
    _dragStartPosition = localPosition;
    _dragStartTilt = _tilt;
    _activateEffect();
  }

  void _updateDrag(Offset localPosition, Size size) {
    if (size.isEmpty || _activePointer == null) {
      return;
    }
    final Offset startPosition = _dragStartPosition ?? localPosition;
    final Offset startTilt = _dragStartTilt ?? _tilt;
    final Offset next = Offset(
      (startTilt.dx + (localPosition.dx - startPosition.dx) / size.width * 2)
          .clamp(-1.0, 1.0),
      (startTilt.dy + (startPosition.dy - localPosition.dy) / size.height * 2)
          .clamp(-1.0, 1.0),
    );
    if (next != _tilt) {
      setState(() => _tilt = next);
    }
  }

  void _endDrag(int pointer) {
    if (_activePointer != pointer) {
      return;
    }
    _activePointer = null;
    _dragStartPosition = null;
    _dragStartTilt = null;
    _resetTilt();
    if (!_hovering) {
      _deactivateEffect();
    }
    _syncAutoPlay();
  }

  void _resetTilt() {
    if (_reduceMotion) {
      setState(() => _tilt = Offset.zero);
      return;
    }
    if (_tilt == Offset.zero) {
      return;
    }
    _returnAnimation = Tween<Offset>(begin: _tilt, end: Offset.zero).animate(
      CurvedAnimation(parent: _returnController, curve: Curves.easeOutCubic),
    );
    _returnController.forward(from: 0);
  }

  void _handleReturn() {
    final Animation<Offset>? animation = _returnAnimation;
    if (animation != null) {
      setState(() => _tilt = animation.value);
    }
  }

  void _activateEffect() {
    _startEffectTransition(
      targetActivation: 1,
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOutCubic,
    );
  }

  void _deactivateEffect() {
    _startEffectTransition(
      targetActivation: 0,
      duration: const Duration(milliseconds: 260),
      curve: Curves.easeOutCubic,
    );
  }

  void _startEffectTransition({
    required double targetActivation,
    required Duration duration,
    required Curve curve,
  }) {
    if (_reduceMotion) {
      setState(() => _effectActivation = targetActivation);
      return;
    }
    if (_effectTargetActivation == targetActivation &&
        (_effectController.isAnimating ||
            _effectActivation == targetActivation)) {
      return;
    }
    _effectController
      ..stop()
      ..duration = duration;
    _effectStartActivation = _effectActivation;
    _effectTargetActivation = targetActivation;
    _effectCurve = curve;
    _effectController.forward(from: 0);
  }

  void _handleEffectTransition() {
    final double progress = _effectCurve.transform(_effectController.value);
    setState(() {
      _effectActivation = ui.lerpDouble(
        _effectStartActivation,
        _effectTargetActivation,
        progress,
      )!;
    });
  }

  @override
  void dispose() {
    _loadGeneration++;
    for (final cancel in _cancelLoads.toList()) {
      cancel();
    }
    _resources?.dispose();
    WidgetsBinding.instance.removeObserver(this);
    _autoController.dispose();
    _returnController.dispose();
    _effectController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.backgroundMotionStrength.isFinite ||
        widget.backgroundMotionStrength < 0 ||
        widget.backgroundMotionStrength > 4) {
      throw ArgumentError(
        'backgroundMotionStrength must be finite and within 0–4.',
      );
    }
    if (!widget.depth.isFinite || widget.depth < 0 || widget.depth > 3) {
      throw ArgumentError(
        'Negative depth removed: migrate to background distance 0–3.',
      );
    }
    if (!widget.maxTiltRadians.isFinite ||
        widget.maxTiltRadians < 0 ||
        widget.maxTiltRadians > .35) {
      throw ArgumentError(
        'maxTiltRadians must be between 0 and 0.35 for overscan safety.',
      );
    }
    final _Resources? resources = _resources;
    if (resources == null) {
      return Semantics(
        image: true,
        label: widget.semanticLabel,
        child: Image(
          image: widget.cardImage,
          fit: BoxFit.contain,
          filterQuality: FilterQuality.high,
        ),
      );
    }

    final double aspectRatio =
        resources.cardMaskImage.width / resources.cardMaskImage.height;
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool boundedWidth = constraints.hasBoundedWidth;
        final bool boundedHeight = constraints.hasBoundedHeight;
        if (boundedWidth && boundedHeight) {
          final double maxWidth = constraints.maxWidth;
          final double maxHeight = constraints.maxHeight;
          final double width = math.min(maxWidth, maxHeight * aspectRatio);
          final double height = width / aspectRatio;
          return Align(
            alignment: Alignment.center,
            child: SizedBox(
              width: width,
              height: height,
              child: _buildCard(resources, Size(width, height)),
            ),
          );
        }
        if (boundedWidth) {
          final double width = constraints.maxWidth;
          final double height = width / aspectRatio;
          return SizedBox(
            width: width,
            height: height,
            child: _buildCard(resources, Size(width, height)),
          );
        }
        if (boundedHeight) {
          final double height = constraints.maxHeight;
          final double width = height * aspectRatio;
          return SizedBox(
            width: width,
            height: height,
            child: _buildCard(resources, Size(width, height)),
          );
        }
        final double width = math.min(
          320,
          resources.cardMaskImage.width.toDouble(),
        );
        final double height = width / aspectRatio;
        return SizedBox(
          width: width,
          height: height,
          child: _buildCard(resources, Size(width, height)),
        );
      },
    );
  }

  Widget _buildCard(_Resources resources, Size size) {
    final phase = _autoController.value * math.pi * 2;
    final automatic =
        widget.autoPlay &&
        !_reduceMotion &&
        !_hovering &&
        _activePointer == null &&
        _tilt.distance < .001;
    final autoPose = Offset(math.sin(phase) * .55, math.sin(phase * 2) * .35);
    final rawPose = widget.controlledTilt ?? (automatic ? autoPose : _tilt);
    final pose = Offset(
      rawPose.dx.clamp(-1.0, 1.0),
      rawPose.dy.clamp(-1.0, 1.0),
    );
    final physical = widget.applyPhysicalTilt && !_reduceMotion;
    final perspective = Matrix4.identity()
      ..setEntry(3, 2, -1 / (size.width * 2));
    if (physical) {
      perspective.rotateX(pose.dy * widget.maxTiltRadians);
      perspective.rotateY(pose.dx * widget.maxTiltRadians);
    }

    return Semantics(
      image: true,
      label: widget.semanticLabel,
      child: MouseRegion(
        onEnter: (_) {
          _hovering = true;
          _stopAutoForInteraction();
          _activateEffect();
        },
        onHover: (event) => _updateHover(event.localPosition, size),
        onExit: (_) {
          _hovering = false;
          if (_activePointer == null) {
            _resetTilt();
            _deactivateEffect();
          }
          _syncAutoPlay();
        },
        child: Listener(
          behavior: HitTestBehavior.opaque,
          onPointerDown: (event) =>
              _beginDrag(event.pointer, event.localPosition, size),
          onPointerUp: (event) => _endDrag(event.pointer),
          onPointerCancel: (event) => _endDrag(event.pointer),
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onPanUpdate: (details) => _updateDrag(details.localPosition, size),
            child: Transform(
              key: const ValueKey('holographic-card-transform'),
              alignment: Alignment.center,
              transform: perspective,
              child: RepaintBoundary(
                key: const ValueKey('holographic-card-renderer'),
                child: CustomPaint(
                  painter: _createPainter(resources, pose),
                  child: const SizedBox.expand(),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  HolographicCardPainter _createPainter(
    _Resources resources,
    Offset shaderView,
  ) {
    // An autoplay presentation is active even without hover/touch. Keep the
    // full material while interaction takes over; explicit activation wins.
    final presenting =
        widget.autoPlay &&
        !_reduceMotion &&
        _foreground &&
        TickerMode.valuesOf(context).enabled;
    final activation =
        (widget.controlledActivation ?? (presenting ? 1.0 : _effectActivation))
            .clamp(0.0, 1.0);
    return HolographicCardPainter(
      shader: resources.shader,
      images: resources.images,
      mode: widget.mode.name,
      view: shaderView,
      maxTiltRadians: widget.maxTiltRadians,
      viewSensitivity: widget.viewSensitivity,
      depth: _reduceMotion ? 0 : widget.depth,
      sourceRect: widget.backgroundSourceRect,
      backgroundMotionStrength: widget.backgroundMotionStrength,
      effectStrength:
          widget.effectStrength *
          ui.lerpDouble(widget.idleEffectStrength, 1, activation)!,
      contourGlowStrength: widget.contourGlowStrength,
      foilStrength: widget.foilStrength,
    );
  }
}

class _Resources {
  _Resources(this.images, this.shader);
  final List<ui.Image> images;
  ui.Image get cardMaskImage => images.first;
  final ui.FragmentShader shader;
  void dispose() {
    for (final image in images) {
      image.dispose();
    }
    shader.dispose();
  }
}
