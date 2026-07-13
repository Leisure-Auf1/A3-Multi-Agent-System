# Node 3: Commit 链条与有向无环图 (DAG) 拓扑演化

> **目标**: 用 Python 亲手创建一个 commit 对象（带 parent 指针），写进 `.git/objects/`，然后在内存里构建整个提交历史的 DAG，实现合并基查找和 ASCII 可视化。看完这节，`git log`、`git branch`、`git merge` 对你来说都只是指针游戏。

---

## 0. 快速回顾：Node 1 + Node 2 我们搞懂了什么

```
Blob (Node 1):  文件内容 → blob <size>\0<content> → SHA1 → zlib → objects/
Tree (Node 2):  文件名 + blob_SHA1 → tree <size>\0<entries> → SHA1 → zlib → objects/

现在你有一个 tree SHA1，代表项目在某一个时刻的完整快照。
但问题是: 这个快照是谁创建的？什么时候？为什么？以及，上一个快照是哪个？
```

**答案：在 commit 对象里。** 一个 commit 把 tree、作者、时间、消息、以及**父 commit** 全部绑在一起。

---

## 1. Commit 对象：Git 历史的原子单位

### 本节概念 (3个)
1. **Commit 对象**: 一个不可变的快照 + 元数据 + 父指针
2. **Commit 字段**: tree, parent(s), author, committer, message
3. **内容寻址的链**: commit 的 SHA1 由内容决定 → 改任何字段 = 新 SHA1

---

### Commit 对象的原始字节格式

```
commit <size>\0tree <tree_sha1>
parent <parent_sha1>
author <name> <<email>> <timestamp> <timezone>
committer <name> <<email>> <timestamp> <timezone>

<message>
```

看一下真实的 git commit 对象：

```bash
$ git cat-file -p HEAD
tree 7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b
parent a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0
author Linus Torvalds <torvalds@linux-foundation.org> 1749778200 -0700
committer Linus Torvalds <torvalds@linux-foundation.org> 1749778200 -0700

Initial commit: add README and main.py
```

```
commit 对象的字节结构:

  commit 217\0                                    ← header
  tree 7a8b9c0d...\n                              ← 指向根 tree
  parent a1b2c3d4...\n                            ← 指向上一个 commit
  author Terence <terence@demo.dev> 1749778200 +0800\n
  committer Terence <terence@demo.dev> 1749778200 +0800\n
  \n                                              ← 空行分隔 header 和 message
  Initial commit: add README\n                    ← 提交消息
```

> 💡 **关键洞察**: 每个 commit 都包含 `tree` 和 `parent` 两个指针。tree 指向"这个版本的全部文件"，parent 指向"上一个版本"。——这是单向链表！多个 parent 就是 DAG。

---

## 2. Commit 如何形成链条：从线性到分支

### 本节概念 (3个)
4. **线性历史**: 每个 commit 一个 parent → 单向链表
5. **分支**: 多个 commit 指向同一个 parent → DAG 分叉
6. **合并**: 一个 commit 有两个 parent → DAG 合流

---

```
线性历史 (单分支):
  A ← B ← C ← D (main)
  每个箭头是 "parent" 指针

分支:
       B ← C (feature)
      /
  A ← D ← E (main)
  
合并 (merge commit):
       B ← C ──┐
      /         \
  A ← D ← E ← F (main, merge commit, 两个 parent: E 和 C)
```

**分支的本质**: branch 只是一个指向 commit 的**指针**。`refs/heads/main` 是一个文件，里面只有一行——当前 commit 的 SHA1。

```bash
$ cat .git/refs/heads/main
a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0

$ git update-ref refs/heads/main <new_sha1>   # 这就是 git commit 做的事
```

> 💡 **关键洞察**: `git branch feature` 不是"复制"任何东西。它只是在 `.git/refs/heads/feature` 里写了一个 SHA1。`git checkout feature` 就是把 HEAD 指向这个文件。**分支是免费的**。

---

## 3. 🔧 动手：Python 实现 create_commit

### 本节概念 (2个)
7. **Commit 构造**: 拼接 header + 字段 + message → SHA1 → zlib → .git/objects
8. **时间戳格式**: Unix timestamp + timezone offset

---

