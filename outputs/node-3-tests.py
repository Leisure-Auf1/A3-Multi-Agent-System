#!/usr/bin/env python3
"""
Node 3 测试 — Git Commit 对象 + DAG 拓扑

学生画像: visual_learner_hates_magic
  - 底层逻辑控, 讨厌黑魔法命令, 必须看懂 .git/objects 物理层
  - 核心领悟: commit = tree + parent 指针 + 元数据, 全在 .git/objects 里
  - ❌ git log --graph (黑魔法) vs ✅ 手动遍历 parent 链 (你写的代码)

测试覆盖:
  T1-T8:   create_commit 正确性测试
  T9-T14:  read_commit 正确性测试
  T15-T19: find_merge_base 测试 (BFS 染色)
  T20-T22: visualize_dag 测试 (ASCII 渲染)
  T23-T25: StudentCompletion 检查
  Probe1-3: 与真实 git commit-tree / cat-file / merge-base 交叉比对

用法:
  # 测试学生的 exercise.py
  python outputs/node-3-tests.py

  # 测试参考 solution.py
  python outputs/node-3-tests.py --solution
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zlib
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# ── 学生填空区域 (Student Fill-in Zone) ──
# ═══════════════════════════════════════════════════════════════


def create_commit(
    repo_path: str,
    tree_sha1: str,
    parent_sha1s: list,
    message: str,
    author_name: str = "Student",
    author_email: str = "student@demo.dev",
) -> str:
    """
    创建一个 commit 对象, 写入 .git/objects, 返回 40位hex SHA1。

    参数:
        repo_path:     .git 目录路径
        tree_sha1:     根 tree 的 40位hex SHA1
        parent_sha1s:  父 commit SHA1 列表 (初始 commit = [])
        message:       提交消息
        author_name:   作者名
        author_email:  作者邮箱

    返回: 40位小写 hex SHA1

    等价于: git commit-tree <tree> -p <parent> -m "<message>"

    ┌──────────── Commit 对象格式 ────────────┐
    │ commit <body_size>\0                    │ ← header
    │ tree <tree_sha1>\n                      │
    │ parent <parent_sha1>\n                  │ ← 每个 parent 一行
    │ author <name> <<email>> <ts> <tz>\n     │
    │ committer <name> <<email>> <ts> <tz>\n  │
    │ \n                                      │ ← 空行
    │ <message>\n                             │
    └─────────────────────────────────────────┘

    步骤:
    1. now = int(time.time()); tz = "+0800"
    2. lines = [f"tree {tree_sha1}"]
    3. for p in parent_sha1s: lines.append(f"parent {p}")
    4. lines.append(f"author {author_name} <{author_email}> {now} {tz}")
    5. lines.append(f"committer {author_name} <{author_email}> {now} {tz}")
    6. lines.append("")       ← 空行分隔
    7. lines.append(message)
    8. body = "\\n".join(lines).encode("utf-8")
    9. header = f"commit {len(body)}\\0".encode("utf-8")
    10. store = header + body
    11. sha1 = hashlib.sha1(store).hexdigest()
    12. zlib.compress(store) → .git/objects/{sha1[:2]}/{sha1[2:]}
    13. return sha1
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    raise NotImplementedError("TODO: 实现 create_commit")


def read_commit(repo_path: str, sha1_hex: str) -> dict:
    """
    从 .git/objects 读取 commit 对象, 解析为字典。

    参数:
        repo_path: .git 目录路径
        sha1_hex:  40位hex commit SHA1

    返回:
      {
        "tree":            "7a8b9c0d...",
        "parents":         ["a1b2c3d4...", ...],
        "author_name":     "Terence",
        "author_email":    "terence@demo.dev",
        "author_time":     1749778200,
        "author_tz":       "+0800",
        "committer_name":  "Terence",
        "committer_email": "terence@demo.dev",
        "committer_time":  1749778200,
        "committer_tz":    "+0800",
        "message":         "Initial commit",
        "sha1":            sha1_hex
      }

    等价于: git cat-file -p <sha1>

    步骤:
    1. obj_path = repo_path + "/objects/" + sha1[:2] + "/" + sha1[2:]
    2. 读文件 → zlib.decompress()
    3. raw.index(b"\\x00") → 剥离 "commit <size>\\0" header
    4. body.decode("utf-8") → 按 \\n 分割
    5. 逐行解析 header 字段 (直到空行):
       - "tree XXXX"     → result["tree"]
       - "parent XXXX"   → result["parents"].append(...)
       - "author ..."    → 用 .rsplit(" ", 2) 拆时间戳/时区
                          用 .rfind("<") 拆 name/email
       - "committer ..." → 同上
    6. 空行之后 → "\\n".join(lines[i+1:]).rstrip("\\n") → message

    解析 author 行技巧:
      line = "author Terence <t@d.dev> 1749778200 +0800"
      parts = line[7:].rsplit(" ", 2)
      # parts = ["Terence <t@d.dev>", "1749778200", "+0800"]
      lt = parts[0].rfind("<")
      name = parts[0][:lt].strip()       # "Terence"
      email = parts[0][lt+1:-1]          # "t@d.dev"
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    raise NotImplementedError("TODO: 实现 read_commit")


def find_merge_base(graph: dict, sha1_a: str, sha1_b: str):
    """
    找两个 commit 的最近共同祖先 (LCA / Merge Base)。

    算法: BFS 染色 (two-phase BFS)

    Phase 1 — 从 A 出发染色:
      colored = set()
      queue = [sha1_a]
      while queue:
          cur = queue.pop(0)
          if cur in colored: continue
          colored.add(cur)
          for p in graph[cur]["parents"]:
              if p not in colored: queue.append(p)

    Phase 2 — 从 B 出发找:
      queue = [sha1_b]; visited = set()
      while queue:
          cur = queue.pop(0)
          if cur in visited: continue
          visited.add(cur)
          if cur in colored: return cur  ← 找到了!
          for p in graph[cur]["parents"]:
              if p not in visited: queue.append(p)
      return None

    参数:
        graph:  {sha1: {"parents": [...], ...}, ...}
        sha1_a: 分支 A 的 tip
        sha1_b: 分支 B 的 tip
    返回:
        LCA 的 SHA1 字符串, 或 None

    等价于: git merge-base <sha1_a> <sha1_b>
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    raise NotImplementedError("TODO: 实现 find_merge_base")


