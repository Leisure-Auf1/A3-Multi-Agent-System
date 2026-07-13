#!/usr/bin/env python3
"""
Node 2 + Node 3 Exercise — Git Tree 对象 + Commit DAG 仿真

学生的任务:
  Node 2 — Tree 对象:
    1. encode_tree_entry(mode, name, sha1_binary) → bytes
    2. build_tree(entries, repo_path) → 40位hex SHA1
    3. read_tree(repo_path, sha1_hex) → list[(mode, name, sha1_hex)]

  Node 3 — Commit + DAG:
    4. create_commit(repo_path, tree_sha1, parent_sha1s, message, ...) → 40位hex SHA1
    5. read_commit(repo_path, sha1_hex) → dict
    6. find_merge_base(graph, sha1_a, sha1_b) → SHA1 | None
    7. visualize_dag(graph, head_sha1, refs) → ASCII string

核心格式:
  - Tree entry:  b"<mode> <name>\\0<20-byte raw SHA1>"
  - Commit:      "commit <size>\\0tree <sha1>\\nparent <sha1>\\nauthor ...\\n\\n<message>"

运行自测: python outputs/exercise.py
完整测试:
  python outputs/node-2-tests.py   (Node 2)
  python outputs/node-3-tests.py   (Node 3)
"""

import hashlib
import os
import time
import zlib


# ═══════════════════════════════════════════════════════════════
# Node 2 — Tree 对象
# ═══════════════════════════════════════════════════════════════


def encode_tree_entry(mode: int, name: str, sha1_binary: bytes) -> bytes:
    """
    将一条 tree entry 编码为原始字节。

    entry 格式: b"<mode> <name>\\0<20-byte SHA1>"

    ┌──────────── 构造步骤 ────────────┐
    │ mode = 100644                    │
    │ name = "README.md"               │
    │ sha1_binary = b"\\x95\\xd0..."    │  ← 20 bytes raw!
    │                                  │
    │ prefix = f"{mode} {name}\\0"      │
    │        = b"100644 README.md\\0"   │
    │                                  │
    │ return prefix + sha1_binary      │
    └──────────────────────────────────┘

    参数:
        mode: 权限位 (int, 如 100644)
        name: 文件名 (str)
        sha1_binary: 20字节的二进制SHA1 (bytes, 不是 hex 字符串!)
    返回:
        entry 的原始字节 (bytes)
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    pass


def build_tree(entries: list, repo_path: str = ".git") -> str:
    """
    从 entries 列表创建 tree 对象，写入 .git/objects，返回 40位hex SHA1。

    entries: [(mode, name, sha1_hex), ...]
      例: [(100644, "README.md", "95d09f2b..."), ...]
      mode=40000 表示子 tree (子目录)

    等价于: git mktree

    ┌──────────── 完整步骤 ────────────┐
    │ 1. 按 name 字典序排序 entries    │
    │    (否则 SHA1 和 git 不一致!)     │
    │ 2. 编码每条 entry               │
    │    sha1_hex → bytes.fromhex()   │
    │    → encode_tree_entry()        │
    │ 3. 拼接所有 entries → body      │
    │ 4. 构造 header:                 │
    │    f"tree {len(body)}\\0"        │
    │ 5. store = header + body        │
    │ 6. SHA1(store) → 40位hex        │
    │ 7. zlib.compress(store)         │
    │    → .git/objects/xx/xxx...     │
    └──────────────────────────────────┘

    参数:
        entries: [(mode, name, sha1_hex), ...] 列表
        repo_path: .git 目录路径
    返回:
        40位小写 hex SHA1 字符串 (str)
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    pass


