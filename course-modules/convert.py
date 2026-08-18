#!/usr/bin/env python3
import os
import markdown

CSS_STYLE = '''
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
'''

def generate_html(md_content, title):
    html_content = markdown.markdown(md_content, extensions=['extra', 'sane_lists', 'tables'])
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{CSS_STYLE}</style>
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
    <script>
        function goBack() {{
            window.location.href = 'index.html';
        }}
    </script>
</body>
</html>'''
    return html

def convert_files():
    module_dir = '/www/wwwroot/iot-pub/course-modules'
    md_files = [f for f in os.listdir(module_dir) if f.endswith('.md')]
    
    for md_file in md_files:
        md_path = os.path.join(module_dir, md_file)
        html_file = md_file.replace('.md', '.html')
        html_path = os.path.join(module_dir, html_file)
        
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            title = md_file.replace('.md', '')
            html = generate_html(md_content, title)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f'✓ {md_file} -> {html_file}')
        except Exception as e:
            print(f'✗ {md_file}: {e}')

if __name__ == '__main__':
    convert_files()