```python
import hashlib
import zlib
import os
import time


def create_commit(
    repo_path: str,
    tree_sha1: str,
    parent_sha1s: list[str],
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
    """
    now = int(time.time())
    tz = "+0800"

    # 构造 commit 内容 (未加 header)
    lines = [f"tree {tree_sha1}"]

    for p in parent_sha1s:
        lines.append(f"parent {p}")

    lines.append(f"author {author_name} <{author_email}> {now} {tz}")
    lines.append(f"committer {author_name} <{author_email}> {now} {tz}")
    lines.append("")  # 空行
    lines.append(message)

    body = "\n".join(lines).encode("utf-8")

    # 加 header: "commit <size>\0"
    header = f"commit {len(body)}\0".encode("utf-8")
    store = header + body

    # SHA1
    sha1_hex = hashlib.sha1(store).hexdigest()

    # zlib 压缩 + 写入
    compressed = zlib.compress(store)
    obj_dir = os.path.join(repo_path, "objects", sha1_hex[:2])
    obj_path = os.path.join(obj_dir, sha1_hex[2:])

    os.makedirs(obj_dir, exist_ok=True)
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(compressed)

    return sha1_hex
```

**关键注意**: commit 的 `\n` 必须是 Unix 换行符 (`\n`，不是 `\r\n`)。message 最后**不要**多余的空行（除非你有意为之）。

### 和真实 git 对比

```bash
$ git commit-tree <tree_sha1> -p <parent> -m "Initial commit"
a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0  ← 你的 Python 输出应该一致
```

---

## 4. 🔧 读取 commit 对象

```python
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
    """
    obj_path = os.path.join(repo_path, "objects", sha1_hex[:2], sha1_hex[2:])
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"commit not found: {obj_path}")

    with open(obj_path, "rb") as f:
        raw = zlib.decompress(f.read())

    # 跳过 header "commit <size>\0"
    null_pos = raw.index(b"\x00")
    body = raw[null_pos + 1:].decode("utf-8")

    lines = body.split("\n")

    result = {"parents": [], "sha1": sha1_hex}
    i = 0

    # 解析 header 字段
    while i < len(lines) and lines[i] != "":
        line = lines[i]
        if line.startswith("tree "):
            result["tree"] = line[5:]
        elif line.startswith("parent "):
            result["parents"].append(line[7:])
        elif line.startswith("author "):
            # author Name <email> timestamp tz
            parts = line[7:].rsplit(" ", 2)
            result["author_time"] = int(parts[1])
            result["author_tz"] = parts[2]
            name_email = parts[0]

```python
# 🔍 对应位置的核心代码示意
# 详见下方完整实现
```

            # 提取 name 和 email
            lt = name_email.rfind("<")
            result["author_name"] = name_email[:lt].strip()
            result["author_email"] = name_email[lt+1:-1]
        elif line.startswith("committer "):
            parts = line[10:].rsplit(" ", 2)
            result["committer_time"] = int(parts[1])
            result["committer_tz"] = parts[2]
            name_email = parts[0]
            lt = name_email.rfind("<")
            result["committer_name"] = name_email[:lt].strip()
            result["committer_email"] = name_email[lt+1:-1]
        i += 1

    # message: 空行之后的所有内容
    if i + 1 < len(lines):
        result["message"] = "\n".join(lines[i+1:]).rstrip("\n")

    return result
```

---

## 5. DAG 在内存里：用 dict 表示整条历史

### 本节概念 (3个)
9. **Commit DAG**: dict {sha1 → {tree, parents, message}}
10. **遍历历史**: BFS/DFS 沿 parent 指针走
11. **根 commit**: parent 列表为空的 commit

---

```python
# 在内存里构建完整的 commit DAG
commit_graph = {}  # {sha1_hex: read_commit(...)}

def load_dag(repo_path: str, start_sha1: str) -> dict:
    """
    从 start_sha1 开始，沿 parent 指针遍历，加载整条历史到 dict。

    返回: {sha1: commit_dict, ...}
    """
    graph = {}
    queue = [start_sha1]

    while queue:
        sha1 = queue.pop(0)
        if sha1 in graph:
            continue

        commit = read_commit(repo_path, sha1)  # ← 用上面的 read_commit
        graph[sha1] = commit

        for p in commit["parents"]:
            if p not in graph:
                queue.append(p)

    return graph
```

---

## 6. 🔧 找合并基 (Merge Base / LCA)

### 本节概念 (3个)
12. **合并基 (Merge Base)**: 两个分支的共同祖先
13. **BFS 染色算法**: 从一个分支涂色，另一个分支 BFS 找第一个有色节点
14. **`git merge-base`**: 就是做这个

---

