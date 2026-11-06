/*
 * On-screen controls for touch devices.
 *
 * The port reads the keyboard through SDL, so a button only has to send the
 * same keydown/keyup events a physical key sends. Keeping this in the page
 * means the WebAssembly build does not change.
 *
 * Add ?touch=1 to the URL to show the controls on a machine with a mouse,
 * ?touch=0 to hide them on a touch screen.
 */
(function () {
  'use strict';

  var q = window.location.search || '';
  if (/(?:^|[?&])touch=0(?:&|$)/.test(q)) return;
  var force = /(?:^|[?&])touch=1(?:&|$)/.test(q);
  var coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
  if (!force && !coarse && !(navigator.maxTouchPoints > 0)) return;

  var KEYS = {
    left:  { key: 'ArrowLeft',  code: 'ArrowLeft',  keyCode: 37 },
    right: { key: 'ArrowRight', code: 'ArrowRight', keyCode: 39 },
    gas:   { key: 'ArrowUp',    code: 'ArrowUp',    keyCode: 38 },
    brake: { key: 'ArrowDown',  code: 'ArrowDown',  keyCode: 40 },
    hand:  { key: ' ',          code: 'Space',      keyCode: 32 },
    enter: { key: 'Enter',      code: 'Enter',      keyCode: 13 },
    pause: { key: 'p',          code: 'KeyP',       keyCode: 80 }
  };

  function send(type, k) {
    var ev;
    try {
      ev = new KeyboardEvent(type, {
        key: k.key,
        code: k.code,
        bubbles: true,
        cancelable: true
      });
    } catch (e) {
      ev = document.createEvent('KeyboardEvent');
      ev.initKeyboardEvent(type, true, true, window, k.key, 0, '', false, '');
    }
    /* SDL's Emscripten backend reads the legacy keyCode/which fields. */
    try {
      Object.defineProperty(ev, 'keyCode', { get: function () { return k.keyCode; } });
      Object.defineProperty(ev, 'which', { get: function () { return k.keyCode; } });
    } catch (e) { /* the browser did not allow it; key/code still carry the key */ }
    document.dispatchEvent(ev);
  }

  var css = document.createElement('style');
  css.textContent = [
    '#touch{position:fixed;top:0;right:0;bottom:0;left:0;z-index:20;pointer-events:none;',
    'font:600 15px/1 system-ui,-apple-system,"Segoe UI",sans-serif;',
    '-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}',
    '#touch .pad{position:absolute;display:flex;gap:10px;align-items:flex-end}',
    '#touch .pad.left{left:14px;bottom:14px;',
    'left:max(14px,env(safe-area-inset-left));bottom:max(14px,env(safe-area-inset-bottom))}',
    '#touch .pad.right{right:14px;bottom:14px;',
    'right:max(14px,env(safe-area-inset-right));bottom:max(14px,env(safe-area-inset-bottom))}',
    '#touch .stack{display:flex;flex-direction:column;gap:10px}',
    '#touch button{pointer-events:auto;touch-action:none;-webkit-tap-highlight-color:transparent;',
    'border:1px solid rgba(255,255,255,.3);border-radius:14px;background:rgba(17,19,23,.55);',
    'color:#fff;margin:0;padding:0;display:flex;align-items:center;justify-content:center;',
    'font:inherit;font-weight:700;backdrop-filter:blur(2px);-webkit-backdrop-filter:blur(2px)}',
    '#touch button:active{background:rgba(232,69,44,.85)}',
    '#touch .pad.left button,#touch .stack button{width:66px;height:66px;font-size:28px}',
    '#touch button.hand{width:54px;height:54px;font-size:20px}',
    '#touch .menu{position:absolute;top:12px;right:12px;',
    'top:max(12px,env(safe-area-inset-top));right:max(12px,env(safe-area-inset-right));',
    'display:flex;gap:8px}',
    '#touch .menu button{height:42px;padding:0 16px;font-size:13px;letter-spacing:.05em}',
    '#touch .menu button.start{background:rgba(232,69,44,.8)}'
  ].join('');
  document.head.appendChild(css);

  var wrap = document.createElement('div');
  wrap.id = 'touch';
  wrap.className = 'hidden';
  wrap.setAttribute('aria-hidden', 'true');
  wrap.innerHTML =
    '<div class="pad left">' +
      '<button type="button" data-key="left" aria-label="Links">◀</button>' +
      '<button type="button" data-key="right" aria-label="Rechts">▶</button>' +
    '</div>' +
    '<div class="pad right">' +
      '<button type="button" class="hand" data-key="hand" aria-label="Handrem">✋</button>' +
      '<div class="stack">' +
        '<button type="button" data-key="gas" aria-label="Gas">▲</button>' +
        '<button type="button" data-key="brake" aria-label="Rem">▼</button>' +
      '</div>' +
    '</div>' +
    '<div class="menu">' +
      '<button type="button" class="start" data-key="enter">ENTER</button>' +
      '<button type="button" data-key="pause" aria-label="Pauze">PAUZE</button>' +
    '</div>';
  document.body.appendChild(wrap);

  /* The buttons use pointer events.  Keep the browser's compatibility
   * mouse/touch events from bubbling to the game, or a tap on a button
   * could also land as a click on the menu behind it. */
  ['mousedown', 'mouseup', 'click'].forEach(function (type) {
    wrap.addEventListener(type, function (e) {
      e.preventDefault();
      e.stopPropagation();
    }, true);
  });
  ['touchstart', 'touchend'].forEach(function (type) {
    wrap.addEventListener(type, function (e) { e.stopPropagation(); }, true);
  });

  var held = [];

  function press(btn, e) {
    e.preventDefault();
    e.stopPropagation();
    var k = KEYS[btn.getAttribute('data-key')];
    if (!k || btn._down) return;
    btn._down = true;
    held.push(btn);
    if (btn._upTimer) {
      clearTimeout(btn._upTimer);
      btn._upTimer = 0;
    }
    try { btn.setPointerCapture(e.pointerId); } catch (err) { /* no capture */ }
    if (!btn._sent) {
      btn._sent = true;
      send('keydown', k);
    }
    btn._at = performance.now();
  }

  function release(btn, e, immediate) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (!btn._down) return;
    btn._down = false;
    var i = held.indexOf(btn);
    if (i >= 0) held.splice(i, 1);
    var k = KEYS[btn.getAttribute('data-key')];
    /* A very quick tap can fall between two frames; keep the key down for
     * at least 50 ms so the game's polling sees it. */
    var wait = immediate ? 0 : Math.max(0, 50 - (performance.now() - (btn._at || 0)));
    if (btn._upTimer) clearTimeout(btn._upTimer);
    if (!wait) {
      if (btn._sent) {
        btn._sent = false;
        send('keyup', k);
      }
      return;
    }
    btn._upTimer = setTimeout(function () {
      btn._upTimer = 0;
      if (!btn._down && btn._sent) {
        btn._sent = false;
        send('keyup', k);
      }
    }, wait);
  }

  Array.prototype.forEach.call(wrap.querySelectorAll('button'), function (btn) {
    btn.addEventListener('pointerdown', function (e) { press(btn, e); });
    btn.addEventListener('pointerup', function (e) { release(btn, e); });
    btn.addEventListener('pointercancel', function (e) { release(btn, e); });
    btn.addEventListener('lostpointercapture', function () { release(btn); });
    btn.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    btn.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); });
  });

  function releaseAll() {
    held.slice().forEach(function (btn) { release(btn, null, true); });
  }
  window.addEventListener('blur', releaseAll);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') releaseAll();
  });

  /* The controls belong to the game, not to the file picker.  This is a
   * capture listener: start() enters the game's main loop and does not
   * return, so a bubble listener on the button would never run. */
  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t && t.closest && t.closest('#play, #fullscreen')) {
      wrap.classList.remove('hidden');
      wrap.removeAttribute('aria-hidden');
    }
  }, true);

  /* Fullscreen on the canvas would leave this overlay outside the fullscreen
   * element, so ask for the page instead; after Play the canvas is all there
   * is to see anyway. */
  var canvas = document.getElementById('canvas');
  if (canvas && canvas.requestFullscreen) {
    canvas.requestFullscreen = function () {
      if (document.documentElement.requestFullscreen)
        return document.documentElement.requestFullscreen();
      return Promise.reject(new Error('fullscreen unavailable'));
    };
  }
})();
