# -*- coding: utf-8 -*-
"""
自动发版脚本：把汉化补丁 zip 上传到 GitHub Release（不是 git 提交）。

用法:
    python publish_release.py                              # 自动找当天(最新)的 *-BlueArchive-steam-zh-cn-patch.zip
    python publish_release.py 2026-08-19-xxx.zip           # 指定文件（可多个）
    python publish_release.py --tag v2026-08-19 --notes-file 公告.md xxx.zip

认证优先级:
    1. 环境变量 GITHUB_TOKEN
    2. Windows 凭据管理器 (通过 git credential fill 动态获取, 脚本内不落盘不硬编码)

默认行为:
    - tag/发布名取自文件名里的日期: 2026-08-19-xxx.zip -> tag v2026-08-19
    - 同名 release 已存在则复用; 同名资产已存在则先删再传, 可重复执行
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

API = "https://api.github.com"
UPLOAD_API = "https://uploads.github.com"
DEFAULT_REPO = "delayboy/BlueArchive-Translator"
AUTO_GLOB = "*-BlueArchive-steam-zh-cn-patch.zip"  # 自动发现用：纯英文名补丁包


def get_repo() -> str:
    """从 git remote 解析 owner/repo，失败则用默认值。"""
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        # 支持 https://github.com/o/r.git 和 git@github.com:o/r.git
        m = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", url)
        if m:
            return m.group(1)
    except Exception:
        pass
    return DEFAULT_REPO


def get_token() -> str:
    """优先环境变量，否则从凭据管理器读取。"""
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    try:
        out = subprocess.run(
            ["git", "credential", "fill"],
            input=b"protocol=https\nhost=github.com\n\n",
            capture_output=True, check=True,
        ).stdout.decode("utf-8", "replace")
        for line in out.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except Exception:
        pass
    print("错误: 未取到 GitHub token。请设置环境变量 GITHUB_TOKEN，"
          "或先任意执行一次 git push 让凭据管理器保存 token。", file=sys.stderr)
    sys.exit(1)


class ProgressReader:
    """流式上传用文件包装器，每传 16MB 打印一次进度，避免 300MB+ 文件读进内存。"""

    STEP = 16 * 1024 * 1024

    def __init__(self, path: Path):
        self._f = open(path, "rb")
        self._total = path.stat().st_size
        self._done = 0
        self._next_mark = self.STEP
        self._t0 = time.time()
        print(f"  上传中: 0%")

    def read(self, n=-1):
        chunk = self._f.read(n)
        if chunk:
            self._done += len(chunk)
            if self._done >= self._next_mark or self._done >= self._total:
                self._next_mark += self.STEP
                speed = self._done / max(time.time() - self._t0, 0.1) / 1024 / 1024
                print(f"  上传中: {self._done * 100 // self._total}% "
                      f"({self._done // 1048576}/{self._total // 1048576} MB, {speed:.1f} MB/s)")
        return chunk

    def close(self):
        self._f.close()


def api_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def create_or_get_release(session, token, repo, tag, name, notes, prerelease) -> dict:
    """创建 release；若 tag 已存在则返回已有 release（幂等）。"""
    r = session.post(
        f"{API}/repos/{repo}/releases",
        headers=api_headers(token),
        json={
            "tag_name": tag,
            "target_commitish": "master",
            "name": name,
            "body": notes,
            "draft": False,
            "prerelease": prerelease,
        },
    )
    if r.status_code == 201:
        print(f"已创建 Release: {tag}")
        return r.json()
    if r.status_code == 422:  # already_exists -> 复用
        r2 = session.get(f"{API}/repos/{repo}/releases/tags/{tag}",
                         headers=api_headers(token))
        if r2.status_code == 200:
            print(f"Release {tag} 已存在，复用之")
            # 顺便更新发布说明
            rid = r2.json()["id"]
            session.patch(f"{API}/repos/{repo}/releases/{rid}",
                          headers=api_headers(token),
                          json={"name": name, "body": notes})
            return r2.json()
        r2.raise_for_status()
    r.raise_for_status()
    return r.json()


def upload_asset(session, token, repo, release_id, path: Path):
    name = path.name
    # 幂等：同名资产先删
    assets = session.get(
        f"{API}/repos/{repo}/releases/{release_id}/assets",
        headers=api_headers(token),
    ).json()
    for a in assets:
        if a["name"] == name:
            print(f"  删除旧资产: {name}")
            session.delete(a["url"], headers=api_headers(token))

    reader = ProgressReader(path)
    try:
        r = session.post(
            f"{UPLOAD_API}/repos/{repo}/releases/{release_id}/assets",
            params={"name": name},
            headers={
                **api_headers(token),
                "Content-Type": "application/zip",
                "Content-Length": str(path.stat().st_size),
            },
            data=reader,
        )
    finally:
        reader.close()
    if r.status_code != 201:
        print(f"  上传失败 HTTP {r.status_code}: {r.text[:500]}", file=sys.stderr)
        sys.exit(1)
    print(f"  上传成功: {r.json()['browser_download_url']}")


def guess_files() -> list[Path]:
    """自动发现最新日期的英文名补丁包。"""
    root = Path(__file__).parent
    cands = sorted(root.glob(AUTO_GLOB), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        print(f"错误: 未找到 {AUTO_GLOB}，请手动指定文件路径。", file=sys.stderr)
        sys.exit(1)
    print(f"自动选用: {cands[0].name}")
    return [cands[0]]


def default_notes(date_str: str) -> str:
    return (
        f"# {date_str} 蔚蓝档案 Steam 端简中汉化补丁\n\n"
        "- 对应大版本更新后的最新数据库密钥，重新适配完成\n"
        "- 下载下方 zip 压缩包，解压到游戏目录后按 README 说明安装\n"
        "- 遇到问题请在 Issue 区反馈\n"
    )


def main():
    ap = argparse.ArgumentParser(description="上传汉化补丁到 GitHub Release")
    ap.add_argument("files", nargs="*", help="zip 文件路径；缺省时自动发现")
    ap.add_argument("--tag", help="tag 名，默认 v<文件名中的日期>")
    ap.add_argument("--name", help="Release 标题，默认 '<日期> 蔚蓝档案steam端简中汉化补丁'")
    ap.add_argument("--notes", help="发布说明正文")
    ap.add_argument("--notes-file", help="发布说明正文(从文件读取)")
    ap.add_argument("--prerelease", action="store_true", help="标记为预发布")
    args = ap.parse_args()

    files = [Path(f) for f in args.files] if args.files else guess_files()
    for f in files:
        if not f.is_file():
            print(f"错误: 文件不存在 {f}", file=sys.stderr)
            sys.exit(1)

    repo = get_repo()
    token = get_token()
    session = requests.Session()

    # 日期取第一个文件名; tag 默认 v2026-08-19
    m = re.search(r"(\d{4}-\d{2}-\d{2})", files[0].name)
    date_str = m.group(1) if m else time.strftime("%Y-%m-%d")
    tag = args.tag or f"v{date_str}"
    name = args.name or f"{date_str} 蔚蓝档案steam端简中汉化补丁"
    if args.notes_file:
        notes = Path(args.notes_file).read_text(encoding="utf-8")
    else:
        notes = args.notes or default_notes(date_str)

    # 校验 token 权限
    who = session.get(f"{API}/user", headers=api_headers(token))
    if who.status_code != 200:
        print(f"错误: token 校验失败 HTTP {who.status_code}: {who.text[:300]}\n"
              f"凭据管理器里的 token 可能无 API 权限，请设置 GITHUB_TOKEN 环境变量。",
              file=sys.stderr)
        sys.exit(1)
    print(f"仓库: {repo}  账号: {who.json().get('login')}")

    release = create_or_get_release(session, token, repo, tag, name, notes, args.prerelease)
    rid = release["id"]
    for f in files:
        print(f"处理资产: {f.name} ({f.stat().st_size // 1048576} MB)")
        upload_asset(session, token, repo, rid, f)

    print(f"\n发版完成: {release['html_url']}")


if __name__ == "__main__":
    main()
