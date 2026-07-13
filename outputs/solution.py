#!/usr/bin/env python3
"""
Node 1 + Node 2 + Node 3 Solution — Git 物理存储层完整参考实现

Node 1 — Blob 对象:
  sha1_file(file_path)             → 40位hex SHA1
  read_blob(repo_path, sha1_hex)   → 原始内容 bytes

Node 2 — Tree 对象:
  encode_tree_entry(mode, name, sha1_binary) → bytes
  build_tree(entries, repo_path)            → 40位hex SHA1
  read_tree(repo_path, sha1_hex)            → list[(mode, name, sha1_hex)]
  read_tree_recursive(repo_path, sha1_hex)  → 递归列出所有文件

Node 3 — Commit + DAG:
  create_commit(repo_path, tree_sha1, parents, msg, ...) → 40位hex SHA1
  read_commit(repo_path, sha1_hex)                       → dict
  find_merge_base(graph, sha1_a, sha1_b)                 → SHA1 | None
  visualize_dag(graph, head_sha1, refs)                  → ASCII string

核心格式:
  Blob:   "blob <size>\\0<content>"
  Tree:   "tree <size>\\0" + entries (每条: "<mode> <name>\\0<20-byte raw SHA1>")
  Commit: "commit <size>\\0tree <sha1>\\nparent <sha1>\\nauthor ...\\n\\n<msg>\\n"
"""

import hashlib
import os
import time
import zlib


# ═══════════════════════════════════════════════════════════════
# Node 1 — Blob 对象
# ═══════════════════════════════════════════════════════════════


def sha1_file(file_path: str) -> str:
    """
    计算文件的 Git blob SHA1 (不写入 .git/objects)。

    等价于: git hash-object <file>

    流程:
      1. 读文件内容 (二进制模式)
      2. 构造 header: b"blob <byte_count>\\0"
      3. SHA1(header + content) → 40位hex
    """
    with open(file_path, "rb") as f:
        content = f.read()

    header = f"blob {len(content)}\0".encode("utf-8")
    store = header + content
    return hashlib.sha1(store).hexdigest()


def read_blob(repo_path: str, sha1_hex: str) -> bytes:
    """
    从 .git/objects 读取 blob 对象, 返回原始内容。

    等价于: git cat-file -p <sha1>

    参数:
        repo_path: 仓库根路径 (包含 .git/ 的那个目录), 或 .git 目录本身
        sha1_hex:  40位hex SHA1

    流程:
      1. 定位: <repo_path>/.git/objects/<sha1[:2]>/<sha1[2:]> (优先)
         或: <repo_path>/objects/<sha1[:2]>/<sha1[2:]> (fallback)
      2. 读取 + zlib.decompress()
      3. 找第一个 \\x00 → 剥离头部
      4. 返回原始内容
    """
    import os as _os

    # 先尝试 repo_root/.git/objects/... (仓库根路径)
    obj_path = _os.path.join(repo_path, ".git", "objects",
                              sha1_hex[:2], sha1_hex[2:])

    # fallback: repo_path 本身就是 .git 目录
    if not _os.path.exists(obj_path):
        obj_path = _os.path.join(repo_path, "objects",
                                  sha1_hex[:2], sha1_hex[2:])

    if not _os.path.exists(obj_path):
        raise FileNotFoundError(f"blob not found: {obj_path}")

    with open(obj_path, "rb") as f:
        raw = zlib.decompress(f.read())

    null_pos = raw.index(b"\x00")
    return raw[null_pos + 1:]


# ═══════════════════════════════════════════════════════════════
# Node 2 — Tree 对象
# ═══════════════════════════════════════════════════════════════


def encode_tree_entry(mode: int, name: str, sha1_binary: bytes) -> bytes:
    """
    将一条 tree entry 编码为原始字节。

    entry 格式: b"<mode> <name>\\0<20-byte SHA1>"

    参数:
        mode: 权限位 (int, 如 100644)
        name: 文件名 (str)
        sha1_binary: 20字节的二进制SHA1 (bytes, 不是 hex!)
    返回:
        entry 的原始字节
    """
    if len(sha1_binary) != 20:
        raise ValueError(
            f"SHA1 必须是 20 字节二进制, 实际 {len(sha1_binary)} 字节"
        )

    # mode(ASCII) + 空格 + name(UTF-8) + null byte
    prefix = f"{mode} {name}\0".encode("utf-8")

    return prefix + sha1_binary


