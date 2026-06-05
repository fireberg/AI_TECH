#!/usr/bin/env python3
"""Build a single-page consolidated Kalman filter textbook HTML."""

import re
import os

BASE = os.path.dirname(os.path.abspath(__file__))

CHAPTER_TITLES = {
    'home': '首页',
    'ch01': '第一章',
    'ch02': '第二章',
    'ch03': '第三章',
    'ch04': '第四章',
    'ch05': '第五章',
    'ch06': '第六章',
    'ch07': '第七章',
    'ch08': '第八章',
    'ch09': '第九章',
}

def read_file(name):
    with open(os.path.join(BASE, name), 'r', encoding='utf-8') as f:
        return f.read()

def extract_body_content(html, chapter_id):
    """Extract content between <div class="container"> and the bottom nav."""
    # Find the container content
    m = re.search(r'<div class="container"[^>]*>\s*\n?(.*?)\n*</div>\s*\n*<nav\s+style=', html, re.DOTALL)
    if not m:
        # For ch01 which has <!-- container -->
        m = re.search(r'<div class="container"[^>]*>\s*\n?(.*?)\n*</div><!-- container -->', html, re.DOTALL)
    if not m:
        # Try simpler match
        m = re.search(r'<div class="container"[^>]*>\s*\n?(.*?)\n*</div>\s*$', html, re.DOTALL | re.MULTILINE)
    if not m:
        raise ValueError(f"Could not extract body content for {chapter_id}")
    return m.group(1)

def extract_script(html):
    """Extract all script content (excluding CDN scripts)."""
    scripts = re.findall(r'<script>\s*(.*?)\s*</script>', html, re.DOTALL)
    return '\n'.join(scripts)

def extract_index_body(html):
    """Extract the index page body content (hero + container)."""
    # Get hero section
    hero_match = re.search(r'(<div class="hero">.*?</div>)', html, re.DOTALL)
    hero = hero_match.group(1) if hero_match else ''
    
    # Get container
    container_match = re.search(r'<div class="container">\s*\n?(.*?)\n*</div>\s*\n*<footer', html, re.DOTALL)
    container = container_match.group(1) if container_match else ''
    
    return hero + '\n<div class="container">\n' + container + '\n</div>'


def collect_ids_from_html(html):
    """Find all id="xxx" in HTML."""
    return re.findall(r'\bid=["\']([^"\']+)["\']', html)