def read_tree(repo_path: str, sha1_hex: str) -> list:
    """
    从 .git/objects 读取 tree 对象，解析出所有 entries。

    返回: [(mode, name, sha1_hex), ...]
      例: [(100644, "README.md", "95d09f2b..."), (40000, "src", "7a8b9c0d...")]

    等价于: git ls-tree <sha1>

    ┌──────────── 完整步骤 ────────────┐
    │ 1. 定位: <repo>/objects/        │
    │    <sha1[:2]>/<sha1[2:]>        │
    │ 2. 读文件 → zlib.decompress()   │
    │ 3. 找第一个 \\x00 → 剥离         │
    │    "tree <size>\\0" header       │
    │ 4. pos = 0                      │
    │    while pos < len(body):       │
    │      a. 找 \\x00 → null_pos      │
    │      b. body[pos:null_pos]      │
    │         → mode_name_bytes       │
    │      c. 找空格 → split mode     │
    │         & name                  │
    │      d. body[null+1:null+21]    │
    │         → 20 bytes raw SHA1     │
    │      e. raw.hex() → sha1_hex    │
    │      f. pos = null_pos + 21     │
    └──────────────────────────────────┘

    参数:
        repo_path: .git 目录路径
        sha1_hex: 40位 hex tree SHA1
    返回:
        [(mode, name, sha1_hex), ...] 列表
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    pass


# ═══════════════════════════════════════════════════════════════
# Node 3 — Commit + DAG
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
    创建一个 commit 对象，写入 .git/objects，返回 40位hex SHA1。

    ┌──────────── Commit 对象格式 ────────────┐
    │ commit <size>\0                         │ ← header
    │ tree <tree_sha1>\n                      │ ← 必填: 指向根 tree
    │ parent <parent_sha1>\n                  │ ← 可选: 每个父 commit 一行
    │ author <name> <<email>> <ts> <tz>\n     │ ← 必填
    │ committer <name> <<email>> <ts> <tz>\n  │ ← 必填
    │ \n                                      │ ← 空行分隔
    │ <message>\n                             │ ← 提交消息
    └─────────────────────────────────────────┘

    关键细节:
    - 时间戳用 int(time.time()), 时区写 "+0800"
    - 换行符必须是 Unix \\n (不是 \\r\\n)
    - message 末尾不要多余空行
    - 初始 commit (无 parent) → parent_sha1s=[]

    等价于: git commit-tree <tree> -p <parent> -m "<message>"

    参数:
        repo_path: .git 目录路径
        tree_sha1: 根 tree 的 40位hex SHA1
        parent_sha1s: 父 commit SHA1 列表 (初始 commit 传空列表)
        message: 提交消息
        author_name: 作者名
        author_email: 作者邮箱
    返回:
        40位小写 hex SHA1
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    pass


def read_commit(repo_path: str, sha1_hex: str) -> dict:
    """
    从 .git/objects 读取 commit 对象，解析为字典。

    ┌──────────── 解析步骤 ────────────┐
    │ 1. 定位: objects/xx/xxx...       │
    │ 2. zlib 解压                     │
    │ 3. 找第一个 \\x00 → 剥离 header   │
    │ 4. body.decode() → 按 \\n 分割    │
    │ 5. 解析 header 字段 (直到空行):  │
    │    tree XXXXXX...                │
    │    parent XXXXXX...              │
    │    author Name <email> ts tz     │
    │    committer Name <email> ts tz  │
    │ 6. 空行之后 = message            │
    └──────────────────────────────────┘

    解析 author/committer 行技巧:
      "author Terence <t@d.dev> 1749778200 +0800"
      用 .rsplit(" ", 2) 拆出时间戳和时区
      用 .rfind("<") 拆出 name 和 email

    等价于: git cat-file -p <sha1>

    参数:
        repo_path: .git 目录路径
        sha1_hex: 40位 hex commit SHA1
    返回:
        {
          "tree": "7a8b9c0d...",
          "parents": ["a1b2c3d4...", ...],
          "author_name": "Terence",
          "author_email": "terence@demo.dev",
          "author_time": 1749778200,
          "author_tz": "+0800",
          "committer_name": "Terence",
          "committer_email": "terence@demo.dev",
          "committer_time": 1749778200,
          "committer_tz": "+0800",
          "message": "Initial commit",
          "sha1": "a1b2c3d4..."
        }
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    pass