def build_tree(entries: list, repo_path: str = ".git") -> str:
    """
    从 entries 列表创建 tree 对象，写入 .git/objects，返回 40位hex SHA1。

    entries: [(mode, name, sha1_hex), ...]
      例: [(100644, "README.md", "95d09f2b..."), ...]
      mode=40000 表示子 tree (子目录)

    等价于: git mktree

    流程:
      1. 按 name 字典序排序 entries (必须! 否则 SHA1 与 git 不一致)
      2. 编码每条 entry → body bytes
      3. 构造 header: b"tree <len(body)>\\0"
      4. SHA1(header + body) → 40位hex
      5. zlib.compress(header + body) → 写入 .git/objects/xx/xxx...
    """
    # Step 1: 按文件名排序 (Git 硬要求)
    sorted_entries = sorted(entries, key=lambda e: e[1])

    # Step 2: 编码每条 entry
    encoded = []
    for mode, name, sha1_hex in sorted_entries:
        sha1_binary = bytes.fromhex(sha1_hex)
        entry_bytes = encode_tree_entry(mode, name, sha1_binary)
        encoded.append(entry_bytes)

    # Step 3: 拼接 body
    body = b"".join(encoded)

    # Step 4: 构造 header
    header = f"tree {len(body)}\0".encode("utf-8")

    # Step 5: 完整 store
    store = header + body

    # Step 6: SHA1
    sha1_hex = hashlib.sha1(store).hexdigest()

    # Step 7: zlib 压缩 + 写入磁盘
    compressed = zlib.compress(store)
    obj_dir = os.path.join(repo_path, "objects", sha1_hex[:2])
    obj_path = os.path.join(obj_dir, sha1_hex[2:])

    os.makedirs(obj_dir, exist_ok=True)
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(compressed)

    return sha1_hex


def read_tree(repo_path: str, sha1_hex: str) -> list:
    """
    从 .git/objects 读取 tree 对象，解析出所有 entries。

    返回: [(mode, name, sha1_hex), ...]
      例: [(100644, "README.md", "95d09f2b..."), (40000, "src", "7a8b9c0d...")]

    等价于: git ls-tree <sha1>

    流程:
      1. 定位对象文件: <repo>/objects/<sha1[:2]>/<sha1[2:]>
      2. 读取 + zlib.decompress()
      3. 找第一个 \\x00 → 剥离 "tree <size>\\0" header
      4. 逐条解析 body:
         - 找 \\x00 分隔 mode+name 和 SHA1
         - 找空格分隔 mode 和 name
         - 读 null byte 后 20 字节 → 二进制 SHA1 → hex
    """
    # Step 1: 定位对象文件
    obj_path = os.path.join(
        repo_path, "objects", sha1_hex[:2], sha1_hex[2:]
    )

    if not os.path.exists(obj_path):
        raise FileNotFoundError(
            f"tree object not found: {obj_path} (SHA1: {sha1_hex})"
        )

    # Step 2: 读取 + zlib 解压
    with open(obj_path, "rb") as f:
        compressed = f.read()

    raw = zlib.decompress(compressed)

    # Step 3: 剥离 "tree <size>\0" header
    null_pos = raw.index(b"\x00")
    body = raw[null_pos + 1:]

    # Step 4: 逐条解析 entries
    results = []
    pos = 0

    while pos < len(body):
        # 找 null byte: 分隔 mode+name 和 SHA1
        null_pos = body.index(b"\x00", pos)

        # mode + name 部分: b"100644 README.md"
        mode_name = body[pos:null_pos].decode("utf-8")

        # 找空格: 分隔 mode 和 name
        space_pos = mode_name.index(" ")
        mode = int(mode_name[:space_pos])
        name = mode_name[space_pos + 1:]

        # SHA1: null byte 后面的 20 字节
        sha1_binary = body[null_pos + 1:null_pos + 21]
        sha1_hex = sha1_binary.hex()

        results.append((mode, name, sha1_hex))

        # 移动到下一个 entry
        pos = null_pos + 21  # null(1) + SHA1(20)

    return results


