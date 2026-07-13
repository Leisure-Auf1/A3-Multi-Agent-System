# Node 1: 内容寻址存储 — 从 ASCII 到 SHA1 到 zlib 到磁盘路径

> **目标**: 用 Python 手工仿真 `git hash-object -w` 的完整链路，
> 跟踪每一个字节从 `"hello world"` 经过 SHA1 哈希、zlib 压缩，
> 最终落到 `.git/objects/a0/42348497357a4e72c99a3c7e4d3c46b7a1a123` 的全过程。
>
> **原则**: 不讲命令，只讲字节变化。每一层变换都要看到输入→输出的物理数据。

---

## 第 1 节：Git 不存"文件"——它存 Blob

### 概念 1：Blob 是 Git 的原子存储单元

当你执行 `git add hello.txt`，Git **不存文件名**。它把文件名扔掉，只取**文件内容**，
包一层轻量头部，哈希，压缩，写到由哈希值决定的路径里。

```
你脑子里以为的:                      实际发生的:

  hello.txt ──► "hello world"        hello.txt ──► blob a042348497...
                   │                                    │
                   ▼                                    ▼
            存在"hello.txt"                   存在 .git/objects/a0/42348...
            这个名字下面                     (文件名=内容的哈希)
```

这叫**内容寻址**（content-addressable storage）：地址（文件名）是内容的密码学哈希。
相同内容 → 相同哈希 → 磁盘上只存一份。Git 的去重就是这么来的——十万个 `"hello world"`
在磁盘上只占一个 blob。

### 概念 2：`.git/objects/` 的物理布局

走进任意一个 Git 仓库：

```
.git/objects/
├── info/               ← 不用管
├── pack/               ← 后面会讲（打包后的对象）
├── a0/
│   └── 42348497357a4e72c99a3c7e4d3c46b7a1a123    ← 一个 blob 文件
├── 8d/
│   └── 0ace693f0a30da465ede515ac12a42d885999e    ← 另一个 blob 文件
├── ff/
│   └── ...
```

SHA1 十六进制串共 40 个字符。Git 把它切成两段：**前 2 字符 → 目录名**，**后 38 字符 → 文件名**。

```
SHA1:    3b18e512dba79e4c8300dd08aeb37f8e728b8dad
         ├─┤├──────────────────────────────────────┤
         2字符              38字符
         目录                文件名

路径:    .git/objects/a0/42348497357a4e72c99a3c7e4d3c46b7a1a123
```

**为什么这么切？** 文件系统在单个目录下放几百万个文件时，`readdir()` 会极慢，有些文件系统甚至有文件数上限。
切成 256 个桶（00~ff）后，每个目录平均只放 N/256 个文件，文件系统毫无压力。

### 概念 3：四种对象类型，一种存储模式

Git 有四种对象，全部用同一种方式存储（header + content → SHA1 → zlib → 磁盘）：

| 类型   | 存什么                           | 由什么命令创建         |
|--------|----------------------------------|------------------------|
| blob   | 文件内容（不含文件名）             | `git hash-object -w`   |
| tree   | 目录列表（模式+文件名+blob SHA1）  | `git write-tree`       |
| commit | 作者、提交信息、父提交、tree SHA1  | `git commit-tree`      |
| tag    | 附注标签元数据                    | `git tag -a`           |

本节只聚焦 **blob**——它是所有其他对象的基石。

---

## 第 2 节：SHA1 —— 算出来的哈希就是磁盘地址

### 概念 1：Git 哈希的是"头部+内容"，不是"内容"

这是全节最重要的一条规则。如果你只对文件内容做 SHA1，得到的是**错的哈希值**。
Git 在内容前面加了一个头部：

```
blob <字节长度>\0<原始内容>
```

以 `"hello world\n"`（含换行符，12 字节）为例：

```
┌─────────┬─────┬──┬──────────────────┐
│  b l o b│  1 2│\0│hello world\n     │
└─────────┴─────┴──┴──────────────────┘
  4 字节    2字节 1B      12 字节
            ↑           ↑
      十进制 ASCII    原始文件字节
      内容长度
```

送入 SHA1 的总输入：`"blob 12\0hello world\n"` = 20 字节。

**关键**：头部里的长度是**纯内容**的字节数（十进制 ASCII，没有前导零）。不是头部长度，不是总长度，就是纯内容。