def find_merge_base(graph: dict, sha1_a: str, sha1_b: str):
    """
    找两个 commit 的最近共同祖先 (Lowest Common Ancestor / Merge Base)。

    算法: BFS 染色 (two-phase BFS)
    Phase 1 — 从 A 出发染色:
      从 sha1_a BFS 遍历所有祖先, 标记为 visited_from_a
    Phase 2 — 从 B 出发找:
      从 sha1_b BFS 遍历祖先, 第一个在 visited_from_a 中的就是 LCA

    ┌──────────── 图示 ────────────┐
    │     B ← C (feature)          │
    │    /     \\                   │
    │  A ← D ← E ← F (main)       │
    │                              │
    │  merge_base(C, E) = A        │
    │  merge_base(C, F) = C        │
    └──────────────────────────────┘

    等价于: git merge-base <sha1_a> <sha1_b>

    参数:
        graph: {sha1: {"parents": [...], ...}, ...}
        sha1_a: 分支 A 的 tip commit SHA1
        sha1_b: 分支 B 的 tip commit SHA1
    返回:
        LCA 的 SHA1 字符串, 或 None (无共同祖先)
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    pass


def visualize_dag(graph: dict, head_sha1: str, refs: dict = None) -> str:
    """
    把 commit DAG 画成 ASCII 树形图。

    ┌──────────── 输出示例 ────────────┐
    │ └── a1b2c3d (main) Merge feat   │
    │     ├── e5f6a7b Update README    │
    │     │   └── d4c3b2a Initial      │
    │     └── c9d0e1f (feature) Feat   │
    │         └── d4c3b2a Initial      │
    └──────────────────────────────────┘

    递归渲染规则:
    - 每个节点显示短 SHA1 (前7位) + 分支标签 + 消息前50字符
    - "├──" 表示非最后一个兄弟, "└──" 表示最后一个
    - 子节点缩进: "│   " (非最后) 或 "    " (最后)
    - 用 visited set 避免重复渲染 (DAG 有共享祖先)

    参数:
        graph: {sha1: {"parents": [...], "message": "..."}, ...}
        head_sha1: 从哪个 commit 开始画
        refs: {"main": sha1, "feature": sha1, ...}  可选
    返回:
        ASCII 多行字符串
    """
    # ── 你的代码从这里开始 ──



    # ── 你的代码到这里结束 ──
    pass


# ═══════════════════════════════════════════════════════════════
# ── 自测区 (完成实现后取消注释运行) ──
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile

    print("=" * 60)
    print("  Node 2 + Node 3 Exercise: 自检")
    print("=" * 60)

    # ── Node 2 自测: encode_tree_entry ──
    print("\n── Node 2: encode_tree_entry ──")
    try:
        raw_sha1 = bytes.fromhex(
            "95d09f2b10159347eece71399a7e2e907ea3df4f"
        )
        entry = encode_tree_entry(100644, "README.md", raw_sha1)
        expected = b"100644 README.md\x00" + raw_sha1
        if entry == expected:
            print(f"✅ encode_tree_entry 输出正确 ({len(entry)} bytes)")
        else:
            print(f"❌ encode_tree_entry 输出不匹配")
            print(f"   期望: {expected!r}")
            print(f"   实际: {entry!r}")
    except NotImplementedError:
        print("⚠️  encode_tree_entry 尚未实现")
    except Exception as e:
        print(f"❌ encode_tree_entry 出错: {e}")

    # ── Node 2 自测: build_tree ──
    print("\n── Node 2: build_tree ──")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = os.path.join(tmpdir, ".git")
            os.makedirs(os.path.join(repo, "objects"))

            entries = [
                (100644, "README.md",
                 "95d09f2b10159347eece71399a7e2e907ea3df4f"),
            ]
            tree_sha1 = build_tree(entries, repo_path=repo)

            if isinstance(tree_sha1, str) and len(tree_sha1) == 40:
                print(f"✅ build_tree 返回 SHA1: {tree_sha1}")
                obj_path = os.path.join(
                    repo, "objects", tree_sha1[:2], tree_sha1[2:]
                )
                if os.path.exists(obj_path):
                    print(f"   ✓ tree 对象已写入磁盘")
                else:
                    print(f"   ✗ tree 对象未写入磁盘")
            else:
                print(f"❌ build_tree 返回值异常: {tree_sha1}")
    except NotImplementedError:
        print("⚠️  build_tree 尚未实现")
    except Exception as e:
        print(f"❌ build_tree 出错: {e}")

    # ── Node 2 自测: read_tree ──
    print("\n── Node 2: read_tree ──")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = os.path.join(tmpdir, ".git")
            os.makedirs(os.path.join(repo, "objects"))

            entries_in = [
                (100644, "main.py",
                 "95d09f2b10159347eece71399a7e2e907ea3df4f"),
            ]
            tree_sha1 = build_tree(entries_in, repo_path=repo)
            entries_out = read_tree(repo, tree_sha1)

            if entries_in == entries_out:
                print(f"✅ read_tree 往返正确: {entries_out}")
            else:
                print(f"❌ read_tree 往返失败")
                print(f"   输入: {entries_in}")
                print(f"   输出: {entries_out}")
    except NotImplementedError:
        print("⚠️  read_tree 或 build_tree 尚未实现")
    except Exception as e:
        print(f"❌ read_tree 出错: {e}")

    # ── Node 2 自测: 排序 ──
    print("\n── Node 2: 排序验证 ──")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = os.path.join(tmpdir, ".git")
            os.makedirs(os.path.join(repo, "objects"))

            entries_in = [
                (100644, "zebra.txt",
                 "95d09f2b10159347eece71399a7e2e907ea3df4f"),
                (100644, "alpha.txt",
                 "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"),
            ]
            tree_sha1 = build_tree(entries_in, repo_path=repo)
            entries_out = read_tree(repo, tree_sha1)

            names = [name for _, name, _ in entries_out]
            if names == sorted(names):
                print(f"✅ 排序正确: {names}")
            else:
                print(f"❌ 排序失败: {names} (期望: {sorted(names)})")
    except NotImplementedError:
        print("⚠️  排序测试跳过 (函数未实现)")
    except Exception as e:
        print(f"❌ 排序测试出错: {e}")

    # ── Node 3 自测: create_commit ──
    print("\n── Node 3: create_commit ──")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = os.path.join(tmpdir, ".git")
            os.makedirs(os.path.join(repo, "objects"))

            # 先建一个 tree (用上面的 build_tree)
            tree_sha1 = build_tree(
                [(100644, "README.md",
                  "95d09f2b10159347eece71399a7e2e907ea3df4f")],
                repo_path=repo,
            )

            commit_sha1 = create_commit(
                repo, tree_sha1, [],
                "Initial commit", "Student", "s@d.dev"
            )

            if isinstance(commit_sha1, str) and len(commit_sha1) == 40:
                print(f"✅ create_commit 返回 SHA1: {commit_sha1}")
                obj_path = os.path.join(
                    repo, "objects", commit_sha1[:2], commit_sha1[2:]
                )
                if os.path.exists(obj_path):
                    print(f"   ✓ commit 对象已写入磁盘")
                else:
                    print(f"   ✗ commit 对象未写入磁盘")
            else:
                print(f"❌ create_commit 返回值异常: {commit_sha1}")
    except NotImplementedError:
        print("⚠️  create_commit 尚未实现 (依赖 build_tree)")
    except Exception as e:
        print(f"❌ create_commit 出错: {e}")

    # ── Node 3 自测: read_commit ──
    print("\n── Node 3: read_commit ──")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = os.path.join(tmpdir, ".git")
            os.makedirs(os.path.join(repo, "objects"))

            tree_sha1 = build_tree(
                [(100644, "x.txt",
                  "95d09f2b10159347eece71399a7e2e907ea3df4f")],
                repo_path=repo,
            )
            commit_sha1 = create_commit(
                repo, tree_sha1, [],
                "Hello DAG", "Student", "s@d.dev"
            )
            info = read_commit(repo, commit_sha1)

            checks = [
                ("tree", info.get("tree") == tree_sha1),
                ("parents", info.get("parents") == []),
                ("author_name", info.get("author_name") == "Student"),
                ("message", info.get("message") == "Hello DAG"),
            ]
            all_ok = all(ok for _, ok in checks)
            if all_ok:
                print(f"✅ read_commit 解析正确")
            else:
                print(f"❌ read_commit 解析有误:")
                for field, ok in checks:
                    status = "✓" if ok else "✗"
                    print(f"   {status} {field}: {info.get(field)}")
    except NotImplementedError:
        print("⚠️  read_commit 或 create_commit 尚未实现")
    except Exception as e:
        print(f"❌ read_commit 出错: {e}")

    # ── Node 3 自测: find_merge_base ──
    print("\n── Node 3: find_merge_base ──")
    try:
        # 构造简单的 DAG:
        #  root ← A ← B (main)
        #        ↖ C (feature)
        graph = {
            "root": {"parents": [], "message": "init"},
            "A":    {"parents": ["root"], "message": "A"},
            "B":    {"parents": ["A"], "message": "B"},
            "C":    {"parents": ["A"], "message": "C"},
        }
        lca = find_merge_base(graph, "B", "C")
        if lca == "A":
            print(f"✅ find_merge_base(B, C) = A (正确)")
        elif lca is not None:
            print(f"❌ find_merge_base(B, C) = {lca} (期望: A)")
        else:
            print(f"❌ find_merge_base 返回 None")
    except NotImplementedError:
        print("⚠️  find_merge_base 尚未实现")
    except Exception as e:
        print(f"❌ find_merge_base 出错: {e}")

    # ── Node 3 自测: visualize_dag ──
    print("\n── Node 3: visualize_dag ──")
    try:
        graph = {
            "B": {"parents": ["A"], "message": "second commit"},
            "A": {"parents": ["root"], "message": "first commit"},
            "root": {"parents": [], "message": "initial"},
        }
        refs = {"main": "B"}
        ascii_art = visualize_dag(graph, "B", refs)
        if ascii_art and "B" in ascii_art and "root" in ascii_art:
            print(f"✅ visualize_dag 输出包含所有节点")
            print(ascii_art)
        else:
            print(f"❌ visualize_dag 输出异常: {ascii_art!r}")
    except NotImplementedError:
        print("⚠️  visualize_dag 尚未实现")
    except Exception as e:
        print(f"❌ visualize_dag 出错: {e}")

    print()
