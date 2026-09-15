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
    required this.foregroundContourImage,
    required this.foregroundBloomImage,
    this.shaderAssetPath = 'shaders/holographic_card.frag',
    this.depth = 1,
    this.effectStrength = 1,
    this.contourGlowStrength = 0.35,
    this.idleEffectStrength = 0.22,
    this.viewSensitivity = 3,
    this.maxTiltRadians = 0.24,
    this.semanticLabel = 'Interactive holographic card',
    super.key,
  }) : assert(depth >= -3 && depth <= 3),
       assert(effectStrength >= 0 && effectStrength <= 1),
       assert(contourGlowStrength >= 0 && contourGlowStrength <= 3),
       assert(idleEffectStrength >= 0 && idleEffectStrength <= 1),
       assert(viewSensitivity >= 1 && viewSensitivity <= 5),
       assert(maxTiltRadians >= 0 && maxTiltRadians <= 0.35);

  final ImageProvider cardImage;
  final ImageProvider backgroundImage;
  final ImageProvider foregroundImage;
  final ImageProvider foregroundContourImage;
  final ImageProvider foregroundBloomImage;
  final String shaderAssetPath;
  final double depth;
  final double effectStrength;
  final double contourGlowStrength;
  final double idleEffectStrength;
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
    _returnController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 240),
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
        oldWidget.foregroundContourImage != widget.foregroundContourImage ||
        oldWidget.foregroundBloomImage != widget.foregroundBloomImage ||
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
      final ui.Image contourImage = await load(widget.foregroundContourImage);
      final ui.Image bloomImage = await load(widget.foregroundBloomImage);
      final List<ui.Image> contractImages = [
        backgroundImage,
        foregroundImage,
        contourImage,
        bloomImage,
      ];
      if (contractImages.any(
        (image) =>
            image.width != cardMaskImage.width ||
            image.height != cardMaskImage.height,
      )) {
        throw FlutterError(
          'All holographic card images must use the same full canvas.',
        );
      }
      final ui.FragmentProgram program = await ui.FragmentProgram.fromAsset(
        widget.shaderAssetPath,
      );
      return _Resources(
        cardMaskImage: cardMaskImage,
        backgroundImage: backgroundImage,
        foregroundImage: foregroundImage,
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

  void _beginDrag(int pointer, Offset localPosition, Size size) {
    if (size.isEmpty || _activePointer != null) {
      return;
    }
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
        onEnter: (_) {
          _hovering = true;
          _activateEffect();
        },
        onHover: (event) => _updateHover(event.localPosition, size),
        onExit: (_) {
          _hovering = false;
          if (_activePointer == null) {
            _resetTilt();
            _deactivateEffect();
          }
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
                child: Stack(
                  clipBehavior: Clip.none,
                  fit: StackFit.expand,
                  children: [
                    Positioned(
                      left: -size.width * 0.3,
                      top: -size.height * 0.3,
                      width: size.width * 1.6,
                      height: size.height * 1.6,
                      child: CustomPaint(
                        painter: _createPainter(resources, shaderView),
                        child: const SizedBox.expand(),
                      ),
                    ),
                  ],
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
    final double activeStrength =
        widget.effectStrength *
        ui.lerpDouble(widget.idleEffectStrength, 1, _effectActivation)!;
    return HolographicCardPainter(
      shader: resources.shader,
      cardMaskImage: resources.cardMaskImage,
      backgroundImage: resources.backgroundImage,
      foregroundImage: resources.foregroundImage,
      foregroundContourImage: resources.contourImage,
      foregroundBloomImage: resources.bloomImage,
      view: shaderView,
      depth: widget.depth,
      effectStrength: activeStrength,
      contourGlowStrength: widget.contourGlowStrength,
    );
  }
}

class _Resources {
  const _Resources({
    required this.cardMaskImage,
    required this.backgroundImage,
    required this.foregroundImage,
    required this.contourImage,
    required this.bloomImage,
    required this.shader,
  });

  final ui.Image cardMaskImage;
  final ui.Image backgroundImage;
  final ui.Image foregroundImage;
  final ui.Image contourImage;
  final ui.Image bloomImage;
  final ui.FragmentShader shader;

  void dispose() {
    cardMaskImage.dispose();
    backgroundImage.dispose();
    foregroundImage.dispose();
    contourImage.dispose();
    bloomImage.dispose();
    shader.dispose();
  }
}