### 概念 2：为什么需要这个头部？

没有头部，不同类型的对象如果内容碰巧一样，哈希就会碰撞：

```
空文件   → "blob 0\0"         → SHA1: e69de29bb2d1...
空目录树 → "tree 0\0"         → SHA1: 4b825dc642cb...
                              ↑ 不一样！因为头部里的类型不同
```

头部也是一种自校验。Git 读取对象时，重新计算 `"blob <N>\0" + content` 的哈希，
与文件名对比——对不上就说明对象损坏了。

### 概念 3：Python 手工计算 SHA1 —— 逐字节追踪

```python
import hashlib

content = b"hello world\n"             # 12 字节
header  = f"blob {len(content)}\0"     # "blob 12\0"
store   = header.encode() + content    # 8 + 12 = 20 字节
sha1    = hashlib.sha1(store).hexdigest()

print(sha1)
# → "3b18e512dba79e4c8300dd08aeb37f8e728b8dad"
```

把 `store` 的每一个字节拆开看：

```
字节偏移:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19
字符:      b  l  o  b     1  2 \0  h  e  l  l  o     w  o  r  l  d \n
Hex:       62 6c 6f 62 20 31 32 00 68 65 6c 6c 6f 20 77 6f 72 6c 64 0a
           ├─ 头部 ─────────────┤├─ 原始内容 ──────────────────────────┤
           "blob 12<NUL>"        "hello world\n"
```

**验证**：在你的终端跑 `echo -n 'blob 12\0hello world\n' | sha1sum`。
必须输出 `3b18e512dba79e4c8300dd08aeb37f8e728b8dad`。
如果不对，检查 `\0`——大多数 shell 会吞掉 NUL 字节。用 Python 验证最可靠。

---

## 第 3 节：zlib —— Git 的压缩层

### 概念 1：每个对象在存盘前都经过 zlib 压缩

Git **不把原始字节直接写到磁盘**。算出 SHA1 之后，Git 把同一份 `header + content` 送进 zlib 的 `compress()`：

```
"blob 12\0hello world\n"   ──►  zlib.compress()  ──►  压缩后的字节
      20 字节                                              ~30 字节
```

压缩后的输出才是真正写到 `.git/objects/a0/42348...` 的内容。

### 概念 2：解压已有对象

读回 blob 就是反向过程：

```
.git/objects/a0/42348...  ──►  zlib.decompress()  ──►  "blob 12\0hello world\n"
    (压缩后的 blob)                                      (头部 + 内容)
```

然后切掉头部（第一个 `\0` 之前的部分），拿到原始内容：

```python
import zlib

with open(".git/objects/a0/42348497357a4e72c99a3c7e4d3c46b7a1a123", "rb") as f:
    raw = zlib.decompress(f.read())
# raw == b"blob 12\x00hello world\n"

null_pos = raw.index(b"\x00")         # 找 NUL 分隔符
obj_type = raw[:null_pos]             # b"blob 12"
content  = raw[null_pos + 1:]         # b"hello world\n"
```

### 概念 3：完整写入管道（端到端数据流）

```
                         ┌─────────────────────────┐
 "hello world\n"         │  第1步: 构造头部         │
 12 字节                 │  f"blob {len}\0"        │
      │                  │  = "blob 12\0"          │
      ▼                  └───────────┬─────────────┘
 ┌──────────┐                        │
 │  原始内容 │◄───────────────────────┘
 └────┬─────┘
      │
      ▼
 ┌──────────────────────────────────────────────┐
 │  第2步: 拼接                                 │
 │  header + content = "blob 12\0hello world\n" │
 │  共 20 字节                                  │
 └──────────────────────┬───────────────────────┘
                        │
                        ▼
 ┌──────────────────────────────────────────────┐
 │  第3步: SHA1 哈希                            │
 │  sha1(20 字节) → a042348497357a4e72c99...    │
 │  40 个十六进制字符                            │
 └──────────────────────┬───────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
         ▼                             ▼
 ┌──────────────────┐    ┌──────────────────────────┐
 │  第4a步: zlib    │    │  第4b步: 构造路径        │
 │  compress(20B)   │    │  sha1[:2] + "/" +        │
 │  → ~30 字节      │    │  sha1[2:]                │
 │                  │    │  = "a0/4234849735..."    │
 └────────┬─────────┘    └────────────┬─────────────┘
          │                           │
          ▼                           ▼
 ┌──────────────────┐    ┌──────────────────────────┐
 │  第5步: 写磁盘   │    │  mkdir -p .git/objects/a0│
 │  将压缩数据写入  │    │  写入 .../a0/42348...    │
 │  上述路径        │    │                          │
 └──────────────────┘    └──────────────────────────┘
```