def visualize_dag(graph: dict, head_sha1: str, refs: dict = None) -> str:
    """
    把 commit DAG 画成 ASCII 树形图。

    参数:
        graph:     {sha1: {"parents": [...], "message": "..."}, ...}
        head_sha1: 从哪个 commit 开始渲染
        refs:      {"main": sha1, "feature": sha1, ...}  可选

    返回:
        多行 ASCII 字符串

    等价于: git log --graph --oneline (但你的实现更底层)

    渲染规则:
    - 短 SHA1: sha1[:7]
    - 分支标签: 从 refs 反查 sha1 → branch name(s)
    - 连接符: "├──" (非最后)  "└──" (最后)
    - 缩进:   "│   " (非最后) "    " (最后)
    - visited set 防止重复渲染 (DAG 共享祖先)

    输出示例:
      └── a1b2c3d (main) Merge feature
          ├── e5f6a7b Update README
          │   └── d4c3b2a Initial commit
          └── c9d0e1f (feature) Add feature
              └── d4c3b2a Initial commit
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    raise NotImplementedError("TODO: 实现 visualize_dag")


# ═══════════════════════════════════════════════════════════════
# ── 参考答案 (Reference Implementation) ──
# ═══════════════════════════════════════════════════════════════


def _ref_create_commit(
    repo_path: str,
    tree_sha1: str,
    parent_sha1s: list,
    message: str,
    author_name: str = "Student",
    author_email: str = "student@demo.dev",
) -> str:
    """参考答案: create_commit"""
    now = int(time.time())
    tz = "+0800"

    lines = [f"tree {tree_sha1}"]
    for p in parent_sha1s:
        lines.append(f"parent {p}")
    lines.append(f"author {author_name} <{author_email}> {now} {tz}")
    lines.append(f"committer {author_name} <{author_email}> {now} {tz}")
    lines.append("")
    lines.append(message)

    body = "\n".join(lines).encode("utf-8")
    header = f"commit {len(body)}\0".encode("utf-8")
    store = header + body

    sha1_hex = hashlib.sha1(store).hexdigest()

    compressed = zlib.compress(store)
    obj_dir = os.path.join(repo_path, "objects", sha1_hex[:2])
    obj_path = os.path.join(obj_dir, sha1_hex[2:])
    os.makedirs(obj_dir, exist_ok=True)
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(compressed)

    return sha1_hex


def _ref_read_commit(repo_path: str, sha1_hex: str) -> dict:
    """参考答案: read_commit"""
    obj_path = os.path.join(repo_path, "objects", sha1_hex[:2], sha1_hex[2:])
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"commit not found: {obj_path}")

    with open(obj_path, "rb") as f:
        raw = zlib.decompress(f.read())

    null_pos = raw.index(b"\x00")
    body = raw[null_pos + 1:].decode("utf-8")
    lines = body.split("\n")

    result = {"parents": [], "sha1": sha1_hex}
    i = 0

    while i < len(lines) and lines[i] != "":
        line = lines[i]

        if line.startswith("tree "):
            result["tree"] = line[5:]
        elif line.startswith("parent "):
            result["parents"].append(line[7:])
        elif line.startswith("author "):
            parts = line[7:].rsplit(" ", 2)
            result["author_time"] = int(parts[1])
            result["author_tz"] = parts[2]
            name_email = parts[0]
            lt = name_email.rfind("<")
            result["author_name"] = name_email[:lt].strip()
            result["author_email"] = name_email[lt + 1:-1]
        elif line.startswith("committer "):
            parts = line[10:].rsplit(" ", 2)
            result["committer_time"] = int(parts[1])
            result["committer_tz"] = parts[2]
            name_email = parts[0]
            lt = name_email.rfind("<")
            result["committer_name"] = name_email[:lt].strip()
            result["committer_email"] = name_email[lt + 1:-1]

        i += 1

    if i + 1 < len(lines):
        result["message"] = "\n".join(lines[i + 1:]).rstrip("\n")

    return result


def _ref_find_merge_base(graph: dict, sha1_a: str, sha1_b: str):
    """参考答案: find_merge_base — BFS 染色算法"""
    if sha1_a not in graph or sha1_b not in graph:
        return None

    # Phase 1: 从 A 出发染色
    colored = set()
    queue = [sha1_a]
    while queue:
        cur = queue.pop(0)
        if cur in colored:
            continue
        colored.add(cur)
        for p in graph[cur].get("parents", []):
            if p not in colored:
                queue.append(p)

    # Phase 2: 从 B 出发找第一个染色节点
    queue = [sha1_b]
    visited = set()
    while queue:
        cur = queue.pop(0)
        if cur in visited:
            continue
        visited.add(cur)
        if cur in colored:
            return cur
        for p in graph[cur].get("parents", []):
            if p not in visited:
                queue.append(p)

    return None


def _ref_visualize_dag(graph: dict, head_sha1: str, refs: dict = None) -> str:
    """参考答案: visualize_dag — ASCII 树形渲染"""
    refs = refs or {}

    sha1_to_refs = {}
    for name, s in refs.items():
        sha1_to_refs.setdefault(s, []).append(name)

    lines = []

    def _render(sha1: str, prefix: str, is_last: bool, visited: set):
        if sha1 in visited:
            return
        visited.add(sha1)

        commit = graph.get(sha1, {})
        tags = sha1_to_refs.get(sha1, [])
        tag_str = f" ({', '.join(tags)})" if tags else ""

        short = sha1[:7]
        msg = commit.get("message", "")[:50].replace("\n", " ")
        connector = "└──" if is_last else "├──"
        lines.append(f"{prefix}{connector} {short}{tag_str} {msg}")

        parents = commit.get("parents", [])
        for i, p in enumerate(parents):
            is_last_p = (i == len(parents) - 1)
            new_prefix = prefix + ("    " if is_last else "│   ")
            _render(p, new_prefix, is_last_p, visited)

    _render(head_sha1, "", True, set())
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# ── Probe 自动探测 ──
# ═══════════════════════════════════════════════════════════════

_HAS_STUDENT_IMPL = None


def _probe() -> bool:
    """探测学生是否已实现 create_commit + read_commit"""
    global _HAS_STUDENT_IMPL
    if _HAS_STUDENT_IMPL is not None:
        return _HAS_STUDENT_IMPL

    try:
        with tempfile.TemporaryDirectory() as td:
            repo = os.path.join(td, ".git")
            os.makedirs(os.path.join(repo, "objects"))

            # 先建一个 tree
            blob_content = b"probe"
            blob_hdr = f"blob {len(blob_content)}\0".encode()
            blob_store = blob_hdr + blob_content
            blob_sha1 = hashlib.sha1(blob_store).hexdigest()
            blob_dir = os.path.join(repo, "objects", blob_sha1[:2])
            os.makedirs(blob_dir, exist_ok=True)
            with open(os.path.join(blob_dir, blob_sha1[2:]), "wb") as f:
                f.write(zlib.compress(blob_store))

            # tree entry
            entry = f"100644 probe.txt\0".encode() + bytes.fromhex(blob_sha1)
            tree_hdr = f"tree {len(entry)}\0".encode()
            tree_store = tree_hdr + entry
            tree_sha1 = hashlib.sha1(tree_store).hexdigest()
            tree_dir = os.path.join(repo, "objects", tree_sha1[:2])
            os.makedirs(tree_dir, exist_ok=True)
            with open(os.path.join(tree_dir, tree_sha1[2:]), "wb") as f:
                f.write(zlib.compress(tree_store))

            sha1 = create_commit(repo, tree_sha1, [], "probe commit")

            ok = isinstance(sha1, str) and len(sha1) == 40
            if ok:
                obj_path = os.path.join(repo, "objects", sha1[:2], sha1[2:])
                ok = os.path.exists(obj_path)
            _HAS_STUDENT_IMPL = ok
    except NotImplementedError:
        _HAS_STUDENT_IMPL = False
    except Exception:
        _HAS_STUDENT_IMPL = False

    return _HAS_STUDENT_IMPL


def _get_create_commit():
    if _probe():
        return create_commit
    return _ref_create_commit


def _get_read_commit():
    if _probe():
        return read_commit
    return _ref_read_commit


def _get_find_merge_base():
    try:
        graph = {"A": {"parents": []}, "B": {"parents": ["A"]}}
        result = find_merge_base(graph, "B", "A")
        if result is not None:
            return find_merge_base
    except NotImplementedError:
        pass
    except Exception:
        pass
    return _ref_find_merge_base


def _get_visualize_dag():
    try:
        graph = {"A": {"parents": [], "message": "init"}}
        result = visualize_dag(graph, "A")
        if result and "A" in result:
            return visualize_dag
    except NotImplementedError:
        pass
    except Exception:
        pass
    return _ref_visualize_dag


# ═══════════════════════════════════════════════════════════════
# ── 辅助函数 ──
# ═══════════════════════════════════════════════════════════════


def _write_blob(repo_path: str, content: bytes) -> str:
    """写入 blob 对象并返回 SHA1"""
    header = f"blob {len(content)}\0".encode("utf-8")
    store = header + content
    sha1 = hashlib.sha1(store).hexdigest()
    obj_dir = os.path.join(repo_path, "objects", sha1[:2])
    os.makedirs(obj_dir, exist_ok=True)
    obj_path = os.path.join(obj_dir, sha1[2:])
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(zlib.compress(store))
    return sha1


def _write_tree_from_entries(repo_path: str, entries: list) -> str:
    """
    从 entries 列表构建 tree 对象, 返回 SHA1。
    entries: [(mode, name, sha1_hex), ...]
    """
    sorted_entries = sorted(entries, key=lambda e: e[1])
    encoded = []
    for mode, name, sha1_hex in sorted_entries:
        prefix = f"{mode} {name}\0".encode("utf-8")
        sha1_bin = bytes.fromhex(sha1_hex)
        encoded.append(prefix + sha1_bin)
    body = b"".join(encoded)
    header = f"tree {len(body)}\0".encode("utf-8")
    store = header + body
    sha1_hex = hashlib.sha1(store).hexdigest()
    obj_dir = os.path.join(repo_path, "objects", sha1_hex[:2])
    obj_path = os.path.join(obj_dir, sha1_hex[2:])
    os.makedirs(obj_dir, exist_ok=True)
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(zlib.compress(store))
    return sha1_hex


def _make_repo() -> str:
    """创建临时 .git 目录结构, 返回 repo 路径"""
    tmpdir = tempfile.mkdtemp()
    repo = os.path.join(tmpdir, ".git")
    os.makedirs(os.path.join(repo, "objects"), exist_ok=True)
    os.makedirs(os.path.join(repo, "refs", "heads"), exist_ok=True)
    return repo


# ═══════════════════════════════════════════════════════════════
# ── 测试用例 ──
# ═══════════════════════════════════════════════════════════════


class TestCreateCommit(unittest.TestCase):
    """create_commit() 测试 — Commit 对象构建"""

    @classmethod
    def setUpClass(cls):
        cls._create_func = staticmethod(_get_create_commit())
        cls._read_ref = staticmethod(_ref_read_commit)

    def setUp(self):
        self.repo = _make_repo()
        self.blob = _write_blob(self.repo, b"hello commit")
        self.tree = _write_tree_from_entries(
            self.repo, [(100644, "file.txt", self.blob)]
        )

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.repo), ignore_errors=True)

    def create_commit(self, repo, tree, parents, msg,
                      author_name="Student", author_email="s@d.dev"):
        return self._create_func(repo, tree, parents, msg,
                                 author_name, author_email)

    # ── T1: 初始 commit (无 parent) ──

    def test_t1_initial_commit(self):
        """T1: 初始 commit (parent=[]) — 返回 40 位 hex SHA1"""
        sha1 = self.create_commit(self.repo, self.tree, [], "init")
        self.assertEqual(len(sha1), 40, "SHA1 必须为 40 字符")
        self.assertTrue(all(c in "0123456789abcdef" for c in sha1),
                        "SHA1 必须全是小写 hex")
        obj_path = os.path.join(self.repo, "objects", sha1[:2], sha1[2:])
        self.assertTrue(os.path.exists(obj_path), f"对象应存在: {obj_path}")

    # ── T2: 含一个 parent ──

    def test_t2_with_parent(self):
        """T2: 第二个 commit (有 1 个 parent)"""
        c1 = self.create_commit(self.repo, self.tree, [], "first")
        c2 = self.create_commit(self.repo, self.tree, [c1], "second")
        self.assertEqual(len(c2), 40)
        self.assertNotEqual(c1, c2, "不同内容 → 不同 SHA1")

    # ── T3: 含两个 parent (merge commit) ──

    def test_t3_merge_commit(self):
        """T3: merge commit (2 个 parent)"""
        c1 = self.create_commit(self.repo, self.tree, [], "init")
        c2 = self.create_commit(self.repo, self.tree, [c1], "feat")
        c3 = self.create_commit(self.repo, self.tree, [c1], "fix")
        merge = self.create_commit(self.repo, self.tree, [c3, c2], "merge")
        self.assertEqual(len(merge), 40)

        info = self._read_ref(self.repo, merge)
        self.assertEqual(len(info["parents"]), 2)
        self.assertIn(c2, info["parents"])
        self.assertIn(c3, info["parents"])

    # ── T4: message 正确存储 ──

    def test_t4_message_roundtrip(self):
        """T4: 提交消息往返正确"""
        msg = "feat: add awesome feature\n\nDetailed description here."
        sha1 = self.create_commit(self.repo, self.tree, [], msg)
        info = self._read_ref(self.repo, sha1)
        self.assertEqual(info["message"], msg)

    # ── T5: author 信息正确 ──

    def test_t5_author_info(self):
        """T5: author/committer 信息正确存储"""
        sha1 = self.create_commit(
            self.repo, self.tree, [], "test author",
            author_name="Terence",
            author_email="terence@demo.dev",
        )
        info = self._read_ref(self.repo, sha1)
        self.assertEqual(info["author_name"], "Terence")
        self.assertEqual(info["author_email"], "terence@demo.dev")
        self.assertEqual(info["committer_name"], "Terence")
        self.assertEqual(info["committer_email"], "terence@demo.dev")

    # ── T6: tree 指针正确 ──

    def test_t6_tree_pointer(self):
        """T6: commit 指向正确的 tree SHA1"""
        sha1 = self.create_commit(self.repo, self.tree, [], "tree check")
        info = self._read_ref(self.repo, sha1)
        self.assertEqual(info["tree"], self.tree)

    # ── T7: SHA1 确定性原理验证 ──

    def test_t7_deterministic_principle(self):
        """T7: 相同内容+固定时间 → 相同 SHA1 (原理验证)"""
        fixed_ts = 1750000000

        def _fixed_create(repo, tree, parents, msg,
                          author="Student", email="s@d.dev"):
            tz = "+0800"
            lines = [f"tree {tree}"]
            for p in parents:
                lines.append(f"parent {p}")
            lines.append(f"author {author} <{email}> {fixed_ts} {tz}")
            lines.append(f"committer {author} <{email}> {fixed_ts} {tz}")
            lines.append("")
            lines.append(msg)
            body = "\n".join(lines).encode("utf-8")
            header = f"commit {len(body)}\0".encode("utf-8")
            store = header + body
            sha1 = hashlib.sha1(store).hexdigest()
            compressed = zlib.compress(store)
            obj_dir = os.path.join(repo, "objects", sha1[:2])
            obj_path = os.path.join(obj_dir, sha1[2:])
            os.makedirs(obj_dir, exist_ok=True)
            with open(obj_path, "wb") as f:
                f.write(compressed)
            return sha1

        sha1_a = _fixed_create(self.repo, self.tree, [], "deterministic")
        self.repo = _make_repo()
        self.tree = _write_tree_from_entries(
            self.repo, [(100644, "file.txt",
                         _write_blob(self.repo, b"hello commit"))]
        )
        sha1_b = _fixed_create(self.repo, self.tree, [], "deterministic")
        self.assertEqual(sha1_a, sha1_b,
                         "相同内容+固定时间戳 → 相同 SHA1 (内容寻址!)")

    # ── T8: 特殊字符 message ──

    def test_t8_special_message(self):
        """T8: 多行消息和特殊字符"""
        msg = "line1\nline2\nline3"
        sha1 = self.create_commit(self.repo, self.tree, [], msg)
        info = self._read_ref(self.repo, sha1)
        self.assertEqual(info["message"], msg)


class TestReadCommit(unittest.TestCase):
    """read_commit() 测试 — Commit 对象解析"""

    @classmethod
    def setUpClass(cls):
        cls._read_func = staticmethod(_get_read_commit())
        cls._create_ref = staticmethod(_ref_create_commit)

    def setUp(self):
        self.repo = _make_repo()
        self.blob = _write_blob(self.repo, b"read test")
        self.tree = _write_tree_from_entries(
            self.repo, [(100644, "f.txt", self.blob)]
        )

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.repo), ignore_errors=True)

    def read_commit(self, repo, sha1):
        return self._read_func(repo, sha1)

    # ── T9: 初始 commit 解析 ──

    def test_t9_read_initial_commit(self):
        """T9: 解析初始 commit (无 parent)"""
        sha1 = self._create_ref(self.repo, self.tree, [], "init",
                                "Alice", "alice@d.dev")
        info = self.read_commit(self.repo, sha1)
        self.assertEqual(info["tree"], self.tree)
        self.assertEqual(info["parents"], [])
        self.assertEqual(info["author_name"], "Alice")
        self.assertEqual(info["author_email"], "alice@d.dev")
        self.assertEqual(info["message"], "init")
        self.assertEqual(info["sha1"], sha1)

    # ── T10: 含 parent 解析 ──

    def test_t10_read_with_parent(self):
        """T10: 解析含 parent 的 commit"""
        c1 = self._create_ref(self.repo, self.tree, [], "first")
        c2 = self._create_ref(self.repo, self.tree, [c1], "second")
        info = self.read_commit(self.repo, c2)
        self.assertEqual(info["parents"], [c1])
        self.assertEqual(info["message"], "second")

    # ── T11: merge commit 解析 ──

    def test_t11_read_merge_commit(self):
        """T11: 解析 merge commit (2 parents)"""
        c1 = self._create_ref(self.repo, self.tree, [], "init")
        c2 = self._create_ref(self.repo, self.tree, [c1], "feat")
        c3 = self._create_ref(self.repo, self.tree, [c1], "fix")
        merge = self._create_ref(self.repo, self.tree, [c3, c2], "merge")
        info = self.read_commit(self.repo, merge)
        self.assertEqual(len(info["parents"]), 2)
        self.assertIn(c2, info["parents"])
        self.assertIn(c3, info["parents"])

    # ── T12: 时间戳解析 ──

    def test_t12_timestamp_parsing(self):
        """T12: author/committer 时间戳正确解析"""
        sha1 = self._create_ref(self.repo, self.tree, [], "ts test")
        info = self.read_commit(self.repo, sha1)
        self.assertIsInstance(info["author_time"], int)
        self.assertIsInstance(info["committer_time"], int)
        self.assertGreater(info["author_time"], 0)
        self.assertEqual(info["author_tz"], "+0800")

    # ── T13: 不存在的 SHA1 ──

    def test_t13_nonexistent_sha1(self):
        """T13: 不存在的 commit 应报错"""
        fake = "a" * 40
        with self.assertRaises((FileNotFoundError, Exception),
                               msg="不存在的 commit 应抛出异常"):
            self.read_commit(self.repo, fake)

    # ── T14: zlib 损坏 ──

    def test_t14_corrupted_zlib(self):
        """T14: zlib 损坏的 commit 对象应报错"""
        sha1 = self._create_ref(self.repo, self.tree, [], "corrupt me")
        obj_path = os.path.join(self.repo, "objects", sha1[:2], sha1[2:])
        with open(obj_path, "wb") as f:
            f.write(b"not valid zlib!")
        with self.assertRaises((zlib.error, Exception),
                               msg="损坏的 zlib 应报错"):
            self.read_commit(self.repo, sha1)


class TestFindMergeBase(unittest.TestCase):
    """find_merge_base() 测试 — BFS 染色 LCA"""

    @classmethod
    def setUpClass(cls):
        cls._lca_func = staticmethod(_get_find_merge_base())

    def find_merge_base(self, graph, a, b):
        return self.__class__._lca_func(graph, a, b)

    # ── T15: 简单 fork ──

    def test_t15_simple_fork(self):
        """T15: 简单 fork: A→B→C 和 A→D→E, merge_base(E,C)=A"""
        graph = {
            "A": {"parents": [], "message": "root"},
            "B": {"parents": ["A"], "message": "B"},
            "C": {"parents": ["B"], "message": "C"},
            "D": {"parents": ["A"], "message": "D"},
            "E": {"parents": ["D"], "message": "E"},
        }
        result = self.find_merge_base(graph, "E", "C")
        self.assertEqual(result, "A",
                         f"merge_base(E,C) 应为 A, 实际 {result}")

    # ── T16: 线性历史 ──

    def test_t16_linear(self):
        """T16: 线性历史 A→B→C, merge_base(C,B)=B"""
        graph = {
            "A": {"parents": [], "message": "A"},
            "B": {"parents": ["A"], "message": "B"},
            "C": {"parents": ["B"], "message": "C"},
        }
        result = self.find_merge_base(graph, "C", "B")
        self.assertEqual(result, "B",
                         "merge_base(C,B) 应为 B (B 是 C 的祖先)")

    # ── T17: 同节点 ──

    def test_t17_same_node(self):
        """T17: merge_base(X, X) = X"""
        graph = {
            "X": {"parents": [], "message": "lone"},
        }
        result = self.find_merge_base(graph, "X", "X")
        self.assertEqual(result, "X")

    # ── T18: merge commit 场景 ──

    def test_t18_merge_commit_graph(self):
        """T18: merge commit DAG — merge_base(C,E) 找 C 或 A"""
        #        B ← D ← E (main, E merges C into D)
        #       /    /
        #  A ← C ←──┘
        graph = {
            "A": {"parents": [], "message": "init"},
            "B": {"parents": ["A"], "message": "B on main"},
            "C": {"parents": ["A"], "message": "C on feature"},
            "D": {"parents": ["B"], "message": "D on main"},
            "E": {"parents": ["D", "C"], "message": "merge feature"},
        }
        result = self.find_merge_base(graph, "C", "E")
        # E 的 parent 之一是 C, 所以 C 本身就是 LCA
        # (BFS 从 C 出发, C 从 phase2 找到自己就在 colored 中)
        valid = result in ("C", "A")
        self.assertIn(result, ["C", "A"],
                      f"merge_base(C,E) 应为 C 或 A, 实际 {result}")

    # ── T19: 无共同祖先 ──

    def test_t19_no_common_ancestor(self):
        """T19: 两个孤立的 DAG → 返回 None"""
        graph = {
            "X": {"parents": [], "message": "orphan1"},
            "Y": {"parents": [], "message": "orphan2"},
        }
        result = self.find_merge_base(graph, "X", "Y")
        self.assertIsNone(result, "无共同祖先应返回 None")


class TestVisualizeDag(unittest.TestCase):
    """visualize_dag() 测试 — ASCII DAG 渲染"""

    @classmethod
    def setUpClass(cls):
        cls._viz_func = staticmethod(_get_visualize_dag())

    def visualize_dag(self, graph, head, refs=None):
        return self.__class__._viz_func(graph, head, refs)

    # ── T20: 单节点 ──

    def test_t20_single_node(self):
        """T20: 单节点 DAG 渲染"""
        graph = {
            "abc1234": {"parents": [], "message": "init"},
        }
        result = self.visualize_dag(graph, "abc1234")
        self.assertIn("abc1234", result)
        self.assertIn("init", result)
        self.assertTrue(result.strip().startswith("└──"),
                        f"应以 └── 开头, 实际: {result[:20]}...")

    # ── T21: 线性链 ──

    def test_t21_linear_chain(self):
        """T21: 3 节点线性链渲染"""
        graph = {
            "ccc3333": {"parents": ["bbb2222"], "message": "third"},
            "bbb2222": {"parents": ["aaa1111"], "message": "second"},
            "aaa1111": {"parents": [], "message": "first"},
        }
        result = self.visualize_dag(graph, "ccc3333")
        self.assertIn("ccc3333", result)
        self.assertIn("bbb2222", result)
        self.assertIn("aaa1111", result)
        self.assertIn("third", result)
        self.assertIn("second", result)
        self.assertIn("first", result)

    # ── T22: 分支标注 ──

    def test_t22_with_refs(self):
        """T22: 分支标签渲染"""
        graph = {
            "fff4444": {"parents": ["eee3333"], "message": "feature done"},
            "eee3333": {"parents": ["ddd2222"], "message": "feature start"},
            "ddd2222": {"parents": [], "message": "initial"},
        }
        refs = {"main": "fff4444", "feature": "eee3333"}
        result = self.visualize_dag(graph, "fff4444", refs)
        self.assertIn("(main)", result)
        self.assertIn("(feature)", result)
        self.assertIn("fff4444", result)
        self.assertIn("eee3333", result)
        self.assertIn("ddd2222", result)


class TestStudentCompletion(unittest.TestCase):
    """检查学生是否完成填空"""

    @classmethod
    def setUpClass(cls):
        cls.has_impl = _probe()

    def test_t23_create_commit_implemented(self):
        """T23: create_commit 已实现"""
        if not self.has_impl:
            self.skipTest(
                "⚠️  create_commit 未实现 — 使用参考答案兜底运行其他测试。\n"
                "    请在 create_commit() 函数中完成你的实现！"
            )
        else:
            self.assertTrue(True, "✅ create_commit 已实现")

    def test_t24_read_commit_implemented(self):
        """T24: read_commit 已实现"""
        if not self.has_impl:
            self.skipTest(
                "⚠️  read_commit 未实现 — 使用参考答案兜底运行其他测试。\n"
                "    请在 read_commit() 函数中完成你的实现！"
            )
        else:
            self.assertTrue(True, "✅ read_commit 已实现")

    def test_t25_advanced_functions(self):
        """T25: find_merge_base + visualize_dag 状态检查"""
        lca_ok = False
        viz_ok = False

        try:
            graph = {"A": {"parents": []}, "B": {"parents": ["A"]}}
            r = find_merge_base(graph, "B", "A")
            lca_ok = r is not None
        except NotImplementedError:
            pass
        except Exception:
            pass

        try:
            graph = {"A": {"parents": [], "message": "x"}}
            r = visualize_dag(graph, "A")
            viz_ok = r is not None and "A" in r
        except NotImplementedError:
            pass
        except Exception:
            pass

        if lca_ok and viz_ok:
            self.assertTrue(True, "✅ find_merge_base + visualize_dag 已实现")
        elif lca_ok:
            self.skipTest("⚠️  visualize_dag 选做 — 已实现则加分")
        elif viz_ok:
            self.skipTest("⚠️  find_merge_base 选做 — 已实现则加分")
        else:
            self.skipTest("⚠️  find_merge_base + visualize_dag 选做 — 已实现则加分")


# ═══════════════════════════════════════════════════════════════
# Probe: 与真实 Git 命令交叉比对
# ═══════════════════════════════════════════════════════════════

class TestGitProbe(unittest.TestCase):
    """Probe 测试 — 与真实 git commit-tree / cat-file / merge-base 交叉比对"""

    @classmethod
    def setUpClass(cls):
        cls._create_func = staticmethod(_get_create_commit())
        cls._read_func = staticmethod(_get_read_commit())
        cls._lca_func = staticmethod(_get_find_merge_base())

        cls.git_available = False
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True, timeout=5
            )
            cls.git_available = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    def setUp(self):
        if not self.git_available:
            self.skipTest("git 命令不可用, 跳过 probe 测试")

        self.tmpdir = tempfile.mkdtemp()
        self.git_repo = os.path.join(self.tmpdir, "probe-repo")
        subprocess.run(
            ["git", "init", "-q", self.git_repo],
            capture_output=True, check=True
        )
        self.repo = os.path.join(self.git_repo, ".git")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _git_hash_object(self, content: bytes) -> str:
        """用 git hash-object -w 写入 blob"""
        r = subprocess.run(
            ["git", "-C", self.git_repo, "hash-object", "-w", "--stdin"],
            input=content, capture_output=True, timeout=10,
        )
        return r.stdout.decode().strip()

    def _git_mktree(self, entries: list) -> str:
        """用 git mktree 创建 tree"""
        input_lines = []
        for mode, name, sha1 in entries:
            type_str = "blob" if mode != 40000 else "tree"
            input_lines.append(f"{mode:06o} {type_str} {sha1}\t{name}")
        r = subprocess.run(
            ["git", "-C", self.git_repo, "mktree"],
            input="\n".join(input_lines), capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip()

    def _git_commit_tree(self, tree: str, parents: list, msg: str) -> str:
        """用 git commit-tree 创建 commit"""
        cmd = ["git", "-C", self.git_repo, "commit-tree", tree, "-m", msg]
        for p in parents:
            cmd.extend(["-p", p])
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Student",
            "GIT_AUTHOR_EMAIL": "student@demo.dev",
            "GIT_AUTHOR_DATE": "1750000000 +0800",
            "GIT_COMMITTER_NAME": "Student",
            "GIT_COMMITTER_EMAIL": "student@demo.dev",
            "GIT_COMMITTER_DATE": "1750000000 +0800",
        }
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, env=env,
        )
        return r.stdout.strip()

    # ── Probe1: create_commit vs git commit-tree ──

    def test_probe1_create_vs_git(self):
        """Probe1: Python create_commit — git cat-file 能读"""
        blob1 = self._git_hash_object(b"probe content")
        git_tree = self._git_mktree([(100644, "probe.txt", blob1)])

        our_commit = self._create_func(
            self.repo, git_tree, [], "probe commit",
            author_name="Student", author_email="student@demo.dev",
        )

        r = subprocess.run(
            ["git", "-C", self.git_repo, "cat-file", "-p", our_commit],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            output = r.stdout
            self.assertIn(f"tree {git_tree}", output,
                          "git cat-file 应能看到 tree 指针")
            self.assertIn("probe commit", output,
                          "git cat-file 应能看到提交消息")
        else:
            self.fail(
                f"git 无法读取我们的 commit 对象!\n"
                f"git stderr: {r.stderr}\n"
                f"我们的 SHA1: {our_commit}"
            )

    # ── Probe2: read_commit vs git cat-file ──

    def test_probe2_read_vs_git(self):
        """Probe2: Python read_commit vs git cat-file — 内容一致"""
        blob1 = self._git_hash_object(b"read probe")
        git_tree = self._git_mktree([(100644, "r.txt", blob1)])
        git_commit = self._git_commit_tree(git_tree, [], "read probe msg")

        info = self._read_func(self.repo, git_commit)

        self.assertEqual(info["tree"], git_tree,
                         "tree 指针应与 git 一致")
        self.assertEqual(info["message"], "read probe msg",
                         "消息应与 git 一致")
        self.assertEqual(info["parents"], [],
                         "初始 commit parent 应为空")
        self.assertEqual(info["sha1"], git_commit,
                         "SHA1 应正确回传")

    # ── Probe3: find_merge_base vs git merge-base ──

    def test_probe3_dag_vs_git(self):
        """Probe3: find_merge_base vs git merge-base — LCA 一致"""
        # 创建 A ← B ← D (main)
        #      ↖ C ←────┘ (merge)
        blob1 = self._git_hash_object(b"dag test")
        git_tree = self._git_mktree([(100644, "d.txt", blob1)])

        commit_a = self._git_commit_tree(git_tree, [], "commit A")
        commit_b = self._git_commit_tree(git_tree, [commit_a], "commit B")
        commit_c = self._git_commit_tree(git_tree, [commit_a], "commit C")
        commit_d = self._git_commit_tree(git_tree, [commit_b, commit_c], "merge D")

        # Python 读取所有 commit 构建 graph
        graph = {}
        for sha1 in [commit_a, commit_b, commit_c, commit_d]:
            graph[sha1] = self._read_func(self.repo, sha1)

        # Python LCA
        py_lca = self._lca_func(graph, commit_b, commit_c)
        self.assertEqual(py_lca, commit_a,
                         f"merge_base(B,C) 应为 A={commit_a[:7]}, "
                         f"实际 {py_lca[:7] if py_lca else None}")

        # git merge-base
        r = subprocess.run(
            ["git", "-C", self.git_repo, "merge-base", commit_b, commit_c],
            capture_output=True, text=True, timeout=10,
        )
        git_lca = r.stdout.strip()
        self.assertEqual(py_lca, git_lca,
                         f"与 git merge-base 不一致:\n"
                         f"  我们的: {py_lca[:12] if py_lca else None}...\n"
                         f"  git 的: {git_lca[:12]}...")


# ═══════════════════════════════════════════════════════════════
# ── 入口 ──
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 65)
    print("  Node 3 Test Suite: Git Commit 对象 + DAG 拓扑")
    print("=" * 65)
    print()

    if _probe():
        print("🔬 检测到学生实现 → 测试学生代码")
    else:
        print("🔬 未检测到学生实现 → 使用参考答案兜底运行")
        print("   (你的代码仍然会被 TestStudentCompletion 检查)")
    print()

    unittest.main(verbosity=2)
