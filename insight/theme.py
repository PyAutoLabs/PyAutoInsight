"""Board presentation, using the shared PyAutoBrain banner and navigation."""

import importlib.util
import os
from pathlib import Path

from insight import ORGAN_ROOT


def theme():
    candidates = [Path(os.environ["PYAUTO_BRAIN"])] if os.environ.get("PYAUTO_BRAIN") else []
    candidates += [ORGAN_ROOT.parent / "PyAutoBrain", ORGAN_ROOT / "_brain"]
    for root in candidates:
        path = root / "board/_theme.py"
        if path.is_file():
            spec = importlib.util.spec_from_file_location("insight_board_theme", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("Shared theme unavailable: set PYAUTO_BRAIN to a PyAutoBrain checkout.")


CSS = "\nmain{padding-bottom:48px}\nh2,h3{color:var(--accent)}h2{border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:32px}\na{color:var(--accent)}\n.lede{color:var(--muted)}\n.tablewrap{overflow-x:auto}\ntable{border-collapse:collapse;width:100%;font-size:14px}\nth,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}\ntd.num{text-align:right;white-space:nowrap}\n.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.muted{color:var(--muted)}\n.notions{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;margin:8px 0}\n.notions div{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px}\n.notions b{display:block;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:1px}\n.stats{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0}\n.stats div{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 14px}\n.stats b{display:block;font-size:20px;color:var(--accent)}.stats span{font-size:12px;color:var(--muted)}\nbutton[data-copy]{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;text-align:left;\nbackground:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:6px;\npadding:3px 6px;cursor:pointer;word-break:break-all}\nbutton.copied{border-color:var(--ok)}\n.checkin textarea{display:block;width:100%;font:inherit;font-size:14px;line-height:1.5;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:12px;margin:8px 0;resize:vertical}\n#copy-checkin{background:var(--accent);color:var(--bg);border:0;border-radius:6px;padding:10px 16px;cursor:pointer;font-weight:600}\n#copy-status{margin-left:12px}\ncode{color:var(--accent);word-break:break-all}\n"
JS = "\ndocument.querySelectorAll('button[data-copy]').forEach(function(b){\n  b.addEventListener('click',function(){\n    var t=b.getAttribute('data-copy');\n    var done=function(){b.classList.add('copied');setTimeout(function(){b.classList.remove('copied')},1200)};\n    if(navigator.clipboard){navigator.clipboard.writeText(t).then(done,function(){})}\n  });\n});\ndocument.querySelectorAll('[data-age-from]').forEach(function(el){\n  var t=Date.parse(el.getAttribute('data-age-from'));\n  if(!isNaN(t)){el.textContent=' · '+Math.max(0,Math.floor((Date.now()-t)/864e5))+' d today';}\n});\n"
