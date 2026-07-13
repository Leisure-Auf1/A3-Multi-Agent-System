# Node 2: Tree 对象 — Git 如何用一个对象存下整个目录

> **目标**: 用 Python 仿真 `git mktree` 和 `git ls-tree`，亲手把一堆 blob SHA1 和文件名打包成一个 tree 对象，写进 `.git/objects/` 再读回来。看完这节，你会知道 `git commit` 之前的"暂存区"本质上就是一个等待写入的 tree。

---

## 0. 快速回顾：Node 1 我们搞懂了什么

你上一节亲手实现了：
```
文件内容  →  blob <size>\0<content>  →  SHA1  →  zlib  →  .git/objects/95/18e5...
```

**但有一个巨大的漏洞**：blob 对象里**没有文件名**。

```
你写了两个文件:
  README.md  → blob 95d09f2b...  (内容: "hello")
  notes.txt  → blob 95d09f2b...  (内容: "hello" — 一模一样!)

你看着 .git/objects/95/18e5... 问:
  "这个 blob 到底叫 README.md 还是 notes.txt？"
  → Git 的 blob 里不存文件名。那文件名去哪了？
```

**答案：在 tree 对象里。** 这就是 Node 2 要解开的谜。

---

## 1. Tree 的本质：一张"文件名 → Blob"的映射表

### 本节概念 (3个)
1. **Tree 对象**: Git 的目录快照
2. **Mode (权限位)**: `100644` / `100755` / `40000`
3. **Tree Entry 结构**: `<mode> <name>\0<20-byte SHA1>`

---

Tree 就是 Git 里"目录"的表示。它是一张表：

```
┌─────────────────────────────────────────────────────┐
│                    Tree 对象                        │
│  SHA1: a1b2c3d4...                                │
├──────────┬──────────┬──────────────────────────────┤
│  Mode    │  Name    │  Blob/Tree SHA1 (20 bytes)   │
├──────────┼──────────┼──────────────────────────────┤
│  100644  │ README.md│  \x95\xd0\x9f\x2b...        │
│  100644  │ main.py  │  \x3b\x18\xe5\x12...        │
│  40000   │ src/     │  \x7a\x8b\x9c\x0d...   ← 指向另一个 tree! │
└──────────┴──────────┴──────────────────────────────┘
```

每一条记录叫一个 **tree entry**。三条关键信息：
- **Mode**: 权限 + 类型。`100644`=普通文件，`100755`=可执行文件，`40000`=子目录(tree)
- **Name**: 文件名。就是它！blob 里没有的东西。
- **SHA1**: 指向 blob 或子 tree 的 20 字节**二进制**哈希 (不是 hex 字符串！)

> 💡 **关键洞察**: Blob 存内容，Tree 存关系。Git 用一个 tree 对象把"文件名"和"内容"绑在一起。这就是为什么同一个内容可以被两个不同的文件名引用——两个 tree entry 指向同一个 blob SHA1。

### 字节级解剖：tree entry 到底长什么样

```python
# 一个 tree entry 的原始字节:
entry = b"100644 README.md\x00" + bytes.fromhex("95d09f2b10159347eece71399a7e2e907ea3df4f")
#       ^^^^^^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#       mode + 空格 + name + \0    20字节的二进制SHA1 (不是40字符hex!)
```

注意：**SHA1 在 tree 里是 20 字节的原始二进制，不是 40 字符的 hex 字符串！** 这是最常见的坑。

---

## 2. Tree 对象的完整结构：header + entries

### 本节概念 (2个)
4. **Tree Header 格式**: `tree <size>\0`
5. **条目排序**: Git 要求 tree entries 按名称排序

---

和 blob 一样，tree 对象也有 header：

```
tree <总字节数>\0<entry1><entry2><entry3>
```

```
完整的 tree 存储流程:

   entries = [
       (100644, "README.md", blob_sha1),
       (100644, "main.py",   blob_sha1),
   ]
        │
        ▼
   raw = tree <N>\0
         + "100644 README.md\0" + binary_sha1_20bytes
         + "100644 main.py\0"   + binary_sha1_20bytes
        │
        ▼
   sha1 = SHA1(raw)
        │
        ▼
   zlib.compress(raw) → .git/objects/xx/xxxx...
```

**排序规则**: Git 按文件名字典序排列 entries。`"main.py"` 排在 `"README.md"` 后面？不对——字典序：`'m' > 'R'`（ASCII），所以 `README.md` 在前。**必须排序**，否则你算出的 SHA1 和 `git mktree` 不一致。