def read_tree_recursive(repo_path: str, sha1_hex: str,
                        prefix: str = "") -> list:
    """
    递归解析整个 tree，返回所有文件的 (mode, path, sha1)。

    等价于: git ls-tree -r <sha1>

    参数:
        repo_path: .git 目录路径
        sha1_hex: tree SHA1
        prefix: 当前路径前缀 (内部递归用)
    返回:
        [(mode, full_path, sha1_hex), ...]
    """
    entries = read_tree(repo_path, sha1_hex)
    results = []

    for mode, name, sha1 in entries:
        path = f"{prefix}{name}"
        if mode == 40000:  # 子树 → 递归
            results.extend(
                read_tree_recursive(repo_path, sha1, path + "/")
            )
        else:
            results.append((mode, path, sha1))

    return results


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
    创建一个 commit 对象，写入 .git/objects，返回 SHA1。

    参数:
        repo_path: .git 目录路径
        tree_sha1: 根 tree 的 40位hex SHA1
        parent_sha1s: 父 commit 的 SHA1 列表 (空列表 = 初始 commit)
        message: 提交消息
        author_name: 作者名
        author_email: 作者邮箱

    返回: 40位hex SHA1

    等价于: git commit-tree <tree> -p <parent> -m "<message>"

    Commit 对象格式:
      commit <size>\0
      tree <sha1>\n
      parent <sha1>\n        ← 每个 parent 一行，初始 commit 无此行
      author <name> <<email>> <timestamp> <tz>\n
      committer <name> <<email>> <timestamp> <tz>\n
      \n
      <message>\n
    """
    now = int(time.time())
    tz = "+0800"

    # 构造 commit 内容 (不含 header)
    lines = [f"tree {tree_sha1}"]

    for p in parent_sha1s:
        lines.append(f"parent {p}")

    lines.append(f"author {author_name} <{author_email}> {now} {tz}")
    lines.append(f"committer {author_name} <{author_email}> {now} {tz}")
    lines.append("")  # 空行分隔 header 和 message
    lines.append(message)

    body = "\n".join(lines).encode("utf-8")

    # 加 header: "commit <size>\0"
    header = f"commit {len(body)}\0".encode("utf-8")
    store = header + body

    # SHA1
    sha1_hex = hashlib.sha1(store).hexdigest()

    # zlib 压缩 + 写入磁盘
    compressed = zlib.compress(store)
    obj_dir = os.path.join(repo_path, "objects", sha1_hex[:2])
    obj_path = os.path.join(obj_dir, sha1_hex[2:])

    os.makedirs(obj_dir, exist_ok=True)
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(compressed)

    return sha1_hex


def read_commit(repo_path: str, sha1_hex: str) -> dict:
    """
    从 .git/objects 读取 commit 对象，解析为字典。

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

    等价于: git cat-file -p <sha1>

    解析技巧:
      author 行: "author Terence <t@d.dev> 1749778200 +0800"
        → .rsplit(" ", 2) 拆出 ["author Terence <t@d.dev>", "1749778200", "+0800"]
        → .rfind("<") 拆出 name="Terence" email="t@d.dev"
    """
    # Step 1: 定位对象文件
    obj_path = os.path.join(repo_path, "objects", sha1_hex[:2], sha1_hex[2:])
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"commit not found: {obj_path}")

    # Step 2: 读取 + zlib 解压
    with open(obj_path, "rb") as f:
        raw = zlib.decompress(f.read())

    # Step 3: 跳过 header "commit <size>\0"
    null_pos = raw.index(b"\x00")
    body = raw[null_pos + 1:].decode("utf-8")

    lines = body.split("\n")

    result = {"parents": [], "sha1": sha1_hex}
    i = 0

    # Step 4: 解析 header 字段 (直到空行)
    while i < len(lines) and lines[i] != "":
        line = lines[i]

        if line.startswith("tree "):
            result["tree"] = line[5:]

        elif line.startswith("parent "):
            result["parents"].append(line[7:])

        elif line.startswith("author "):
            # 格式: "author Name <email> timestamp tz"
            parts = line[7:].rsplit(" ", 2)
            result["author_time"] = int(parts[1])
            result["author_tz"] = parts[2]
            name_email = parts[0]
            lt = name_email.rfind("<")
            result["author_name"] = name_email[:lt].strip()
            result["author_email"] = name_email[lt + 1:-1]

        elif line.startswith("committer "):
            # 格式: "committer Name <email> timestamp tz"
            parts = line[10:].rsplit(" ", 2)
            result["committer_time"] = int(parts[1])
            result["committer_tz"] = parts[2]
            name_email = parts[0]
            lt = name_email.rfind("<")
            result["committer_name"] = name_email[:lt].strip()
            result["committer_email"] = name_email[lt + 1:-1]

        i += 1

    # Step 5: 空行之后 = message
    if i + 1 < len(lines):
        result["message"] = "\n".join(lines[i + 1:]).rstrip("\n")

    return result


def find_merge_base(graph: dict, sha1_a: str, sha1_b: str):
    """
    找两个 commit 的最近共同祖先 (Lowest Common Ancestor)。

    算法: BFS 染色 (two-phase BFS)
    Phase 1 — 从 A 出发, BFS 遍历所有祖先, 标记到 colored set
    Phase 2 — 从 B 出发, BFS 遍历祖先, 第一个在 colored 中的就是 LCA

    参数:
        graph: {sha1: {"parents": [...], ...}, ...}
        sha1_a: 分支 A 的 tip
        sha1_b: 分支 B 的 tip
    返回:
        LCA 的 SHA1, 或 None

    等价于: git merge-base <sha1_a> <sha1_b>
    """
    if sha1_a not in graph or sha1_b not in graph:
        return None

    # Phase 1: 从 A 出发染色
    colored = set()
    queue = [sha1_a]
    while queue:
        current = queue.pop(0)
        if current in colored:
            continue
        colored.add(current)
        for p in graph[current].get("parents", []):
            if p not in colored:
                queue.append(p)

    # Phase 2: 从 B 出发找第一个染色节点
    queue = [sha1_b]
    visited = set()
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        if current in colored:
            return current  # 找到了!

        for p in graph[current].get("parents", []):
            if p not in visited:
                queue.append(p)

    return None  # 无共同祖先


def visualize_dag(graph: dict, head_sha1: str, refs: dict = None) -> str:
    """
    把 commit DAG 画成 ASCII 树形图。

    参数:
        graph: {sha1: {"parents": [...], "message": "..."}, ...}
        head_sha1: 从哪个 commit 开始画
        refs: {"main": sha1, "feature": sha1, ...}  可选

    返回:
        ASCII 多行字符串

    等价于: git log --graph --oneline (但更底层)
    """
    refs = refs or {}

    # 反向索引: sha1 → branch names
    sha1_to_refs = {}
    for name, s in refs.items():
        sha1_to_refs.setdefault(s, []).append(name)

    lines = []

    def _render(sha1: str, prefix: str, is_last: bool, visited: set):
        if sha1 in visited:
            return
        visited.add(sha1)

        commit = graph.get(sha1, {})

        # 分支标签
        tags = sha1_to_refs.get(sha1, [])
        tag_str = f" ({', '.join(tags)})" if tags else ""

        # 短 SHA1 + 消息
        short_sha1 = sha1[:7]
        msg = commit.get("message", "")[:50].replace("\n", " ")
        connector = "└──" if is_last else "├──"
        lines.append(f"{prefix}{connector} {short_sha1}{tag_str} {msg}")

        parents = commit.get("parents", [])
        for i, p in enumerate(parents):
            is_last_p = (i == len(parents) - 1)
            new_prefix = prefix + ("    " if is_last else "│   ")
            _render(p, new_prefix, is_last_p, visited)

    _render(head_sha1, "", True, set())
    return "\n".join(lines)


def load_dag(repo_path: str, start_sha1: str) -> dict:
    """
    从 start_sha1 出发, 沿 parent 指针 BFS 遍历, 加载全部历史到 dict。

    返回: {sha1: commit_dict, ...}
    """
    graph = {}
    queue = [start_sha1]

    while queue:
        sha1 = queue.pop(0)
        if sha1 in graph:
            continue
        commit = read_commit(repo_path, sha1)
        graph[sha1] = commit
        for p in commit["parents"]:
            if p not in graph:
                queue.append(p)

    return graph


# ═══════════════════════════════════════════════════════════════
# ── 演示 / 自测 ──
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile

    print("=" * 60)
    print("  Node 2 + Node 3 Solution Demo")
    print("=" * 60)

    # ── Node 2: encode_tree_entry ──
    print("\n── Node 2: encode_tree_entry ──")
    raw_sha1 = bytes.fromhex("95d09f2b10159347eece71399a7e2e907ea3df4f")
    entry = encode_tree_entry(100644, "README.md", raw_sha1)
    print(f"  mode=100644, name='README.md'")
    print(f"  编码结果: {entry!r}")
    print(f"  字节数:   {len(entry)} (mode=6 + sp=1 + name=9 + null=1 + SHA1=20)")
    print()

    # ── Node 2: build_tree + read_tree ──
    print("── Node 2: build_tree + read_tree 演示 ──")

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = os.path.join(tmpdir, ".git")
        os.makedirs(os.path.join(repo, "objects"))

        # 写几个 blob
        def _write_blob(content: bytes) -> str:
            hdr = f"blob {len(content)}\0".encode()
            st = hdr + content
            s = hashlib.sha1(st).hexdigest()
            d = os.path.join(repo, "objects", s[:2])
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, s[2:]), "wb") as f:
                f.write(zlib.compress(st))
            return s

        blob_rm = _write_blob(b"# My Project\n")
        blob_mp = _write_blob(b"print('hello')\n")

        entries = [
            (100644, "main.py", blob_mp),
            (100644, "README.md", blob_rm),
        ]
        tree_sha1 = build_tree(entries, repo_path=repo)
        print(f"  Tree SHA1: {tree_sha1}")

        recovered = read_tree(repo, tree_sha1)
        for mode, name, sha1 in recovered:
            type_str = "tree" if mode == 40000 else "blob"
            print(f"  {mode:06o} {type_str} {sha1[:12]}...\t{name}")

        names = [n for _, n, _ in recovered]
        print(f"  排序验证: {names} → "
              f"{'✅' if names == sorted(names) else '❌'}")

        # ── Node 2: 嵌套 tree ──
        print("\n── Node 2: 嵌套 tree 演示 ──")
        blob_sub = _write_blob(b"def util(): pass\n")
        sub_tree = build_tree([(100644, "utils.py", blob_sub)], repo_path=repo)
        root_entries = [
            (100644, "README.md", blob_rm),
            (40000, "src", sub_tree),
        ]
        root_sha1 = build_tree(root_entries, repo_path=repo)
        print(f"  根 tree: {root_sha1}")
        all_files = read_tree_recursive(repo, root_sha1)
        for mode, path, sha1 in all_files:
            print(f"  {mode:06o} blob {sha1[:12]}...\t{path}")

        # ── Node 3: create_commit ──
        print("\n── Node 3: create_commit 演示 ──")

        init_commit = create_commit(
            repo, tree_sha1, [],
            "Initial commit: add README and main.py"
        )
        print(f"  初始 commit: {init_commit}")
        print(f"  短 SHA1:     {init_commit[:7]}")

        # 第二个 commit
        blob_rm2 = _write_blob(b"# My Project v2\n")
        tree2 = build_tree(
            [(100644, "README.md", blob_rm2),
             (100644, "main.py", blob_mp)],
            repo_path=repo,
        )
        commit2 = create_commit(
            repo, tree2, [init_commit],
            "Update README to v2"
        )
        print(f"  第二个 commit: {commit2[:7]} (parent: {init_commit[:7]})")

        # 分支 commit
        blob_feat = _write_blob(b"# feature WIP\n")
        tree_feat = build_tree(
            [(100644, "FEATURE.md", blob_feat)],
            repo_path=repo,
        )
        feat_commit = create_commit(
            repo, tree_feat, [init_commit],
            "Start feature work"
        )
        print(f"  feature 分支: {feat_commit[:7]} (parent: {init_commit[:7]})")

        # ── Node 3: read_commit ──
        print("\n── Node 3: read_commit 演示 ──")
        info = read_commit(repo, init_commit)
        print(f"  tree:      {info['tree'][:12]}...")
        print(f"  parents:   {info['parents']}")
        print(f"  author:    {info['author_name']} <{info['author_email']}>")
        print(f"  timestamp: {info['author_time']}")
        print(f"  message:   {info['message']}")

        # ── Node 3: DAG ──
        print("\n── Node 3: load_dag + find_merge_base ──")
        graph = load_dag(repo, commit2)
        # 手动加入 feature 分支 commit
        graph[feat_commit] = read_commit(repo, feat_commit)

        print(f"  DAG 节点数: {len(graph)}")
        lca = find_merge_base(graph, commit2, feat_commit)
        print(f"  merge_base(main, feature) = {lca[:7] if lca else None}")
        print(f"  验证: {'✅' if lca == init_commit else '❌'} (应为 {init_commit[:7]})")

        # ── Node 3: visualize_dag ──
        print("\n── Node 3: visualize_dag 演示 ──")
        refs = {
            "main": commit2,
            "feature": feat_commit,
        }
        ascii_art = visualize_dag(graph, commit2, refs)
        print(ascii_art)

    print()
    print("── 全部演示完毕 ──")