读取路径（反向）：

```
  .git/objects/a0/42348...
         │
         ▼
  ┌──────────────────┐
  │  zlib.decompress │
  └────────┬─────────┘
           │
           ▼
  ┌────────────────────────────────────────┐
  │  b"blob 12\x00hello world\n"          │
  │  split on \x00 → [b"blob 12", 内容]   │
  └────────────────────┬───────────────────┘
                       │
                       ▼
                 "hello world\n"
```

---

## 第 4 节：Blob 路径公式 —— SHA1 → 文件系统路径

### 概念 1：规则本身

```
已知:  sha1_hex = "3b18e512dba79e4c8300dd08aeb37f8e728b8dad"  (40字符)

路径:  .git/objects/{sha1_hex[0:2]}/{sha1_hex[2:40]}

结果:  .git/objects/a0/42348497357a4e72c99a3c7e4d3c46b7a1a123
       ├── 仓库根 ──┤├─┤├──────────── 38 字符 ──────────────┤
                      2字符
```

两行 Python：

```python
def blob_path(repo_root, sha1_hex):
    return f"{repo_root}/.git/objects/{sha1_hex[:2]}/{sha1_hex[2:]}"
```

### 概念 2：为什么是 2+38？文件系统的现实约束

| 方案                | 单目录文件数                  | 问题                                  |
|---------------------|-------------------------------|---------------------------------------|
| 平铺（全部40字符做文件名） | 数百万个文件挤在一个目录里      | `readdir()` 巨慢，有些 FS 有文件数上限 |
| 2+38（Git 所选）     | ~256 个子目录，每个 N/256 个文件 | 均衡——ext4、HFS+、NTFS 都无压力       |
| 4+36                | 65536 个子目录，每个几乎空着    | 目录太多，浪费 inode                   |

Git 的 2+38 分割是工程上的甜点。一个 10 万对象的仓库，每个目录平均 ~390 个文件——
任何文件系统都能轻松处理。

### 概念 3：通过 SHA1 读取任意 Blob

```python
import zlib
from pathlib import Path

def read_blob(repo_path: str, sha1_hex: str) -> bytes:
    """
    从 Git 仓库中读取一个 blob 对象，返回原始内容。

    Args:
        repo_path: 仓库根路径（包含 .git/ 的那个目录）
        sha1_hex:  40 字符的十六进制 SHA1

    Returns:
        blob 的原始内容（头部已剥离）
    """
    obj_path = Path(repo_path) / ".git" / "objects" / sha1_hex[:2] / sha1_hex[2:]
    raw = zlib.decompress(obj_path.read_bytes())
    # 在第一个 NUL 字节处切分头部和内容
    null_idx = raw.index(b"\x00")
    return raw[null_idx + 1:]
```

核心逻辑就 ~5 行。剩下全是错误处理。

---

## 第 5 节：完整仿真 —— 用 Python 从零实现 `git hash-object -w`

### 概念 1：完整写入器

每一步都不藏，黑白分明：