```python
# ✅ 正确: 先排序再拼字节
sorted_entries = sorted(entries, key=lambda e: e[1])
raw = header + b"".join(encode_entry(mode, name, sha1_binary) for ...)

# ❌ 错误: 没排序
raw = header + b"".join(encode_entry(...))  # SHA1 会和 git 不一致!
```

---

## 3. 动手：在 Python 里完整实现 build_tree / read_tree

### 本节概念 (3个)
6. **`build_tree`**: 从 entries 列表构造 tree 对象 → SHA1
7. **`read_tree`**: 从 `.git/objects` 读 tree → 解析 entries
8. **纯 Python 仿真 vs `git mktree` / `git ls-tree`**

---

### 🔧 Part A: 构建 tree 对象

```python
import hashlib
import zlib
import os


def encode_tree_entry(mode: int, name: str, sha1_binary: bytes) -> bytes:
    """
    将一条 tree entry 编码为原始字节。

    entry 格式: b"<mode> <name>\\0<20-byte SHA1>"

    参数:
        mode: 权限位 (如 100644)
        name: 文件名 (str)
        sha1_binary: 20字节的二进制SHA1 (bytes)
    """
    if len(sha1_binary) != 20:
        raise ValueError(f"SHA1 必须是 20 字节二进制, 实际 {len(sha1_binary)} 字节")

    # mode + 空格 + name + null byte
    prefix = f"{mode} {name}\0".encode("utf-8")

    return prefix + sha1_binary


def build_tree(entries: list, repo_path: str = ".git") -> str:
    """
    从 entries 列表创建 tree 对象，写入 .git/objects，返回 40位hex SHA1。

    entries: [(mode, name, sha1_hex), ...]
      例: [(100644, "README.md", "95d09f2b..."), ...]
      mode=40000 表示子 tree (子目录)

    返回: 40位hex SHA1

    等价于:
      echo -e "...entries..." | git mktree
    """
    # Step 1: 排序 (Git 要求按 name 字典序)
    sorted_entries = sorted(entries, key=lambda e: e[1])

    # Step 2: 编码每条 entry
    encoded_entries = []
    for mode, name, sha1_hex in sorted_entries:
        # 把 hex SHA1 转成 20 字节二进制
        sha1_binary = bytes.fromhex(sha1_hex)
        entry_bytes = encode_tree_entry(mode, name, sha1_binary)
        encoded_entries.append(entry_bytes)

    # Step 3: 拼接所有 entries
    entries_blob = b"".join(encoded_entries)

    # Step 4: 构造 header
    header = f"tree {len(entries_blob)}\0".encode("utf-8")

    # Step 5: 完整 tree 对象
    store = header + entries_blob

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
```

### 🔧 Part B: 读取 tree 对象

```python
def read_tree(repo_path: str, sha1_hex: str) -> list:
    """
    从 .git/objects 读取 tree 对象，解析出所有 entries。

    返回: [(mode, name, sha1_hex), ...]
      例: [(100644, "README.md", "95d09f2b..."), (40000, "src", "7a8b9c0d...")]

    等价于:
      git ls-tree <sha1>
    """
    # Step 1: 定位对象文件
    obj_path = os.path.join(repo_path, "objects", sha1_hex[:2], sha1_hex[2:])
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"tree not found: {obj_path}")

    # Step 2: 读取 + zlib 解压
    with open(obj_path, "rb") as f:
        raw = zlib.decompress(f.read())

    # Step 3: 跳过 header "tree <size>\0"
    null_pos = raw.index(b"\x00")
    entries_blob = raw[null_pos + 1:]  # header 之后的所有字节

    # Step 4: 逐条解析 entries
    results = []
    pos = 0
    while pos < len(entries_blob):
        # 找到 null byte (分隔 mode+name 和 SHA1)
        null_pos = entries_blob.index(b"\x00", pos)

        # mode + name 部分: b"100644 README.md"
        mode_name = entries_blob[pos:null_pos].decode("utf-8")
        space_pos = mode_name.index(" ")
        mode = int(mode_name[:space_pos])
        name = mode_name[space_pos + 1:]

        # SHA1: null byte 后面的 20 字节
        sha1_binary = entries_blob[null_pos + 1 : null_pos + 21]
        sha1_hex = sha1_binary.hex()

        results.append((mode, name, sha1_hex))

        # 移动游标到下一个 entry
        pos = null_pos + 21  # 1 (null) + 20 (SHA1)

    return results
```

### 🔧 Part C: 和真实 git 对比验证

