"""
ابزار تشخیصی: دامپ ساختار DOM رندرشده صفحه ورود با همان موتور Edge WebView2 برنامه.
استفاده: python main.py --dump-login-dom
خروجی: JSON در stdout (بدون هیچ مقدار حساسی، فقط ساختار).
"""
import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

import json
import threading
import webview

DUMP_JS = """() => {
  try {
  const out = { url: location.href, title: document.title,
    bodyLen: (document.body ? document.body.innerHTML.length : -1), inputs: [], extras: [] };
  const els = document.querySelectorAll('input, select, textarea, button');
  for (const el of els) {
    let w = 0, h = 0;
    try { const r = el.getBoundingClientRect(); w = Math.round(r.width); h = Math.round(r.height); } catch(e) {}
    let sib = '';
    try {
      const p = el.previousElementSibling;
      if (p) sib = (p.innerText || '').slice(0, 50);
    } catch(e) {}
    out.inputs.push({
      tag: el.tagName, type: el.type || '', id: el.id || '', name: el.name || '',
      cls: ((el.className || '').toString()).slice(0, 80),
      ph: (el.getAttribute('placeholder') || '').slice(0, 40),
      w: w, h: h, ro: !!el.readOnly, dis: !!el.disabled,
      hasVal: !!(el.value && el.value.length), tab: el.getAttribute('tabindex'),
      prev: sib,
      style: (el.getAttribute('style') || '').slice(0, 80)
    });
  }
  const all = document.querySelectorAll('*');
  for (const el of all) {
    const c = ((el.className || '').toString());
    if (/keypad|keyboard|shuf|virtual/i.test(c) || /keypad|keyboard/i.test(el.id || '')) {
      let w = 0, h = 0;
      try { const r = el.getBoundingClientRect(); w = Math.round(r.width); h = Math.round(r.height); } catch(e) {}
      out.extras.push({ tag: el.tagName, id: el.id || '', cls: c.slice(0, 100), w: w, h: h });
      if (out.extras.length > 20) break;
    }
  }
  out.hasJQuery = (typeof window.jQuery !== 'undefined');
  return out;
  } catch(e) { return { jsError: String(e).slice(0, 200) }; }
}"""


def run_dom_dump(url="https://ipm.ssaa.ir/CA/DeclarationList", wait_seconds=20):
    result = {}

    def fetch(window):
        import time
        time.sleep(wait_seconds)
        try:
            result["dom"] = window.evaluate_js(DUMP_JS)
        except Exception as e:
            result["error"] = str(e)[:300]
        try:
            window.destroy()
        except Exception:
            pass

    window = webview.create_window(
        title="DOM Inspector", url=url, width=1200, height=800,
        resizable=True, text_select=True, confirm_close=False,
    )
    t = threading.Thread(target=fetch, args=(window,), daemon=True)
    t.start()
    webview.start(gui="edgechromium", debug=False)
    t.join(timeout=10)
    try:
        print(json.dumps(result, ensure_ascii=True))
    except Exception:
        print('{"error": "print-failed"}')


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://ipm.ssaa.ir/CA/DeclarationList"
    run_dom_dump(target)