def collect_ids_from_script(script):
    """Find all getElementById('xxx') and Plotly.react('xxx' references."""
    ids = set()
    # getElementById patterns
    ids.update(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", script))
    # Plotly.react patterns
    ids.update(re.findall(r"Plotly\.react\(['\"]([^'\"]+)['\"]", script))
    return ids

def prefix_ids_in_html(html, prefix, ids_to_prefix):
    """Prefix all id attributes in HTML."""
    def replace_id(m):
        attr = m.group(1)  # id= or for= etc
        quote = m.group(2)
        id_val = m.group(3)
        if id_val in ids_to_prefix:
            return f'{attr}{quote}{prefix}_{id_val}{quote}'
        return m.group(0)
    
    # Replace id="xxx"
    html = re.sub(r'\b(id=)(["\'])([^"\']+)\2', replace_id, html)
    return html

def prefix_ids_in_script(script, prefix, ids_to_prefix):
    """Prefix all element ID references in script."""
    def replace_getbyid(m):
        quote = m.group(1)
        id_val = m.group(2)
        if id_val in ids_to_prefix:
            return f"getElementById({quote}{prefix}_{id_val}{quote})"
        return m.group(0)
    
    def replace_plotly(m):
        quote = m.group(1)
        id_val = m.group(2)
        if id_val in ids_to_prefix:
            return f"Plotly.react({quote}{prefix}_{id_val}{quote}"
        return m.group(0)
    
    script = re.sub(r"getElementById\((['\"])([^'\"]+)\1\)", replace_getbyid, script)
    script = re.sub(r"Plotly\.react\((['\"])([^'\"]+)\1", replace_plotly, script)
    
    # Also handle querySelector patterns with #id
    def replace_qs(m):
        prefix_text = m.group(1)
        quote = m.group(2)
        id_val = m.group(3)
        if id_val in ids_to_prefix:
            return f"{prefix_text}{quote}#{prefix}_{id_val}{quote}"
        return m.group(0)
    script = re.sub(r"(querySelector(?:All)?\()(['\"])#([^'\"]+)\2", replace_qs, script)
    
    return script


def process_chapter(chapter_num, filename):
    """Process a chapter file, returning prefixed HTML and script."""
    html = read_file(filename)
    prefix = f'ch{chapter_num:02d}'
    
    body = extract_body_content(html, prefix)
    script = extract_script(html)
    
    # Remove the DOMContentLoaded/renderMathInElement wrapper from script
    # We'll handle KaTeX rendering in the master script
    script = re.sub(
        r'document\.addEventListener\(["\']DOMContentLoaded["\'],\s*function\(\)\s*\{[^}]*renderMathInElement\(document\.body,\s*\{[\s\S]*?\}\s*\);\s*\}\);?\s*',
        '',
        script
    )
    
    # Collect all IDs
    html_ids = set(collect_ids_from_html(body))
    script_ids = collect_ids_from_script(script)
    all_ids = html_ids | script_ids
    
    # Also handle data-tab and tab-xxx IDs from ch09
    if chapter_num == 9:
        # ch09 has tab content with id="tab-preset" etc and data-tab="preset"
        # We prefix the IDs (tab-preset -> ch09_tab-preset)
        # But leave data-tab values as-is (they stay "preset", "custom", "csv")
        # And update the JS to construct the right ID: 'ch09_tab-' + this.dataset.tab
        tab_ids = re.findall(r'\bid=["\']tab-([^"\']+)["\']', body)
        for tid in tab_ids:
            all_ids.add(f'tab-{tid}')
        # Fix the JS to construct prefixed ID from unprefixed data-tab value
        script = script.replace("'tab-'+this.dataset.tab", "'ch09_tab-'+this.dataset.tab")
    
    # Prefix IDs
    prefixed_body = prefix_ids_in_html(body, prefix, all_ids)
    prefixed_script = prefix_ids_in_script(script, prefix, all_ids)
    
    # For ch09, also need to prefix the querySelectorAll('.tab') and '.tab-content' 
    # to scope them to ch09 section
    if chapter_num == 9:
        prefixed_script = prefixed_script.replace(
            "document.querySelectorAll('.tab')",
            "document.querySelectorAll('#ch09 .ch09-tab')"
        )
        prefixed_script = prefixed_script.replace(
            "document.querySelectorAll('.tab-content')",
            "document.querySelectorAll('#ch09 .ch09-tab-content')"
        )
        # Add ch09- prefix to tab/tab-content classes in HTML
        prefixed_body = prefixed_body.replace('class="tab active"', 'class="ch09-tab active"')
        prefixed_body = prefixed_body.replace('class="tab"', 'class="ch09-tab"')
        prefixed_body = prefixed_body.replace('class="tab-content active"', 'class="ch09-tab-content active"')
        prefixed_body = prefixed_body.replace('class="tab-content"', 'class="ch09-tab-content"')
    
    return prefixed_body, prefixed_script


def build_css():
    """Build merged, deduplicated CSS."""
    return """:root {
  --primary: #2563eb;
  --primary-dark: #1d4ed8;
  --primary-light: #dbeafe;
  --bg: #f8fafc;
  --card: #ffffff;
  --card-bg: #ffffff;
  --text: #1e293b;
  --text-light: #64748b;
  --border: #e2e8f0;
  --accent: #f59e0b;
  --note-bg: #fffbeb;
  --note-border: #f59e0b;
  --code-bg: #f1f5f9;
  --danger: #dc2626;
  --danger-light: #fef2f2;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.8;
  padding-top: 48px;
}

/* ===== Tab Navigation ===== */
.tab-nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 200;
  background: #1e293b; color: #fff;
  display: flex; align-items: center;
  height: 48px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.tab-nav-title {
  flex-shrink: 0; font-weight: 800; font-size: 0.92em;
  padding: 0 16px; white-space: nowrap;
  border-right: 1px solid rgba(255,255,255,0.15);
}
.tab-nav-scroll {
  flex: 1; overflow-x: auto; overflow-y: hidden;
  display: flex; align-items: stretch; height: 100%;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.tab-nav-scroll::-webkit-scrollbar { display: none; }
.tab-nav-btn {
  flex-shrink: 0; padding: 0 18px; height: 100%;
  display: flex; align-items: center;
  cursor: pointer; font-size: 0.9em; font-weight: 600;
  color: rgba(255,255,255,0.65); white-space: nowrap;
  border-bottom: 3px solid transparent;
  transition: color .2s, border-color .2s, background .2s;
  background: none; border-top: none; border-left: none; border-right: none;
  font-family: inherit;
}
.tab-nav-btn:hover { color: #fff; background: rgba(255,255,255,0.06); }
.tab-nav-btn.active { color: #fff; border-bottom-color: #60a5fa; }

/* ===== Chapter Sections ===== */
.chapter-section { display: none; }
.chapter-section.active { display: block; }

/* ===== Index / Home ===== */
.hero {
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 50%, #0ea5e9 100%);
  color: #fff; padding: 60px 20px 50px; text-align: center;
}
.hero h1 { font-size: 2.2em; margin-bottom: 12px; font-weight: 800; color: #fff; }
.hero p { font-size: 1.1em; opacity: 0.9; max-width: 680px; margin: 0 auto 8px; }
.hero .subtitle { font-size: 0.92em; opacity: 0.7; }
.intro {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; padding: 28px 32px; margin-bottom: 36px; font-size: 1.02em;
}
.intro h2 { color: var(--primary); margin-bottom: 12px; font-size: 1.3em; border: none; padding: 0; }
.intro ul { padding-left: 20px; }
.intro li { margin-bottom: 6px; }
.chapters { display: grid; gap: 16px; }
.ch-card {
  display: flex; align-items: flex-start;
  background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; padding: 24px 28px;
  text-decoration: none; color: inherit; cursor: pointer;
  transition: box-shadow .2s, transform .15s;
}
.ch-card:hover {
  box-shadow: 0 4px 20px rgba(37,99,235,.12); transform: translateY(-2px);
}
.ch-num {
  flex-shrink: 0; width: 48px; height: 48px;
  background: linear-gradient(135deg, var(--primary), #0ea5e9);
  color: #fff; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 1.2em; margin-right: 20px; margin-top: 2px;
}
.ch-info h3 { font-size: 1.1em; margin-bottom: 4px; color: var(--primary-dark); }
.ch-info p { font-size: 0.92em; color: var(--text-light); }
.tag {
  display: inline-block; font-size: 0.75em; padding: 2px 8px;
  border-radius: 4px; margin-right: 6px; margin-top: 6px; font-weight: 600;
}
.tag-interact { background: #dbeafe; color: #1d4ed8; }
.tag-code { background: #dcfce7; color: #166534; }
.tag-math { background: #fef3c7; color: #92400e; }

/* ===== Common Chapter Styles ===== */
.container { max-width: 900px; margin: 0 auto; padding: 32px 20px 60px; }
h1 { font-size: 2em; margin-bottom: 8px; color: var(--primary); }
.chapter-meta { color: var(--text-light); margin-bottom: 28px; font-size: 0.95em; }
h2 { font-size: 1.4em; margin: 36px 0 14px; color: #0f172a; border-left: 4px solid var(--primary); padding-left: 12px; }
h3 { font-size: 1.15em; margin: 24px 0 10px; }
p { margin-bottom: 14px; }
.objective {
  background: var(--primary-light); border-radius: 10px;
  padding: 20px 24px; margin-bottom: 28px;
}
.objective h3 { margin-top: 0; color: var(--primary); }
.interactive-box {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; padding: 24px; margin: 24px 0;
}
.controls { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 16px; }
.control-group { display: flex; flex-direction: column; gap: 4px; }
.control-group label { font-size: 0.85em; color: var(--text-light); font-weight: 600; }
.control-group input[type="range"] { width: 170px; }
.control-group select { padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border); }
.val-display {
  display: inline-block; min-width: 40px; text-align: center;
  background: var(--code-bg); border-radius: 4px; padding: 1px 6px;
  font-family: 'SF Mono', 'Consolas', monospace; font-size: 0.85em;
}
pre {
  background: #1e293b; color: #e2e8f0; border-radius: 8px;
  padding: 18px 20px; overflow-x: auto; font-size: 0.88em;
  line-height: 1.6; margin: 14px 0; position: relative;
}
pre code { font-family: 'SF Mono', 'Consolas', 'Menlo', monospace; }
.note {
  background: var(--note-bg); border-left: 4px solid var(--note-border);
  border-radius: 0 8px 8px 0; padding: 20px 24px; margin: 32px 0;
}
.note h3 { color: #92400e; margin-top: 0; }
.note h3::before { content: "\\1F527  "; }
.katex-display { overflow-x: auto; overflow-y: hidden; padding: 4px 0; }
button.action {
  padding: 8px 18px; border: none; border-radius: 6px;
  cursor: pointer; font-weight: 600; color: #fff; font-size: 0.92em;
}

/* ===== Ch02 extras ===== */
.matrix-display {
  background: var(--code-bg); border-radius: 8px; padding: 14px 18px;
  margin: 10px 0; overflow-x: auto; font-family: 'SF Mono', monospace; font-size: 0.92em;
}
table.matrix-table { border-collapse: collapse; margin: 10px 0; }
table.matrix-table td {
  padding: 6px 14px; text-align: center; border: 1px solid var(--border);
  font-family: 'SF Mono', monospace;
}
table.matrix-table th {
  padding: 6px 14px; background: var(--primary-light);
  border: 1px solid var(--border); font-size: 0.88em;
}

/* ===== Ch03/Ch05/Ch06/Ch07 extras ===== */
.stats-panel, .stats-row { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }
.stat-box {
  background: var(--code-bg); border-radius: 8px; padding: 8px 14px;
  flex: 1; min-width: 120px;
}
.stat-box .label { font-size: 0.78em; color: var(--text-light); margin-bottom: 2px; }
.stat-box .value {
  font-family: 'SF Mono', monospace; font-weight: 700; font-size: 0.95em;
}
.highlight-box {
  background: #f0f9ff; border: 2px solid var(--primary);
  border-radius: 10px; padding: 20px 24px; margin: 20px 0;
}

/* ===== Ch04 extras ===== */
.eq-box {
  background: var(--code-bg); border-radius: 10px; padding: 18px 22px;
  margin: 16px 0; border-left: 4px solid var(--primary);
}
.eq-box .eq-label { font-weight: 700; color: var(--primary); font-size: 0.92em; margin-bottom: 6px; }
.eq-box.predict { border-left-color: #2563eb; background: #eff6ff; }
.eq-box.update { border-left-color: #16a34a; background: #f0fdf4; }
.state-panel {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px; margin: 12px 0;
}
.state-item { background: var(--code-bg); border-radius: 8px; padding: 10px 14px; }
.state-item .label { font-size: 0.82em; color: var(--text-light); margin-bottom: 2px; }
.state-item .value {
  font-family: 'SF Mono', monospace; font-size: 0.95em;
  font-weight: 600; word-break: break-all;
}
.step-indicator { display: flex; gap: 4px; margin-bottom: 12px; }
.step-dot {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75em; font-weight: 700;
  border: 2px solid var(--border); color: var(--text-light);
}
.step-dot.active { border-color: var(--primary); background: var(--primary); color: #fff; }
.step-dot.done { border-color: #16a34a; background: #dcfce7; color: #16a34a; }

/* ===== Ch07 extras ===== */
.warn-box {
  background: var(--danger-light); border: 2px solid var(--danger);
  border-radius: 10px; padding: 16px 20px; margin: 16px 0;
}
.warn-box strong { color: var(--danger); }
.checklist { list-style: none; padding: 0; }
.checklist li {
  padding: 8px 0 8px 32px; position: relative;
  border-bottom: 1px solid var(--border);
}
.checklist li::before {
  content: "\\2713"; position: absolute; left: 4px;
  color: #16a34a; font-weight: 700; font-size: 1.1em;
}

/* ===== Ch08 extras ===== */
.card-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px; margin: 20px 0;
}
.app-card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 10px; padding: 20px; transition: box-shadow .2s;
}
.app-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,.08); }
.app-card h4 { color: var(--primary); margin-bottom: 8px; font-size: 1.05em; }
.app-card .specs {
  font-size: 0.82em; color: var(--text-light); margin-top: 8px;
  padding-top: 8px; border-top: 1px solid var(--border);
}
.compare-table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.92em; }
.compare-table th, .compare-table td {
  padding: 10px 14px; border: 1px solid var(--border); text-align: left;
}
.compare-table th { background: var(--primary-light); font-weight: 700; }
.compare-table tr:nth-child(even) { background: #f8fafc; }
.flow-box {
  background: var(--code-bg); border-radius: 10px; padding: 20px;
  margin: 16px 0; text-align: center;
}
.flow-box .step {
  display: inline-block; padding: 8px 16px; margin: 4px;
  border-radius: 6px; font-weight: 600; font-size: 0.9em;
}
.flow-box .arrow { color: var(--text-light); margin: 0 4px; font-size: 1.2em; }

/* ===== Ch09 extras ===== */
.sandbox {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; padding: 24px; margin: 24px 0;
}
.form-row {
  display: flex; flex-wrap: wrap; gap: 16px;
  margin-bottom: 16px; align-items: flex-start;
}
.form-col { flex: 1; min-width: 220px; }
.form-col label {
  display: block; font-size: 0.88em; color: var(--text-light);
  font-weight: 600; margin-bottom: 4px;
}
.form-col select, .form-col input[type="number"] {
  width: 100%; padding: 6px 10px; border: 1px solid var(--border);
  border-radius: 6px; font-size: 0.92em; font-family: inherit;
}
textarea.matrix-input {
  width: 100%; height: 72px; padding: 8px 10px;
  border: 1px solid var(--border); border-radius: 6px;
  font-family: 'SF Mono', 'Consolas', monospace; font-size: 0.88em;
  resize: vertical;
}
textarea.matrix-input.tall { height: 100px; }
.copy-btn {
  position: absolute; top: 8px; right: 8px;
  padding: 4px 12px; background: rgba(255,255,255,.15);
  color: #e2e8f0; border: none; border-radius: 4px;
  cursor: pointer; font-size: 0.82em;
}
.copy-btn:hover { background: rgba(255,255,255,.25); }
.ch09-tab, .tabs .tab {
  padding: 8px 18px; cursor: pointer; font-weight: 600; font-size: 0.92em;
  color: var(--text-light); border-bottom: 2px solid transparent;
  margin-bottom: -2px; transition: all .2s;
  background: none; border-top: none; border-left: none; border-right: none;
}
.ch09-tab.active, .tabs .tab.active {
  color: var(--primary); border-bottom-color: var(--primary);
}
.tabs {
  display: flex; gap: 0; border-bottom: 2px solid var(--border); margin-bottom: 16px;
}
.ch09-tab-content { display: none; }
.ch09-tab-content.active { display: block; }

/* ===== Footer ===== */
footer {
  text-align: center; padding: 30px 20px;
  color: var(--text-light); font-size: 0.88em;
  border-top: 1px solid var(--border);
}

/* ===== Responsive ===== */
@media (max-width: 600px) {
  .controls { flex-direction: column; }
  .control-group input[type="range"] { width: 100%; }
  .form-row { flex-direction: column; }
  .tab-nav-title { font-size: 0.82em; padding: 0 10px; }
  .tab-nav-btn { padding: 0 12px; font-size: 0.82em; }
  .hero h1 { font-size: 1.6em; }
}
"""


def build_tab_nav():
    """Build the sticky tab navigation HTML."""
    tabs = []
    for key, title in CHAPTER_TITLES.items():
        active = ' active' if key == 'home' else ''
        tabs.append(f'    <button class="tab-nav-btn{active}" data-target="{key}">{title}</button>')
    
    return f"""<div class="tab-nav">
  <div class="tab-nav-title">卡尔曼滤波教材</div>
  <div class="tab-nav-scroll">
{chr(10).join(tabs)}
  </div>
</div>"""


def build_index_section():
    """Build the home/index section."""
    html = read_file('index.html')
    
    # Extract hero
    hero_match = re.search(r'(<div class="hero">.*?</div>)', html, re.DOTALL)
    hero = hero_match.group(1) if hero_match else ''
    
    # Extract container content
    container_match = re.search(r'<div class="container">\s*\n?(.*?)\n*</div>\s*\n*<footer', html, re.DOTALL)
    container = container_match.group(1) if container_match else ''
    
    # Convert chapter links to tab-switch actions
    for i in range(1, 10):
        container = container.replace(
            f'href="ch{i:02d}.html"',
            f'href="javascript:void(0)" onclick="switchTab(\'ch{i:02d}\')"'
        )
    
    return f"""<section id="home" class="chapter-section active">
{hero}
<div class="container">
{container}
</div>
<footer>
  卡尔曼滤波交互式教材 · 面向嵌入式开发者 · 浏览器即教室
</footer>
</section>"""


def build_master_script():
    """Build the master tab-switching and lazy-init script."""
    return """
/* ============================================================
 * Master Tab Switching & Lazy Initialization
 * ============================================================ */
var chapterInitialized = {};

function switchTab(targetId) {
  document.querySelectorAll('.chapter-section').forEach(function(s) {
    s.classList.remove('active');
  });
  document.querySelectorAll('.tab-nav-btn').forEach(function(b) {
    b.classList.remove('active');
  });

  var section = document.getElementById(targetId);
  if (section) {
    section.classList.add('active');
  }
  var btn = document.querySelector('.tab-nav-btn[data-target="' + targetId + '"]');
  if (btn) {
    btn.classList.add('active');
    btn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }

  window.scrollTo(0, 0);

  if (targetId !== 'home') {
    renderMathInElement(section, {
      delimiters: [
        {left: "$$", right: "$$", display: true},
        {left: "\\\\(", right: "\\\\)", display: false}
      ]
    });
  }

  if (!chapterInitialized[targetId] && typeof window['init_' + targetId] === 'function') {
    window['init_' + targetId]();
    chapterInitialized[targetId] = true;
  }

  setTimeout(function() {
    window.dispatchEvent(new Event('resize'));
  }, 100);
}

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.tab-nav-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      switchTab(this.getAttribute('data-target'));
    });
  });
});
"""


def main():
    # Build all chapter sections
    chapter_sections = []
    chapter_scripts = []
    
    for i in range(1, 10):
        filename = f'ch{i:02d}.html'
        prefix = f'ch{i:02d}'
        print(f'Processing {filename}...')
        
        body, script = process_chapter(i, filename)
        
        chapter_sections.append(
            f'<section id="{prefix}" class="chapter-section">\n'
            f'<div class="container">\n{body}\n</div>\n'
            f'</section>'
        )
        
        # Wrap script in lazy-init function
        chapter_scripts.append(
            f'/* ===== Chapter {i:02d} ===== */\n'
            f'window.init_{prefix} = function() {{\n'
            f'{script}\n'
            f'}};\n'
        )
    
    # Build the complete HTML
    css = build_css()
    tab_nav = build_tab_nav()
    index_section = build_index_section()
    master_script = build_master_script()
    
    output = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>卡尔曼滤波交互式教材 — 嵌入式开发者实战指南</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
{css}
</style>
</head>
<body>

{tab_nav}

{index_section}

{chr(10).join(chapter_sections)}

<script>
{master_script}

{chr(10).join(chapter_scripts)}
</script>
</body>
</html>
"""
    
    outpath = os.path.join(BASE, 'kalman_textbook.html')
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(output)
    
    size = os.path.getsize(outpath)
    print(f'\nGenerated: {outpath}')
    print(f'File size: {size:,} bytes ({size/1024:.1f} KB)')


if __name__ == '__main__':
    main()