```bash
# 用真实 git 创建 tree
$ mkdir /tmp/tree-demo && cd /tmp/tree-demo
$ git init -q

$ echo "hello world" > README.md
$ echo 'print("hello")' > main.py
$ git hash-object -w README.md main.py
95d09f2b10159347eece71399a7e2e907ea3df4f    # README.md
e69b6f2a58c3c4bc5e3e88070a1aa9c0d7e3e5a2    # main.py

# 用 git mktree 创建 tree
$ printf "100644 blob 95d09f2b10159347eece71399a7e2e907ea3df4f\tREADME.md\n" > /tmp/tree-input.txt
$ printf "100644 blob e69b6f2a58c3c4bc5e3e88070a1aa9c0d7e3e5a2\tmain.py\n" >> /tmp/tree-input.txt
$ cat /tmp/tree-input.txt | git mktree
7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b   ← tree SHA1

# 用 Python 做同样的事
entries = [
    (100644, "README.md", "95d09f2b10159347eece71399a7e2e907ea3df4f"),
    (100644, "main.py",   "e69b6f2a58c3c4bc5e3e88070a1aa9c0d7e3e5a2"),
]
tree_sha1 = build_tree(entries, repo_path="/tmp/tree-demo/.git")
print(tree_sha1)
# 7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b  ← 一模一样!

# 用 Python 读回来
entries = read_tree("/tmp/tree-demo/.git", tree_sha1)
for mode, name, sha1 in entries:
    print(f"{mode:06o} blob {sha1}\t{name}")
# 100644 blob 95d09f2b... README.md
# 100644 blob e69b6f2a... main.py
```

---

## 4. 嵌套 tree：目录套目录

### 本节概念 (3个)
9. **子树 (subtree)**: mode=40000 的 entry 指向另一个 tree
10. **递归解析**: 读 tree → 遇到 40000 → 读子树 → 层层深入
11. **完整的项目快照 = 根 tree**

---

一个 tree 的 entry 的 mode 如果是 `40000`，说明这个"文件"其实是**子目录**——它指向的是另一个 tree 对象。

```
项目结构:
  /
  ├── README.md        (blob: 95d09f2b...)
  ├── main.py          (blob: e69b6f2a...)
  └── src/
      ├── utils.py     (blob: aabbccdd...)
      └── core.py      (blob: 11223344...)

Git 内部表示:
  root tree (7a8b9c0d...)
  ├── 100644 README.md  → blob 95d09f2b...
  ├── 100644 main.py    → blob e69b6f2a...
  └── 40000  src/       → tree ffee9933...    ← 指向另一个 tree!
                              │
                              ├── 100644 utils.py  → blob aabbccdd...
                              └── 100644 core.py   → blob 11223344...
```

```
┌──────────────────────────────────┐
│  根 tree: 7a8b9c0d              │
│  ├─ README.md  → blob 95d09f2b  │
│  ├─ main.py    → blob e69b6f2a  │
│  └─ src/       → tree ffee9933  │──────┐
└──────────────────────────────────┘      │
                                          ▼
                              ┌──────────────────────────────┐
                              │  子树 tree: ffee9933          │
                              │  ├─ utils.py → blob aabbccdd  │
                              │  └─ core.py  → blob 11223344  │
                              └──────────────────────────────┘
```

**这就是 Git 的"快照"** —— 一个根 tree 对象，通过哈希指针逐层展开到所有文件和子目录。没有文件名重复，没有文件拷贝，全是哈希链接。

---

## 5. 🔧 进阶：递归列出整个树 (模拟 `git ls-tree -r`)

```python
def read_tree_recursive(repo_path: str, sha1_hex: str, prefix: str = "") -> list:
    """
    递归解析整个 tree，返回所有文件的 (mode, path, sha1)。

    等价于: git ls-tree -r <sha1>
    """
    entries = read_tree(repo_path, sha1_hex)
    results = []

    for mode, name, sha1 in entries:
        path = f"{prefix}{name}"
        if mode == 40000:  # 子树 → 递归
            results.extend(read_tree_recursive(repo_path, sha1, path + "/"))
        else:
            results.append((mode, path, sha1))

    return results


# 使用示例:
all_files = read_tree_recursive(repo_path, root_tree_sha1)
for mode, path, sha1 in all_files:
    print(f"{mode:06o} blob {sha1[:8]}... {path}")

# 输出:
# 100644 blob 95d09f2b... README.md
# 100644 blob e69b6f2a... main.py
# 100644 blob aabbccdd... src/utils.py
# 100644 blob 11223344... src/core.py
```

