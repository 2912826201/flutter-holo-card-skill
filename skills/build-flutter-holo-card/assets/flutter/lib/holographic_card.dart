import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import 'holographic_card_painter.dart';

class HolographicCard extends StatefulWidget {
  const HolographicCard({
    required this.cardImage,
    required this.backgroundImage,
    required this.foregroundImage,
    required this.characterContourImage,
    required this.characterBloomImage,
    this.characterImage,
    this.shaderAssetPath = 'shaders/holographic_card.frag',
    this.depth = 0,
    this.effectStrength = 1,
    this.contourGlowStrength = 0.15,
    this.viewSensitivity = 4,
    this.maxTiltRadians = 0.28,
    this.semanticLabel = 'Interactive holographic card',
    super.key,
  }) : assert(depth >= -3 && depth <= 3),
       assert(effectStrength >= 0 && effectStrength <= 1),
       assert(contourGlowStrength >= 0 && contourGlowStrength <= 3),
       assert(viewSensitivity >= 1 && viewSensitivity <= 5),
       assert(maxTiltRadians >= 0 && maxTiltRadians <= 0.35);

  final ImageProvider cardImage;
  final ImageProvider backgroundImage;
  final ImageProvider foregroundImage;
  final ImageProvider? characterImage;
  final ImageProvider characterContourImage;
  final ImageProvider characterBloomImage;
  final String shaderAssetPath;
  final double depth;
  final double effectStrength;
  final double contourGlowStrength;
  final double viewSensitivity;
  final double maxTiltRadians;
  final String semanticLabel;

  @override
  State<HolographicCard> createState() => _HolographicCardState();
}