```python
def find_merge_base(graph: dict, sha1_a: str, sha1_b: str) -> str | None:
    """
    找两个 commit 的最近共同祖先 (LCA)。

    算法: BFS 染色
    1. 从 sha1_a 出发，BFS 遍历所有祖先，标记为 "visited from A"
    2. 从 sha1_b 出发，BFS 遍历祖先，第一个在步骤1中标记的节点就是 LCA

    返回: LCA 的 SHA1，或 None (无共同祖先)
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
            return current  # ← 找到了!

        for p in graph[current].get("parents", []):
            if p not in visited:
                queue.append(p)

    return None  # 无共同祖先
```

```
可视化示例:

       B ← C (feature)
      /     \
  A ← D ← E ← F (main)

  merge_base(C, E) = A   ← A 是两者最近的共同祖先
  merge_base(C, F) = C   ← C 是 F 的祖先之一 (F 有两个 parent: E 和 C)
  merge_base(C, D) = A   ← 追溯到 A

  git merge-base feature main → A
```

---

## 7. 🔧 ASCII 可视化 DAG

### 本节概念 (2个)
14. **DAG 可视化**: 把 dict 转成 `git log --graph` 风格的 ASCII
15. **拓扑排序**: 按时间/拓扑序排列节点

---

```python
def visualize_dag(graph: dict, head_sha1: str, refs: dict = None) -> str:
    """
    把 commit DAG 画成 ASCII 图。

    graph: {sha1: {"parents": [...], "message": "..."}}
    head_sha1: 从哪个 commit 开始画
    refs: {"main": sha1, "feature": sha1, ...}  可选，标注分支名

    返回: ASCII 字符串
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
        msg = commit.get("message", "")[:50]
        connector = "└──" if is_last else "├──"
        lines.append(f"{prefix}{connector} {short_sha1}{tag_str} {msg}")

        parents = commit.get("parents", [])
        for i, p in enumerate(parents):
            is_last_p = (i == len(parents) - 1)
            if len(parents) > 1:
                new_prefix = prefix + ("    " if is_last else "│   ")
            else:
                new_prefix = prefix + ("    " if is_last else "│   ")
            _render(p, new_prefix, is_last_p, visited)

    _render(head_sha1, "", True, set())
    return "\n".join(lines)
```

```
示例输出:

└── a1b2c3d (main, HEAD) Merge feature into main
    └── e5f6a7b Update README
        ├── c9d0e1f (feature) Add new feature
        │   └── a1b2c3d Initial commit
        └── b3c4d5e Fix bug in main
            └── a1b2c3d Initial commit
```

---

## 8. 模拟整个 Git 工作流

现在你已经有了所有积木块，可以在 Python 里模拟一个完整的 Git 工作流：

```python
def simulate_git_workflow(repo_path: str):
    """
    纯 Python 模拟: init → add → commit → branch → merge
    """
    os.makedirs(os.path.join(repo_path, "objects"), exist_ok=True)
    os.makedirs(os.path.join(repo_path, "refs", "heads"), exist_ok=True)

    # Step 1: 写文件 → blob
    # (沿用 Node 1 的 hash_object)
    blob_readme = hash_object(b"# My Project\n", repo_path)
    blob_main = hash_object(b"print('hello')\n", repo_path)

    # Step 2: 创建 tree
    entries = [
        (100644, "README.md", blob_readme),
        (100644, "main.py", blob_main),
    ]
    tree_sha1 = build_tree(entries, repo_path)  # Node 2

    # Step 3: 创建初始 commit
    init_commit = create_commit(repo_path, tree_sha1, [],
                                "Initial commit", "Student")

    # Step 4: 更新分支指针
    ref_path = os.path.join(repo_path, "refs", "heads", "main")
    with open(ref_path, "w") as f:
        f.write(init_commit + "\n")

    print(f"✅ 初始 commit: {init_commit[:7]}")
    print(f"✅ 分支 main → {init_commit[:7]}")

    # Step 5: 修改文件，创建第二个 commit
    blob_readme_v2 = hash_object(b"# My Project v2\n", repo_path)
    entries_v2 = [
        (100644, "README.md", blob_readme_v2),
        (100644, "main.py", blob_main),
    ]
    tree_v2 = build_tree(entries_v2, repo_path)
    commit_v2 = create_commit(repo_path, tree_v2, [init_commit],
                               "Update README", "Student")

    # 移动 main 分支指针
    with open(ref_path, "w") as f:
        f.write(commit_v2 + "\n")

    print(f"✅ 第二个 commit: {commit_v2[:7]}")
    print(f"✅ 分支 main → {commit_v2[:7]}")

    # 展示历史
    graph = load_dag(repo_path, commit_v2)
    print("\n── DAG 可视化 ──")
    print(visualize_dag(graph, commit_v2, {"main": commit_v2}))
```