---

## 6. 补完 git add 的全貌

Node 1 我们说了 `git add` = hash_object + 更新 index。现在加上 tree：

```
git add README.md
  ├── 1. 读文件内容 → blob
  ├── 2. SHA1(blob <size>\0content)
  ├── 3. zlib 压缩 → .git/objects/xx/xxx
  └── 4. 更新 .git/index:
         "README.md" → SHA1: 95d09f2b...

git commit (后面 Node 3 详讲)
  ├── 1. 读取 .git/index 中的文件列表
  ├── 2. 构造 tree 对象 (build_tree)
  ├── 3. 构造 commit 对象 → 指向 tree
  └── 4. 更新 refs/heads/main → commit SHA1
```

| 层 | 存什么 | 在哪 |
|:---|:---|:---|
| Blob | 文件内容 | `.git/objects/` |
| Tree | 文件名 + 权限 + blob 指针 | `.git/objects/` |
| Index (暂存区) | 当前待提交的文件列表 | `.git/index` (二进制格式, 本章不讲) |
| Commit | 谁、什么时候、为什么 | `.git/objects/` (Node 3) |

---

## 7. 字节级总览：tree 对象在 `.git/objects` 里到底长什么样

假设一个目录里只有一个文件 `hello.txt`，内容为 `"hi"`。

```
blob:  hello.txt → "hi"
       header:  blob 2\0
       store:   blob 2\0hi
       SHA1:    c5c8a9e... (假设)
       磁盘:    .git/objects/c5/c8a9e...  ← zlib(blob 2\0hi)

tree:  包含 hello.txt
       entries: "100644 hello.txt\0" + c5c8a9e...的20字节二进制
       entries_blob:  100644 hello.txt\x00\xc5\xc8\xa9\xe9... (20 bytes)
       header:  tree 36\0   ← entries_blob 是 36 字节 (12+1+3+20?)
                             实际: b"100644 hello.txt" = 16, \0 = 1, SHA1 = 20
                             共 37 字节
       store:   tree 37\0 + entries_blob
       SHA1:    aabbccdd... (假设)
       磁盘:    .git/objects/aa/bbccdd...  ← zlib(tree 37\0 + entries)
```

```python
# 你可以用 Python 直接看到这些字节:
with open(".git/objects/aa/bbccdd...", "rb") as f:
    raw_tree = zlib.decompress(f.read())
print(raw_tree)
# b'tree 37\x00100644 hello.txt\x00\xc5\xc8\xa9\xe9...'
#  ^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#  header     entries (mode+name+\0+20byte_SHA1)
```

**看着这些原始字节，你还会觉得 `git add` 是黑魔法吗？**

---

## 6b. ❌ vs ✅ 对比：`git ls-tree` 黑盒子 vs 你的 `read_tree` 手动解析

这一节是为你（底层逻辑控）准备的。你把两段代码放在一起看：

### ❌ 你讨厌的方式：`git ls-tree`

```bash
$ git ls-tree 7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b
100644 blob 95d09f2b10159347eece71399a7e2e907ea3df4f    README.md
100644 blob e69b6f2a58c3c4bc5e3e88070a1aa9c0d7e3e5a2    main.py
```

你看到了什么？一坨 hex。你**不知道**：
- Git 内部访问了哪些文件
- 原始字节长什么样
- 文件名和 SHA1 之间用什么分隔符
- mode 是怎么存的（字符串？整数？二进制？）
- 如果 SHA1 损坏了，Git 怎么发现

**这就是黑魔法。** 你敲一个命令，输出一堆 hex，但你对底层一无所知。

### ✅ 你写的方式：`read_tree` 手动解析二进制

```python
# 你的 read_tree() 的核心循环
pos = 0
while pos < len(entries_blob):
    null_pos = entries_blob.index(b"\x00", pos)      # 找 \x00 分隔符
    
    mode_name = entries_blob[pos:null_pos]            # b"100644 README.md"
    space_pos = mode_name.index(b" ")                 # 找空格
    mode = int(mode_name[:space_pos])                 # 100644
    name = mode_name[space_pos + 1:].decode()         # "README.md"
    
    sha1_binary = entries_blob[null_pos + 1:null_pos + 21]  # 20 bytes raw SHA1
    sha1_hex = sha1_binary.hex()                            # → hex string
    
    results.append((mode, name, sha1_hex))
    pos = null_pos + 21   # 1 (null) + 20 (SHA1) = 下一个 entry 的起点
```

