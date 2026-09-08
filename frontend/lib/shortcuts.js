/**
 * Keyboard Shortcuts Manager
 * Registers and coordinates global shortcuts (Ctrl+K Command Palette, Ctrl+N New Chat, Esc Close).
 */

export class ShortcutManager {
  constructor() {
    this.handlers = new Map();
    this._boundOnKeyDown = this.handleKeyDown.bind(this);
    this.isListening = false;
  }

  start() {
    if (typeof window !== 'undefined' && !this.isListening) {
      window.addEventListener('keydown', this._boundOnKeyDown);
      this.isListening = true;
    }
  }

  stop() {
    if (typeof window !== 'undefined' && this.isListening) {
      window.removeEventListener('keydown', this._boundOnKeyDown);
      this.isListening = false;
    }
  }

  register(nameOrKey, comboOrCallback, maybeCallback) {
    if (typeof comboOrCallback === 'function') {
      this.handlers.set(String(nameOrKey).toLowerCase(), comboOrCallback);
    } else if (typeof maybeCallback === 'function') {
      // comboOrCallback is an object like { key: 'k', ctrl: true }
      const key = (comboOrCallback.key || '').toLowerCase();
      const isCtrl = comboOrCallback.ctrl ? 'ctrl+' : '';
      const comboStr = `${isCtrl}${key}`;
      this.handlers.set(comboStr, maybeCallback);
      this.handlers.set(String(nameOrKey).toLowerCase(), maybeCallback);
    }
  }

  unregister(key) {
    this.handlers.delete(String(key).toLowerCase());
  }

  handleKeyDown(event) {
    // Ignore when focused inside text input or textarea unless specifically handled
    const tag = event.target?.tagName?.toUpperCase();
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

    const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform);
    const modKey = event.ctrlKey || event.metaKey;

    // Esc
    if (event.key === 'Escape') {
      const handler = this.handlers.get('escape') || this.handlers.get('esc');
      if (handler) {
        if (event.preventDefault) event.preventDefault();
        handler();
      }
      return;
    }

    if (isInput) {
      return;
    }

    // Mod + K (Command Palette)
    if (modKey && (event.key === 'k' || event.key === 'K')) {
      const handler = this.handlers.get('ctrl+k') || this.handlers.get('mod+k') || this.handlers.get('open_palette');
      if (handler) {
        if (event.preventDefault) event.preventDefault();
        handler();
      }
      return;
    }

    // Mod + N (New Chat)
    if (modKey && (event.key === 'n' || event.key === 'N')) {
      const handler = this.handlers.get('ctrl+n') || this.handlers.get('mod+n') || this.handlers.get('new_chat');
      if (handler) {
        if (event.preventDefault) event.preventDefault();
        handler();
      }
      return;
    }
  }
}

export { ShortcutManager as KeyboardShortcuts };
export const shortcuts = new ShortcutManager();