---

## 9. 综合拓扑：blob → tree → commit → refs/heads → HEAD

```
                    HEAD
                     │
                     ▼
              refs/heads/main          ← 一个文本文件, 内容是一个 SHA1
                     │
                     ▼
         ┌─── commit a1b2c3d4 ───┐
         │  tree:    7a8b9c0d    │──────┐
         │  parent:  (none)      │      │
         │  author:  Student     │      │
         │  message: Init        │      │
         └───────────────────────┘      │
                                        ▼
                              ┌─── tree 7a8b9c0d ─────┐
                              │  100644 README.md      │──→ blob 95d09f2b
                              │  100644 main.py        │──→ blob e69b6f2a
                              │  40000  src/           │──→ tree ffee9933
                              └────────────────────────┘        │
                                                                ▼
                                                    ┌─── tree ffee9933 ──┐
                                                    │  100644 utils.py   │──→ blob aabbccdd
                                                    └────────────────────┘

  blob 95d09f2b:  blob 14\0# My Project\n
  blob e69b6f2a:  blob 15\0print('hello')\n
  blob aabbccdd:  blob 18\0def util(): pass\n

  每一个对象都在 .git/objects/ 里, 用 zlib 压缩存储。
```

**整个 Git 数据库的本质 = 一个以 SHA1 为键的键值存储，值是带类型标签的 zlib 压缩数据。**

---

## 9b. ❌ vs ✅ 对比：`git log --graph` 黑盒子 vs 你的 DAG 手动遍历

这是为你（底层逻辑控）准备的横评。把两个世界放在一起：

### ❌ 你讨厌的方式：`git log --graph --oneline`

```bash
$ git log --graph --oneline
* a1b2c3d (HEAD -> main) Merge feature into main
|\
| * c9d0e1f (feature) Add new feature
* | e5f6a7b Update README
|/
* d4c3b2a Initial commit
```

你看到了什么？一个漂亮的 ASCII 图。但你**不知道**：
- 这些 `*` 和 `|` 和 `\` 是怎么画出来的
- Git 内部是通过什么数据结构判断 C 和 E 分叉的
- `merge-base` 的算法是什么
- 如果图很复杂（几千个 commit），`git log --graph` 会不会漏节点
- 分支指针和 commit SHA1 之间的关系

**这就是黑魔法。** 敲命令，看图，但你对算法一无所知。

### ✅ 你写的方式：`load_dag()` + `find_merge_base()` + `visualize_dag()`

```python
# 1. 你自己从 .git/objects 加载整个 DAG
graph = {}
queue = [head_sha1]
while queue:
    sha1 = queue.pop(0)
    if sha1 in graph:
        continue
    commit = read_commit(repo_path, sha1)   # ← 你 Node 3 写的 read_commit
    graph[sha1] = commit
    for p in commit["parents"]:
        queue.append(p)

# 2. 你自己写 BFS 染色算法找 merge-base
#    Phase 1: 从 A 出发, 把祖先全染色
#    Phase 2: 从 B 出发 BFS, 第一个有色节点就是 LCA

