/**
 * SpineChar - 可嵌入角色页面的 Spine 动画组件
 *
 * 使用前需在页面中引入：
 *   <script src="/plugins/pixi.js"></script>
 *   <script src="/plugins/spine-pixi-v8.js"></script>
 *   <script src="/javascripts/spine_char.js"></script>
 *
 * 用法：
 *   SpineChar.init('#my-container', {
 *       skelPath: '/spine/sr/1415/xilian.json',
 *       atlasPath: '/spine/sr/1415/xilian.atlas',
 *       scale: 0.5,
 *       bgColor: 0x1a1a2e,
 *   });
 */
(function (global) {
    'use strict';

    var DEFAULT_OPTIONS = {
        skelPath: '',
        atlasPath: '',
        scale: 0.5,
        minScale: 0.05,
        maxScale: 3,
        bgColor: 0x1a1a2e,
        antialias: true,
        autoPlay: true,
        onReady: null,
        onError: null,
    };

    var instances = [];

    function SpineInstance(containerEl, options) {
        this._container = containerEl;
        this._opts = Object.assign({}, DEFAULT_OPTIONS, options);
        this._app = null;
        this._spineObj = null;
        this._viewport = null;
        this._vpScale = this._opts.scale;
        this._vpX = 0;
        this._vpY = 0;
        this._W = 0;
        this._H = 0;
        this._animName = '';
        this._dragging = false;
        this._dragStartX = 0;
        this._dragStartY = 0;
        this._dragVpX = 0;
        this._dragVpY = 0;
        this._resizeHandler = null;
        this._wheelHandler = null;
        this._mousedownHandler = null;
        this._mousemoveHandler = null;
        this._mouseupHandler = null;
    }

    SpineInstance.prototype = {
        _applyViewport: function () {
            if (!this._viewport) return;
            this._viewport.scale.set(this._vpScale);
            this._viewport.x = this._vpX;
            this._viewport.y = this._vpY;
        },

        _handleWheel: function (e) {
            e.preventDefault();
            var oldScale = this._vpScale;
            this._vpScale *= (1 - e.deltaY * 0.001);
            this._vpScale = Math.max(this._opts.minScale,
                Math.min(this._opts.maxScale, this._vpScale));

            var rect = this._app.canvas.getBoundingClientRect();
            var mx = e.clientX - rect.left;
            var my = e.clientY - rect.top;
            this._vpX = mx - (mx - this._vpX) * (this._vpScale / oldScale);
            this._vpY = my - (my - this._vpY) * (this._vpScale / oldScale);
            this._applyViewport();
        },

        _handleMouseDown: function (e) {
            this._dragging = true;
            this._dragStartX = e.clientX;
            this._dragStartY = e.clientY;
            this._dragVpX = this._vpX;
            this._dragVpY = this._vpY;
            this._app.canvas.style.cursor = 'grabbing';
        },

        _handleMouseMove: function (e) {
            if (!this._dragging) return;
            this._vpX = this._dragVpX + (e.clientX - this._dragStartX);
            this._vpY = this._dragVpY + (e.clientY - this._dragStartY);
            this._applyViewport();
        },

        _handleMouseUp: function () {
            this._dragging = false;
            if (this._app && this._app.canvas) {
                this._app.canvas.style.cursor = 'grab';
            }
        },

        _handleResize: function () {
            var newW = this._container.clientWidth || this._container.offsetWidth;
            var newH = this._container.clientHeight || this._container.offsetHeight;
            if (!newW || !newH) return;
            this._app.renderer.resize(newW, newH);
            this._vpX += (newW - this._W) / 2;
            this._vpY += (newH - this._H) / 2;
            this._W = newW;
            this._H = newH;
            this._applyViewport();
        },

        zoomIn: function (factor) {
            if (!factor) factor = 1.3;
            var cx = this._W / 2;
            var cy = this._H / 2;
            this._vpScale = Math.min(this._opts.maxScale, this._vpScale * factor);
            this._vpX = cx - (cx - this._vpX) * factor;
            this._vpY = cy - (cy - this._vpY) * factor;
            this._applyViewport();
        },

        zoomOut: function (factor) {
            if (!factor) factor = 1.3;
            var cx = this._W / 2;
            var cy = this._H / 2;
            this._vpScale = Math.max(this._opts.minScale, this._vpScale / factor);
            this._vpX = cx - (cx - this._vpX) / factor;
            this._vpY = cy - (cy - this._vpY) / factor;
            this._applyViewport();
        },

        resetView: function () {
            this._vpScale = this._opts.scale;
            this._vpX = this._W / 2;
            this._vpY = this._H * 0.6;
            this._applyViewport();
        },

        getScale: function () {
            return this._vpScale;
        },

        destroy: function () {
            if (this._wheelHandler && this._app) {
                this._app.canvas.removeEventListener('wheel', this._wheelHandler);
            }
            if (this._mousedownHandler && this._app) {
                this._app.canvas.removeEventListener('mousedown', this._mousedownHandler);
            }
            if (this._mousemoveHandler) {
                window.removeEventListener('mousemove', this._mousemoveHandler);
            }
            if (this._mouseupHandler) {
                window.removeEventListener('mouseup', this._mouseupHandler);
            }
            if (this._resizeHandler) {
                window.removeEventListener('resize', this._resizeHandler);
            }
            if (this._app) {
                this._app.destroy(true, { children: true, texture: true });
                this._app = null;
            }
            this._container.innerHTML = '';
        },

        init: function () {
            var self = this;
            var container = this._container;
            var opts = this._opts;

            this._W = container.clientWidth || container.offsetWidth || 400;
            this._H = container.clientHeight || container.offsetHeight || 600;

            var app = new PIXI.Application();
            this._app = app;

            return app.init({
                width: this._W,
                height: this._H,
                backgroundColor: opts.bgColor,
                antialias: opts.antialias,
                resolution: window.devicePixelRatio || 1,
                autoDensity: true,
            }).then(function () {
                container.appendChild(app.canvas);

                var viewport = new PIXI.Container();
                self._viewport = viewport;
                app.stage.addChild(viewport);

                // 手动 fetch + JSON.parse 骨架，避免 PixiJS 默认 JSON 加载器的问题
                return fetch(opts.skelPath)
                    .then(function (r) { return r.text(); })
                    .then(function (text) {
                        PIXI.Assets.cache.set(opts.skelPath, JSON.parse(text));
                        return PIXI.Assets.load({ src: opts.atlasPath });
                    });
            }).then(function () {
                var spineObj = spine.Spine.from({
                    skeleton: opts.skelPath,
                    atlas: opts.atlasPath,
                });

                self._spineObj = spineObj;
                spineObj.x = 0;
                spineObj.y = 0;
                spineObj.scale.set(opts.scale);

                self._viewport.addChild(spineObj);

                self._vpScale = opts.scale;
                self._vpX = self._W / 2;
                self._vpY = self._H * 0.6;
                self._applyViewport();

                if (opts.autoPlay) {
                    var anims = spineObj.state.data.skeletonData.animations;
                    if (anims.length > 0) {
                        self._animName = anims[0].name;
                        spineObj.state.setAnimation(0, self._animName, true);
                    }
                }

                app.canvas.style.cursor = 'grab';

                self._wheelHandler = self._handleWheel.bind(self);
                self._mousedownHandler = self._handleMouseDown.bind(self);
                self._mousemoveHandler = self._handleMouseMove.bind(self);
                self._mouseupHandler = self._handleMouseUp.bind(self);
                self._resizeHandler = self._handleResize.bind(self);

                app.canvas.addEventListener('wheel', self._wheelHandler, { passive: false });
                app.canvas.addEventListener('mousedown', self._mousedownHandler);
                window.addEventListener('mousemove', self._mousemoveHandler);
                window.addEventListener('mouseup', self._mouseupHandler);
                window.addEventListener('resize', self._resizeHandler);

                if (typeof opts.onReady === 'function') {
                    opts.onReady(self);
                }

                return self;
            }).catch(function (err) {
                console.error('[SpineChar] Init error:', err);
                if (typeof opts.onError === 'function') {
                    opts.onError(err);
                }
                throw err;
            });
        },
    };

    var SpineChar = {
        _instances: {},

        init: function (selector, options) {
            var container = (typeof selector === 'string')
                ? document.querySelector(selector)
                : selector;

            if (!container) {
                console.error('[SpineChar] Container not found:', selector);
                return Promise.reject(new Error('Container not found'));
            }

            var inst = new SpineInstance(container, options || {});
            // 用容器元素作为key存储实例，方便后续 destroy
            var key = container.id || container.className || ('spinechar-' + Math.random().toString(36).slice(2, 8));
            this._instances[key] = inst;
            return inst.init();
        },

        get: function (selector) {
            var container = (typeof selector === 'string')
                ? document.querySelector(selector)
                : selector;
            if (!container) return null;
            var key = container.id || container.className;
            return this._instances[key] || null;
        },
    };

    global.SpineChar = SpineChar;
}(window));