```python
#!/usr/bin/env python3
"""
手工仿真:  echo -n "hello world" | git hash-object -w --stdin

这个脚本用纯 Python 重现 Git 内部做的事:
  1. 构造头部     → "blob 11\0"
  2. 拼接         → "blob 11\0hello world"
  3. SHA1 哈希    → 95d09f2b10159347eece71399a7e2e907ea3df4f
  4. zlib 压缩    → 压缩后的字节
  5. 写入磁盘     → .git/objects/95/d09f2b10159347eece71399a7e2e907ea3df4f

不调用 git 命令。不 subprocess。纯 Python + 标准库。
"""
import hashlib
import zlib
import os
from pathlib import Path

# ── 输入 ───────────────────────────────────────────────
content = b"hello world"           # 11 字节（无换行）
repo_root = "/tmp/demo-repo"

# ── 第1步: 构造头部 ───────────────────────────────────
# 头部格式: "blob " + ASCII 十进制长度 + "\0"
header = f"blob {len(content)}\0".encode()
print(f"头部: {header!r}")          # → b'blob 11\x00'

# ── 第2步: 拼接头部 + 内容 ────────────────────────────
store = header + content
print(f"拼接 ({len(store)} 字节): {store!r}")
# → b'blob 11\x00hello world'  (共 19 字节)

# ── 第3步: SHA1 哈希 ──────────────────────────────────
sha1_hex = hashlib.sha1(store).hexdigest()
print(f"SHA1:  {sha1_hex}")
# → 95d09f2b10159347eece71399a7e2e907ea3df4f

# ── 第4步: zlib 压缩 ──────────────────────────────────
compressed = zlib.compress(store)
print(f"zlib:   {len(store)} 字节 → {len(compressed)} 字节 "
      f"(压缩率 {len(compressed)/len(store):.0%})")

# ── 第5步: 构造路径并写入 ──────────────────────────────
obj_dir = Path(repo_root) / ".git" / "objects" / sha1_hex[:2]
obj_dir.mkdir(parents=True, exist_ok=True)

obj_path = obj_dir / sha1_hex[2:]
obj_path.write_bytes(compressed)

print(f"已写入: {obj_path}")
print(f"验证:   git -C {repo_root} cat-file -p {sha1_hex}")
```

### 概念 2：与真实 Git 交叉验证

跑完上面的脚本后，用 Git 自身来验证：

```bash
# blob 应该在我们预测的路径上
$ ls -la /tmp/demo-repo/.git/objects/95/d09f2b10159347eece71399a7e2e907ea3df4f

# Git 能读回来
$ git -C /tmp/demo-repo cat-file -p 95d09f2b10159347eece71399a7e2e907ea3df4f
hello world

# Git 算出来的哈希跟我们的完全一致
$ echo -n "hello world" | git hash-object --stdin
95d09f2b10159347eece71399a7e2e907ea3df4f
```

哈希完全吻合——因为我们精确复现了 Git 内部做的每一件事。

### 概念 3：逐字节数据流总览

```
输入:                b"hello world"
                     │
                     │ len(content) = 11
                     ▼
头部:                b"blob 11\0"
                     │
                     │ header + content
                     ▼
拼接 (19字节):       b"blob 11\0hello world"
                     │
                     │ sha1()
                     ▼
SHA1 (40字符):       95d09f2b10159347eece71399a7e2e907ea3df4f
                     │
             ┌───────┴────────┐
             │                │
             ▼                ▼
     zlib.compress()   路径 = "95/d09f2b101593..."
             │                │
             ▼                │
     压缩后的字节 ◄───────────┘
             │
             ▼
磁盘:        .git/objects/95/d09f2b10159347eece71399a7e2e907ea3df4f
             │
             │ (反向: zlib.decompress → 在 \0 处切分)
             ▼
输出:        b"hello world"
```

**核心领悟**：总共只有 5 次变换。每一步都没有"魔法"。
每个字节都可以溯源。这就是你理解 Git 底层的基础——
接下来在 Node 2 中，我们会在此基础上理解 tree（目录）和 Merkle DAG。

---

## 速查表

```
┌─────────────────────────────────────────────────────────────────┐
│                    BLOB STORAGE 速查表                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  写入:                                                           │
│    header   = b"blob " + str(len(content)).encode() + b"\0"     │
│    store    = header + content                                   │
│    sha1     = hashlib.sha1(store).hexdigest()                    │
│    path     = f".git/objects/{sha1[:2]}/{sha1[2:]}"              │
│    write zlib.compress(store) to path                            │
│                                                                  │
│  读取:                                                           │
│    raw      = zlib.decompress(read_bytes(path))                   │
│    null_pos = raw.index(b"\x00")                                 │
│    content  = raw[null_pos + 1:]                                 │
│                                                                  │
│  头部格式:   "blob <十进制长度>\0"                                │
│              ↑                    ↑                              │
│         对象类型              NUL 分隔符                          │
│                                                                  │
│  路径公式:   sha1[:2]  + "/" + sha1[2:]                          │
│              (目录)            (文件名)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

*下一节: Node 2 — Tree（Git 如何存储目录结构、mode bits 和 Merkle DAG）*
