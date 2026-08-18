import os
import re
import markdown

MODULE_DIR = r"c:\Users\admin\Desktop\dev\2000_Embody\course-modules"

css = '''
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #0f172a; color: #e2e8f0; line-height: 1.6; }
.header { background: #1e293b; padding: 1rem 2rem; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 1rem; }
.logo { font-size: 1.25rem; font-weight: 700; color: #38bdf8; }
.back-btn { padding: 0.5rem 1rem; background: #334155; color: #e2e8f0; border: none; border-radius: 0.5rem; cursor: pointer; font-size: 0.875rem; }
.back-btn:hover { background: #475569; }
.content { max-width: 800px; margin: 0 auto; padding: 2rem; }
.markdown-body { background: #1e293b; border-radius: 1rem; padding: 2rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
.markdown-body h1 { color: #38bdf8; margin-bottom: 1rem; font-size: 2rem; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; }
.markdown-body h2 { color: #22d3ee; margin-top: 1.5rem; margin-bottom: 0.75rem; font-size: 1.5rem; }
.markdown-body h3 { color: #a5f3fc; margin-top: 1.25rem; margin-bottom: 0.5rem; font-size: 1.25rem; }
.markdown-body h4 { color: #67e8f9; margin-top: 1rem; margin-bottom: 0.5rem; font-size: 1.1rem; }
.markdown-body p { margin-bottom: 1rem; }
.markdown-body ul, .markdown-body ol { margin-left: 1.5rem; margin-bottom: 1rem; }
.markdown-body li { margin-bottom: 0.25rem; }
.markdown-body code { background: #0f172a; padding: 0.2rem 0.4rem; border-radius: 0.25rem; font-family: 'Fira Code', monospace; font-size: 0.875rem; color: #fcd34d; }
.markdown-body pre { background: #0f172a; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; margin-bottom: 1rem; }
.markdown-body pre code { padding: 0; display: block; }
.markdown-body blockquote { border-left: 4px solid #38bdf8; padding-left: 1rem; margin-left: 0; margin-bottom: 1rem; color: #94a3b8; background: rgba(56,189,248,0.1); padding: 0.5rem 1rem; border-radius: 0 0.5rem 0.5rem 0; }
.markdown-body a { color: #38bdf8; text-decoration: none; }
.markdown-body a:hover { text-decoration: underline; }
.markdown-body hr { border: none; border-top: 1px solid #334155; margin: 2rem 0; }
.markdown-body table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
.markdown-body th, .markdown-body td { border: 1px solid #334155; padding: 0.5rem; text-align: left; }
.markdown-body th { background: #0f172a; }
.markdown-body img { max-width: 100%; border-radius: 0.5rem; }
.markdown-body .mermaid { background: #0f172a; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; border: 1px solid #334155; white-space: pre; }
'''

script_part = '''
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
'''

js_part = '''
    <script>
        function goBack() { window.location.href = "index.html"; }
        MathJax.config = {
            tex: {
                inlineMath: [["$", "$"], ["\\\\(", "\\\\)"]],
                displayMath: [["$$", "$$"], ["\\\\[", "\\\\]"]],
                processEscapes: true
            }
        };
        document.addEventListener("DOMContentLoaded", function() {
            mermaid.initialize({
                startOnLoad: true,
                theme: "dark",
                themeVariables: {
                    primaryColor: "#38bdf8",
                    primaryTextColor: "#e2e8f0",
                    primaryBorderColor: "#334155",
                    lineColor: "#64748b",
                    secondaryColor: "#1e293b",
                    tertiaryColor: "#0f172a"
                }
            });
        });
    </script>
'''

def fix_mermaid_blocks(html):
    pattern = r'<pre><code class="language-mermaid">(.*?)</code></pre>'
    def replacer(m):
        content = m.group(1)
        content = re.sub(r'^<br\s*/?>', '', content, flags=re.MULTILINE)
        content = re.sub(r'<br\s*/?>$', '', content, flags=re.MULTILINE)
        return '<pre class="mermaid">' + content + '</pre>'
    return re.sub(pattern, replacer, html, flags=re.DOTALL)

def gen_html(md_content, title):
    html_content = markdown.markdown(
        md_content,
        extensions=["extra", "sane_lists", "tables", "fenced_code"],
        output_format="html5"
    )
    html_content = fix_mermaid_blocks(html_content)
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{css}</style>
    {script_part}
</head>
<body>
    <div class="header">
        <button class="back-btn" onclick="goBack()">← 返回课程列表</button>
        <div class="logo">Embody Course Modules</div>
    </div>
    <div class="content">
        <div class="markdown-body">
            {html_content}
        </div>
    </div>
    {js_part}
</body>
</html>'''.format(title=title, css=css, script_part=script_part, html_content=html_content, js_part=js_part)

md_files = [f for f in os.listdir(MODULE_DIR) if f.endswith('.md') and f.startswith('模块')]

total_mermaid_fixed = 0

for md_file in md_files:
    md_path = os.path.join(MODULE_DIR, md_file)
    html_file = md_file.replace('.md', '.html')
    html_path = os.path.join(MODULE_DIR, html_file)
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        mermaid_count = md_content.count('```mermaid')
        if mermaid_count > 0:
            print(f"  [mermaid] {md_file}: {mermaid_count} blocks found")

        title = md_file.replace('.md', '')
        html = gen_html(md_content, title)

        fixed_count = html.count('class="mermaid"')
        if fixed_count > 0:
            total_mermaid_fixed += fixed_count
            print(f"  [fixed] {html_file}: {fixed_count} mermaid blocks converted")

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"OK {md_file} -> {html_file}")
    except Exception as e:
        print(f"FAIL {md_file}: {e}")

print(f"\nDone! {len(md_files)} files converted.")
print(f"Mermaid blocks fixed: {total_mermaid_fixed}")