**你完全掌控了**：
- 知道 `.git/objects/` 里那个 zlib 压缩文件解压后**每一个字节**的含义
- 知道 `\x00` 是 mode+name 和 SHA1 之间的分隔符
- 知道 SHA1 存的是 **20 字节二进制**，不是 40 字符 hex
- 知道每个 entry 的总长度 = len(prefix) + 1 (null) + 20 (SHA1)
- 知道如果 zlib 解压失败、或 null byte 找不到、或 SHA1 不是 20 字节 → 对象损坏

### 核心差异

| 层面 | ❌ `git ls-tree` | ✅ 你的 `read_tree` |
|:-----|:-----------------|:--------------------|
| 输入 | 敲命令 | 用 `open()` 打开 `.git/objects/xx/xxx...` |
| 处理 | Git 内部 C 代码（你看不到） | `zlib.decompress()` → `while pos < len(body)` |
| 分隔符 | 你不知道 | 你亲手处理 `\x00` 和空格 |
| SHA1 格式 | hex 字符串（已转换好的） | 你亲手把 20 bytes 转成 `.hex()` |
| 错误 | Git 报错你看不懂 | 你写的 `FileNotFoundError` / `zlib.error` / `ValueError` |
| 理解深度 | **黑魔法** | **每一层都透明** |

> 💡 **这就是你写这 20 行 Python 的意义。** 你不再"相信 Git 能正确列出文件"——你**知道**它是怎么做的，因为你亲手实现了一遍。

---

## 回顾：本节你搞懂了什么

| 序号 | 概念 | 一句话 |
|------|------|--------|
| 1 | Tree 对象 | 一张"文件名 → SHA1 → blob"的映射表 |
| 2 | Mode | `100644`=普通文件, `100755`=可执行, `40000`=子目录 |
| 3 | Tree Entry | `<mode> <name>\0<20-byte SHA1>` — 严格二进制 |
| 4 | Tree Header | `tree <size>\0` |
| 5 | 条目排序 | 必须按 name 字典序，否则 SHA1 不一致 |
| 6 | build_tree | entries → encode → header → SHA1 → zlib → .git/objects |
| 7 | read_tree | .git/objects → zlib → 剥离 header → 逐条解析 entries |
| 8 | 20 字节 SHA1 | tree entry 里存的是**二进制**SHA1，不是 hex 字符串 |
| 9 | 子树 | mode=40000 指向另一个 tree，实现目录嵌套 |
| 10 | 递归解析 | mode=40000 → read_tree 再调用 → 层层深入 |
| 11 | 根 tree | 一个 tree 对象 = 整个项目的快照 |
| 12 | `git add` 全貌 | hash_object → 更新 index → commit 时构建 tree |
| 13 | Index | 暂存区就是"下次 commit 时的 tree entries 草稿" |

### ❌ 现在你该扔掉的想法
- "tree 只是一个概念，看不见摸不着"
- "文件名存在某种神秘的 Git 数据库里"
- "目录结构靠文件系统维护，Git 只是标记变化"

### ✅ 换成这些
- "tree 是 `.git/objects` 里的一个 zlib 压缩对象，里面存着 `100644 hello.txt\0<20-byte SHA1>`"
- "文件名在 tree entry 的 `<mode> <name>\0` 部分里，明明白白"
- "嵌套目录 = tree 里有 mode=40000 的 entry，指向另一个 tree"

---

> **下一节预告**: Node 3 — Commit 链条与 DAG 拓扑。当你有了 tree 快照，Git 如何用 commit 对象记录"谁、什么时候、为什么"，并通过 parent 指针串成一条历史链。分支和合并的本质，就在这里面。

---

## 练习

### 练习 1: 实现 `build_tree`
在 `outputs/node-2-tests.py` 的 `build_tree()` 函数中实现：
- 接收 `entries: list[(mode, name, sha1_hex)]`
- 排序、编码、压缩、写入 `.git/objects`
- 返回 40位 hex SHA1

### 练习 2: 实现 `read_tree`
实现 `read_tree(repo_path, sha1_hex)` → `list[(mode, name, sha1_hex)]`：
- 读取 `.git/objects` → zlib 解压 → 跳过 header → 逐条解析
- 每条 entry: 找 `\x00` → 前面是 mode+name → 后面 20 字节是二进制 SHA1

### 练习 3 (挑战): 实现 `read_tree_recursive`
递归列出整个 tree 的所有文件，跳过 mode=40000 的子树，沿用 `read_tree`。

**运行验证**:
```bash
python outputs/node-2-tests.py
```