# 3. 你自己递归渲染 ASCII 图
#    sha1[:7] + branch_tag + message[:50]
#    "├──" / "└──" + "│   " / "    " 缩进
```

### 核心差异

| 层面 | ❌ `git log --graph` | ✅ 你的手动遍历 |
|:-----|:---------------------|:----------------|
| 数据来源 | Git 内部 walker（你看不到） | 你从 `.git/objects/` 逐个 `zlib.decompress()` |
| 图结构 | Git C 代码维护的 `commit_graph` | 你写的 Python `dict`: `{sha1: {"parents": [...], ...}}` |
| 遍历算法 | Git 的 `revision.c` (5000+ 行 C) | 你的 `while queue:` BFS, ~15 行 |
| LCA 算法 | Git 的内部实现 | 你的 "BFS 染色" 两步算法 |
| ASCII 渲染 | `graph.c` 复杂状态机 | 你的 `_render()` 递归, ~20 行 |
| 分支本质 | 你不知道 `refs/heads/main` 是啥 | 你知道它就是一个**文本文件**, 里面一行 SHA1 |

### 你现在知道了什么

```bash
$ cat .git/refs/heads/main
3b18e512dba79e4c8300dd08aeb37f8e728b8dad
```

就这一行。`git log` 就是从这个 SHA1 出发，沿 `parent` 指针一路走回去。

**分支不是"复制代码"——它是 "SHA1 的别名"。** 你创建 100 个分支，Git 只在 `.git/refs/heads/` 下写了 100 个文本文件，每个 41 字节。

> 💡 **这就是你把 4 个函数写一遍的意义。** 你不再"相信 Git 能记录历史"——你**知道**它就是把 `tree` + `parent` + `author` + `message` 拼成一个文本，SHA1 后 zlib 压缩，扔进 `.git/objects/`。分支就是 `.git/refs/heads/` 下的一个 41 字节文本文件。

---

## 回顾：本节你搞懂了什么

| 序号 | 概念 | 一句话 |
|------|------|--------|
| 1 | Commit 对象 | tree + parent(s) + author + committer + message |
| 2 | Commit 字段 | `commit <size>\0` + 多行 key-value + 空行 + message |
| 3 | SHA1 不变性 | 改任何字段 = 新 SHA1 = 新 commit |
| 4 | 线性历史 | 每个 commit 一个 parent → 单向链表 |
| 5 | 分支 | `refs/heads/xxx` 文件里写一个 SHA1 |
| 6 | 合并 | 一个 commit 有两个 parent → DAG 合流 |
| 7 | create_commit | 拼接字段 → header → SHA1 → zlib → objects/ |

```python
# 🔍 对应位置的核心代码示意
# 详见下方完整实现
```

| 8 | 时间戳 | Unix timestamp + timezone offset (如 `+0800`) |
| 9 | Commit DAG | dict {sha1 → {tree, parents, message}} |
| 10 | BFS 遍历 | 沿 parent 指针走，构建/查询整个图 |
| 11 | 根 commit | parent 列表为空的初始提交 |
| 12 | Merge Base (LCA) | BFS 染色算法找最近共同祖先 |
| 13 | `git merge-base` | === `find_merge_base()` |
| 14 | DAG 可视化 | 递归渲染 parent 指针树 |
| 15 | 拓扑排序 | 按 parent 依赖关系排列节点 |
| 16 | Git 数据库本质 | SHA1 → zlib(type size\0content) 的 K-V 存储 |

### ❌ 现在你该扔掉的想法
- "commit 是某种特殊的、我看不懂的数据库记录"
- "`git log` 和 `git branch` 依赖某种黑魔法索引"
- "合并基是 Git 内部的一个神秘算法，我理解不了"

### ✅ 换成这些
- "commit 就是 `.git/objects` 里的一个文本记录，字段包括 tree、parent、author、message"
- "`git log` = 沿着 parent 指针遍历 commit 对象链"
- "`git merge-base` = BFS 染色，找一个被两个分支都访问过的节点"
- "分支 = `.git/refs/heads/xxx` 里的一个 SHA1，HEAD = `.git/HEAD` 指向当前分支"

---

> **三节总结**: 你现在完全理解了 Git 的物理存储层。
> - **Blob** = 文件内容 + hash
> - **Tree** = 文件名 + blob 指针 → 目录快照
> - **Commit** = tree + parent + 元数据 → 历史链
> - **Refs** = 指向 commit 的命名指针 → 分支和标签
>
> 每一层都是纯文本/二进制 + zlib 压缩。**没有魔法。只有数据结构。**

---

## 练习

### 练习 1: 实现 `create_commit`
在 `outputs/node-3-tests.py` 中实现：
- 接收 tree_sha1, parent_sha1s, message, author
- 按 commit 格式拼接字段 → SHA1 → zlib → 写入 .git/objects
- 返回 40位 hex SHA1

### 练习 2: 实现 `read_commit`
实现 `read_commit(repo_path, sha1_hex)` → dict:
- 读取 → zlib 解压 → 跳过 header → 解析字段
- 正确解析 parent 列表、author/committer 的时间戳和时区

### 练习 3 (挑战): 实现 `find_merge_base`
实现 `find_merge_base(graph, sha1_a, sha1_b)` → SHA1:
- BFS 染色算法，在两个 DAG 分支中找到最近共同祖先

### 练习 4 (挑战): 实现 `visualize_dag`
实现 `visualize_dag(graph, head_sha1)` → ASCII 字符串:
- 递归渲染，标注分支名，正确缩进

**运行验证**:
```bash
python outputs/node-3-tests.py
```
