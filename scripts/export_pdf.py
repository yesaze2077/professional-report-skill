#!/usr/bin/env python3
"""Print a local HTML file with an already installed Playwright/Chromium; no downloads."""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import sys


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--browser',help='已安装Chromium/Chrome可执行文件路径')
    p.add_argument('--force',action='store_true')
    a=p.parse_args()
    try:
        if not a.input.is_file():raise ValueError('HTML文件不存在')
        if a.output.exists() and not a.force:raise ValueError('输出已存在；请换名或显式使用--force')
        browser=a.browser or shutil.which('chromium') or shutil.which('google-chrome') or shutil.which('chromium-browser')
        if not browser:raise ValueError('未找到已安装的Chromium；可使用--browser，或在浏览器中打印为PDF')
        from playwright.sync_api import sync_playwright
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with sync_playwright() as pw:
            b=pw.chromium.launch(executable_path=browser,headless=True)
            page=b.new_page()
            page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(('file:','data:')) else route.abort())
            page.set_content(a.input.read_text(encoding='utf-8'),wait_until='load')
            page.evaluate('document.fonts.ready')
            page.pdf(path=str(a.output),format='A4',print_background=True,prefer_css_page_size=True)
            b.close()
        print(f'已导出：{a.output}（需另行检查最终分页与可读性）')
        return 0
    except Exception as e:  # Optional browser/runtime errors are surfaced, never hidden.

        print(f'未导出：{e}。本脚本不会下载依赖或浏览器。',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