class _HolographicCardState extends State<HolographicCard>
    with TickerProviderStateMixin {
  late final AnimationController _returnController;
  late final AnimationController _effectController;

  _Resources? _resources;
  Offset _tilt = Offset.zero;
  Offset? _dragStartPosition;
  Offset? _dragStartTilt;
  Animation<Offset>? _returnAnimation;
  double _effectActivation = 0;
  double _effectStartActivation = 0;
  double _effectTargetActivation = 0;
  Curve _effectCurve = Curves.linear;
  int _loadGeneration = 0;

  @override
  void initState() {
    super.initState();
    _returnController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 220),
    )..addListener(_handleReturn);
    _effectController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 180),
    )..addListener(_handleEffectTransition);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_loadGeneration == 0) {
      _startLoading();
    }
  }

  @override
  void didUpdateWidget(HolographicCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.cardImage != widget.cardImage ||
        oldWidget.backgroundImage != widget.backgroundImage ||
        oldWidget.foregroundImage != widget.foregroundImage ||
        oldWidget.characterImage != widget.characterImage ||
        oldWidget.characterContourImage != widget.characterContourImage ||
        oldWidget.characterBloomImage != widget.characterBloomImage ||
        oldWidget.shaderAssetPath != widget.shaderAssetPath) {
      _startLoading();
    }
  }

  void _startLoading() {
    final int generation = ++_loadGeneration;
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
    final List<ui.Image> loadedImages = [];
    try {
      Future<ui.Image> load(ImageProvider provider) async {
        final ui.Image image = await _loadImage(provider, configuration);
        loadedImages.add(image);
        return image;
      }

      final ui.Image cardMaskImage = await load(widget.cardImage);
      final ui.Image backgroundImage = await load(widget.backgroundImage);
      final ui.Image foregroundImage = await load(widget.foregroundImage);
      final ImageProvider? characterProvider = widget.characterImage;
      final ui.Image? characterImage = characterProvider == null
          ? null
          : await load(characterProvider);
      final ui.Image contourImage = await load(widget.characterContourImage);
      final ui.Image bloomImage = await load(widget.characterBloomImage);
      final ui.FragmentProgram program = await ui.FragmentProgram.fromAsset(
        widget.shaderAssetPath,
      );
      return _Resources(
        cardMaskImage: cardMaskImage,
        backgroundImage: backgroundImage,
        foregroundImage: foregroundImage,
        characterImage: characterImage,
        contourImage: contourImage,
        bloomImage: bloomImage,
        shader: program.fragmentShader(),
      );
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
    listener = ImageStreamListener(
      (ImageInfo info, bool synchronousCall) {
        stream.removeListener(listener);
        if (!completer.isCompleted) {
          completer.complete(info.image);
        }
      },
      onError: (Object error, StackTrace? stackTrace) {
        stream.removeListener(listener);
        if (!completer.isCompleted) {
          completer.completeError(error, stackTrace);
        }
      },
    );
    stream.addListener(listener);
    return completer.future;
  }

  void _updateHover(Offset localPosition, Size size) {
    if (size.isEmpty) {
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

  void _beginDrag(Offset localPosition, Size size) {
    if (size.isEmpty) {
      return;
    }
    _returnController.stop();
    _returnAnimation = null;
    _dragStartPosition = localPosition;
    _dragStartTilt = _tilt;
  }

  void _updateDrag(Offset localPosition, Size size) {
    if (size.isEmpty) {
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

  void _endDrag() {
    _dragStartPosition = null;
    _dragStartTilt = null;
    _resetTilt();
  }

  void _resetTilt() {
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
    _resources?.dispose();
    _returnController.dispose();
    _effectController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final _Resources? resources = _resources;
    if (resources == null) {
      return Semantics(
        image: true,
        label: widget.semanticLabel,
        child: Image(
          image: widget.cardImage,
          fit: BoxFit.fill,
          filterQuality: FilterQuality.high,
        ),
      );
    }

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final Size size = constraints.biggest;
        final Matrix4 perspective = Matrix4.identity()
          ..setEntry(3, 2, 0.0012)
          ..rotateX(_tilt.dy * widget.maxTiltRadians)
          ..rotateY(_tilt.dx * widget.maxTiltRadians);
        final Offset shaderView = Offset(
          (math.sin(_tilt.dx * widget.maxTiltRadians) *
                  0.65 *
                  widget.viewSensitivity)
              .clamp(-0.5, 0.5)
              .toDouble(),
          (math.sin(_tilt.dy * widget.maxTiltRadians) *
                  0.65 *
                  widget.viewSensitivity)
              .clamp(-0.5, 0.5)
              .toDouble(),
        );

        return Semantics(
          image: true,
          label: widget.semanticLabel,
          child: MouseRegion(
            onEnter: (_) => _activateEffect(),
            onHover: (event) => _updateHover(event.localPosition, size),
            onExit: (_) {
              _resetTilt();
              _deactivateEffect();
            },
            child: Listener(
              behavior: HitTestBehavior.opaque,
              onPointerDown: (event) {
                _beginDrag(event.localPosition, size);
                _activateEffect();
              },
              onPointerUp: (_) {
                _endDrag();
                _deactivateEffect();
              },
              onPointerCancel: (_) {
                _endDrag();
                _deactivateEffect();
              },
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onPanUpdate: (details) =>
                    _updateDrag(details.localPosition, size),
                child: Transform(
                  key: const ValueKey('holographic-card-transform'),
                  alignment: Alignment.center,
                  transform: perspective,
                  child: RepaintBoundary(
                    key: const ValueKey('holographic-card-renderer'),
                    child: resources.hasCharacterLayer
                        ? Stack(
                            clipBehavior: Clip.none,
                            fit: StackFit.expand,
                            children: [
                              Positioned(
                                left: -size.width * 0.3,
                                top: -size.height * 0.3,
                                width: size.width * 1.6,
                                height: size.height * 1.6,
                                child: CustomPaint(
                                  painter: _createPainter(
                                    resources,
                                    shaderView,
                                  ),
                                  child: const SizedBox.expand(),
                                ),
                              ),
                            ],
                          )
                        : CustomPaint(
                            painter: _createPainter(resources, shaderView),
                            child: const SizedBox.expand(),
                          ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  HolographicCardPainter _createPainter(
    _Resources resources,
    Offset shaderView,
  ) {
    return HolographicCardPainter(
      shader: resources.shader,
      cardMaskImage: resources.cardMaskImage,
      backgroundImage: resources.backgroundImage,
      foregroundImage: resources.foregroundImage,
      characterImage: resources.characterImage ?? resources.foregroundImage,
      characterContourImage: resources.contourImage,
      characterBloomImage: resources.bloomImage,
      view: shaderView,
      depth: widget.depth,
      effectStrength: widget.effectStrength,
      contourGlowStrength: widget.contourGlowStrength,
      effectActivation: _effectActivation,
      hasCharacterLayer: resources.hasCharacterLayer,
    );
  }
}

class _Resources {
  const _Resources({
    required this.cardMaskImage,
    required this.backgroundImage,
    required this.foregroundImage,
    required this.characterImage,
    required this.contourImage,
    required this.bloomImage,
    required this.shader,
  });

  final ui.Image cardMaskImage;
  final ui.Image backgroundImage;
  final ui.Image foregroundImage;
  final ui.Image? characterImage;
  final ui.Image contourImage;
  final ui.Image bloomImage;
  final ui.FragmentShader shader;

  bool get hasCharacterLayer => characterImage != null;

  void dispose() {
    cardMaskImage.dispose();
    backgroundImage.dispose();
    foregroundImage.dispose();
    characterImage?.dispose();
    contourImage.dispose();
    bloomImage.dispose();
    shader.dispose();
  }
}
