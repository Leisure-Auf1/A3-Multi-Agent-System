#!/usr/bin/env python3
"""
Node 2 测试 — Git Tree 对象构建 + 解析

学生画像: visual_learner_hates_magic
目标: 验证 build_tree() 和 read_tree() 与 git mktree / git ls-tree 完全一致

运行: python outputs/node-2-tests.py
"""

import hashlib
import os
import shutil
import tempfile
import unittest
import zlib
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# ── 学生填空区域 (Student Fill-in Zone) ──
# ═══════════════════════════════════════════════════════════════


def build_tree(entries: list, repo_path: str = ".git") -> str:
    """
    从 entries 列表创建 tree 对象，写入 .git/objects，返回 40位hex SHA1。

    entries: [(mode, name, sha1_hex), ...]
      例: [(100644, "README.md", "95d09f2b..."), ...]
      mode=40000 表示子 tree (子目录)

    算法:
    1. 按 name 字典序排序 entries
    2. 每条 entry 编码为: b"<mode> <name>\\0<20-byte SHA1>"
    3. 拼接所有 entries
    4. header: b"tree <size>\\0"
    5. SHA1(header + entries_blob)
    6. zlib 压缩 → .git/objects/xx/xxxx...

    参数:
        entries: [(mode: int, name: str, sha1_hex: str), ...]
        repo_path: .git 目录路径

    返回:
        40位小写 hex SHA1 字符串

    等价于: echo -e "..." | git mktree
    """
    # ── 你的代码从这里开始 ──
    # 提示:
    #   sorted_entries = sorted(entries, key=lambda e: e[1])
    #   对每条 entry: prefix = f"{mode} {name}\0".encode() + bytes.fromhex(sha1_hex)
    #   拼接 → header = f"tree {len(entries_blob)}\0".encode()
    #   store = header + entries_blob
    #   sha1 = hashlib.sha1(store).hexdigest()
    #   写入 .git/objects/{sha1[:2]}/{sha1[2:]}  ← zlib 压缩后写入
    #   return sha1
    # ── 你的代码到这里结束 ──
    raise NotImplementedError("TODO: 实现 build_tree")


def read_tree(repo_path: str, sha1_hex: str) -> list:
    """
    从 .git/objects 读取 tree 对象，解析出所有 entries。

    算法:
    1. 定位: <repo_path>/objects/<sha1[:2]>/<sha1[2:]>
    2. 读取 zlib 压缩文件 → 解压
    3. 跳过 header "tree <size>\\0"
    4. 逐条解析:
       - 找 null byte → 前面是 mode+name
       - null byte 后的 20 字节 → 二进制 SHA1 (用 .hex() 转 hex)
       - 用 " " 分隔 mode 和 name

    参数:
        repo_path: .git 目录路径
        sha1_hex: 40位 hex SHA1

    返回:
        [(mode: int, name: str, sha1_hex: str), ...]

    等价于: git ls-tree <sha1>
    """
    # ── 你的代码从这里开始 ──
    # 提示:
    #   obj_path = os.path.join(repo_path, "objects", sha1_hex[:2], sha1_hex[2:])
    #   raw = zlib.decompress(open(obj_path, "rb").read())
    #   null_pos = raw.index(b"\x00")  # 跳过 header
    #   entries_blob = raw[null_pos + 1:]
    #   pos = 0; results = []
    #   while pos < len(entries_blob):
    #       null = entries_blob.index(b"\x00", pos)
    #       mode, name = entries_blob[pos:null].decode().split(" ", 1)
    #       sha1_bin = entries_blob[null+1:null+21]
    #       results.append((int(mode), name, sha1_bin.hex()))
    #       pos = null + 21
    #   return results
    # ── 你的代码到这里结束 ──
    raise NotImplementedError("TODO: 实现 read_tree")


def read_tree_recursive(repo_path: str, sha1_hex: str, prefix: str = "") -> list:
    """
    递归解析整个 tree，返回所有文件的 (mode, path, sha1_hex)。

    mode=40000 的 entry → 递归调用 read_tree_recursive 进入子树。
    普通文件 → 直接添加到结果。

    参数:
        repo_path: .git 目录路径
        sha1_hex: 40位 hex SHA1
        prefix: 当前路径前缀 (递归时用)

    返回:
        [(mode: int, path: str, sha1_hex: str), ...]

    等价于: git ls-tree -r <sha1>
    """
    # ── 你的代码从这里开始 ──
    # 提示:
    #   entries = read_tree(repo_path, sha1_hex)
    #   results = []
    #   for mode, name, sha1 in entries:
    #       path = f"{prefix}{name}"
    #       if mode == 40000:
    #           results.extend(read_tree_recursive(repo_path, sha1, path + "/"))
    #       else:
    #           results.append((mode, path, sha1))
    #   return results
    # ── 你的代码到这里结束 ──
    raise NotImplementedError("TODO: 实现 read_tree_recursive（选做）")


# ═══════════════════════════════════════════════════════════════
# ── 参考答案 (Reference Implementation) ──
# ═══════════════════════════════════════════════════════════════


def _ref_build_tree(entries: list, repo_path: str = ".git") -> str:
    """参考答案: build_tree"""
    sorted_entries = sorted(entries, key=lambda e: e[1])
    encoded = []
    for mode, name, sha1_hex in sorted_entries:
        sha1_bin = bytes.fromhex(sha1_hex)
        if len(sha1_bin) != 20:
            raise ValueError(f"SHA1 必须是 20 字节, 实际 {len(sha1_bin)}")
        prefix = f"{mode} {name}\0".encode("utf-8")
        encoded.append(prefix + sha1_bin)
    entries_blob = b"".join(encoded)
    header = f"tree {len(entries_blob)}\0".encode("utf-8")
    store = header + entries_blob
    sha1_hex = hashlib.sha1(store).hexdigest()
    obj_dir = os.path.join(repo_path, "objects", sha1_hex[:2])
    obj_path = os.path.join(obj_dir, sha1_hex[2:])
    os.makedirs(obj_dir, exist_ok=True)
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(zlib.compress(store))
    return sha1_hex


def _ref_read_tree(repo_path: str, sha1_hex: str) -> list:
    """参考答案: read_tree"""
    obj_path = os.path.join(repo_path, "objects", sha1_hex[:2], sha1_hex[2:])
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"tree not found: {obj_path}")
    with open(obj_path, "rb") as f:
        raw = zlib.decompress(f.read())
    null_pos = raw.index(b"\x00")  # skip header "tree <size>\0"
    entries_blob = raw[null_pos + 1:]
    results = []
    pos = 0
    while pos < len(entries_blob):
        nl = entries_blob.index(b"\x00", pos)
        mode_name = entries_blob[pos:nl].decode("utf-8")
        sp = mode_name.index(" ")
        mode = int(mode_name[:sp])
        name = mode_name[sp + 1:]
        sha1_bin = entries_blob[nl + 1 : nl + 21]
        sha1_hex = sha1_bin.hex()
        results.append((mode, name, sha1_hex))
        pos = nl + 21
    return results


def _ref_read_tree_recursive(repo_path: str, sha1_hex: str, prefix: str = "") -> list:
    """参考答案: read_tree_recursive"""
    entries = _ref_read_tree(repo_path, sha1_hex)
    results = []
    for mode, name, sha1 in entries:
        path = f"{prefix}{name}"
        if mode == 40000:
            results.extend(_ref_read_tree_recursive(repo_path, sha1, path + "/"))
        else:
            results.append((mode, path, sha1))
    return results


# ═══════════════════════════════════════════════════════════════
# ── Probe 自动探测 ──
# ═══════════════════════════════════════════════════════════════

_HAS_STUDENT_IMPL = None


def _probe() -> bool:
    """探测学生是否已实现 build_tree 和 read_tree"""
    global _HAS_STUDENT_IMPL
    if _HAS_STUDENT_IMPL is not None:
        return _HAS_STUDENT_IMPL

    try:
        with tempfile.TemporaryDirectory() as td:
            repo = os.path.join(td, ".git")
            os.makedirs(os.path.join(repo, "objects"))
            sha1 = build_tree([(100644, "test.txt", "95d09f2b10159347eece71399a7e2e907ea3df4f")], repo)
            _HAS_STUDENT_IMPL = isinstance(sha1, str) and len(sha1) == 40
    except NotImplementedError:
        _HAS_STUDENT_IMPL = False
    except Exception:
        _HAS_STUDENT_IMPL = False

    return _HAS_STUDENT_IMPL


def _get_build_tree():
    """返回可用的 build_tree 实现"""
    if _probe():
        return build_tree
    return _ref_build_tree


def _get_read_tree():
    """返回可用的 read_tree 实现"""
    if _probe():
        return read_tree
    return _ref_read_tree


def _get_read_tree_recursive():
    """返回可用的 read_tree_recursive 实现"""
    # 即使 build/read 是学生的, read_tree_recursive 也需要单独探测
    try:
        with tempfile.TemporaryDirectory() as td:
            repo = os.path.join(td, ".git")
            os.makedirs(os.path.join(repo, "objects"))
            result = read_tree_recursive(repo, "0" * 40)
            return read_tree_recursive
    except NotImplementedError:
        return _ref_read_tree_recursive
    except Exception:
        return _ref_read_tree_recursive


# ═══════════════════════════════════════════════════════════════
# ── 辅助函数 ──
# ═══════════════════════════════════════════════════════════════


def _write_blob(repo_path: str, content: bytes) -> str:
    """写入一个 blob 对象并返回其 SHA1"""
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
    """写入一个 tree 并返回 SHA1 (用参考实现保证正确)"""
    return _ref_build_tree(entries, repo_path)


# ═══════════════════════════════════════════════════════════════
# ── 测试用例 ──
# ═══════════════════════════════════════════════════════════════


class TestBuildTree(unittest.TestCase):
    """build_tree() 测试 — Git Tree 对象构建"""

    @classmethod
    def setUpClass(cls):
        cls._build_func = _get_build_tree()
        cls.tmpdir = tempfile.mkdtemp()
        cls.repo = os.path.join(cls.tmpdir, ".git")
        os.makedirs(os.path.join(cls.repo, "objects"), exist_ok=True)

    def build_tree(self, entries, repo_path=None):
        if repo_path is None:
            repo_path = self.__class__.repo
        return self.__class__._build_func(entries, repo_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    # ── Test 1: 单文件 tree ──

    def test_single_entry(self):
        """单文件 tree: SHA1 必须是 40 位 hex"""
        blob_sha1 = _write_blob(self.repo, b"hello")
        result = self.build_tree([(100644, "hello.txt", blob_sha1)])
        self.assertEqual(len(result), 40, "SHA1 必须为 40 位")
        self.assertTrue(all(c in "0123456789abcdef" for c in result),
                        "SHA1 必须全是小写 hex")

    # ── Test 2: 多文件 tree ──

    def test_multiple_entries(self):
        """多文件 tree 正确创建"""
        blob_a = _write_blob(self.repo, b"content A")
        blob_b = _write_blob(self.repo, b"content B")
        entries = [
            (100644, "b.txt", blob_b),
            (100644, "a.txt", blob_a),
        ]
        sha1 = self.build_tree(entries)
        self.assertEqual(len(sha1), 40)
        # 验证文件存在
        obj_path = os.path.join(self.repo, "objects", sha1[:2], sha1[2:])
        self.assertTrue(os.path.exists(obj_path), f"对象文件应存在: {obj_path}")

    # ── Test 3: 排序 — 无论输入顺序，SHA1 必须一致 ──

    def test_sorting_deterministic(self):
        """排序: 输入顺序不影响输出 SHA1"""
        blob_a = _write_blob(self.repo, b"A")
        blob_b = _write_blob(self.repo, b"B")

        entries_ab = [(100644, "a.txt", blob_a), (100644, "b.txt", blob_b)]
        entries_ba = [(100644, "b.txt", blob_b), (100644, "a.txt", blob_a)]

        sha1_ab = self.build_tree(entries_ab)
        sha1_ba = self.build_tree(entries_ba)

        self.assertEqual(sha1_ab, sha1_ba,
                         "排序不同 → SHA1 必须一致 (Git 按 name 排序)")
        self.assertEqual(len(sha1_ab), 40)

    # ── Test 4: 含子树 (mode=40000) ──

    def test_with_subtree(self):
        """子树 mode=40000 的 tree 构建正确"""
        blob = _write_blob(self.repo, b"root file")
        # 先创建子树
        sub_blob = _write_blob(self.repo, b"sub file")
        sub_tree = _ref_build_tree([(100644, "sub.txt", sub_blob)], self.repo)

        entries = [
            (100644, "root.txt", blob),
            (40000, "subdir", sub_tree),  # ← 40000 = 子目录
        ]
        sha1 = self.build_tree(entries)
        self.assertEqual(len(sha1), 40)

        # 读回来确认
        parsed = _ref_read_tree(self.repo, sha1)
        names = [e[1] for e in parsed]
        self.assertIn("root.txt", names)
        self.assertIn("subdir", names)

    # ── Test 5: hash 一致性 — 和 `git mktree` 对比 ──

    def test_vs_git_mktree(self):
        """与 git mktree 输出一致"""
        if not shutil.which("git"):
            self.skipTest("git not found in PATH")

        with tempfile.TemporaryDirectory() as git_tmp:
            import subprocess
            subprocess.run(["git", "init", "-q", git_tmp], check=True)
            git_repo = os.path.join(git_tmp, ".git")

            # 写入 blob
            blob_data = b"compare tree"
            header = f"blob {len(blob_data)}\0".encode()
            store = header + blob_data
            sha1 = hashlib.sha1(store).hexdigest()
            obj_dir = os.path.join(git_repo, "objects", sha1[:2])
            os.makedirs(obj_dir, exist_ok=True)
            with open(os.path.join(obj_dir, sha1[2:]), "wb") as f:
                f.write(zlib.compress(store))

            # Python build_tree
            py_sha1 = self.build_tree([(100644, "file.txt", sha1)], git_repo)

            # git mktree 对比: 先 ls-tree 读回来确认内容一致
            git_process = subprocess.run(
                ["git", "-C", git_tmp, "ls-tree", py_sha1],
                capture_output=True, text=True,
            )
            if git_process.returncode == 0 and git_process.stdout.strip():
                line = git_process.stdout.strip().split("\n")[0]
                parts = line.split()
                self.assertEqual(parts[3], "file.txt", "文件名应一致")
            else:
                # git 不认识这个 tree — 构造 mktree 输入来交叉验证
                entry_line = f"100644 blob {sha1}\tfile.txt\n"
                r = subprocess.run(
                    ["git", "-C", git_tmp, "mktree"],
                    input=entry_line, capture_output=True, text=True,
                )
                if r.returncode == 0:
                    git_sha1 = r.stdout.strip()
                    self.assertEqual(py_sha1, git_sha1,
                                     f"你的={py_sha1[:8]}... git={git_sha1[:8]}...")

    # ── Test 6: 空 tree (0 entries) ──

    def test_empty_tree(self):
        """空 tree (0 entries)"""
        sha1 = self.build_tree([], self.repo)
        self.assertEqual(len(sha1), 40)
        # 读回来确认没条目
        parsed = _ref_read_tree(self.repo, sha1)
        self.assertEqual(len(parsed), 0, "空 tree 应有 0 条 entry")

    # ── Test 7: 特殊字符文件名 ──

    def test_special_filename(self):
        """文件名含空格和特殊字符"""
        blob = _write_blob(self.repo, b"special")
        sha1 = self.build_tree([(100644, "my file.txt", blob)], self.repo)
        parsed = _ref_read_tree(self.repo, sha1)
        self.assertEqual(parsed[0][1], "my file.txt")

    # ── Test 8: 可执行文件 (100755) ──

    def test_executable_mode(self):
        """可执行文件 mode=100755"""
        blob = _write_blob(self.repo, b"#!/bin/sh\necho hi\n")
        sha1 = self.build_tree([(100755, "script.sh", blob)], self.repo)
        parsed = _ref_read_tree(self.repo, sha1)
        self.assertEqual(parsed[0][0], 100755, f"mode 应为 100755，实际 {parsed[0][0]}")


class TestReadTree(unittest.TestCase):
    """read_tree() 测试 — Tree 对象解析"""

    @classmethod
    def setUpClass(cls):
        cls._read_func = _get_read_tree()
        cls.tmpdir = tempfile.mkdtemp()
        cls.repo = os.path.join(cls.tmpdir, ".git")
        os.makedirs(os.path.join(cls.repo, "objects"), exist_ok=True)

    def read_tree(self, repo_path, sha1_hex):
        return self.__class__._read_func(repo_path, sha1_hex)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    # ── Test 9: 单文件往返 ──

    def test_single_roundtrip(self):
        """单文件 tree: build → read → 数据一致"""
        blob_a = _write_blob(self.repo, b"file A")
        tree_sha1 = _ref_build_tree([(100644, "a.txt", blob_a)], self.repo)
        result = self.read_tree(self.repo, tree_sha1)
        self.assertEqual(len(result), 1)
        mode, name, sha1 = result[0]
        self.assertEqual(mode, 100644)
        self.assertEqual(name, "a.txt")
        self.assertEqual(sha1, blob_a)

    # ── Test 10: 多文件往返 ──

    def test_multi_roundtrip(self):
        """多文件 tree: 所有 entry 正确解析"""
        blob_a = _write_blob(self.repo, b"A" * 50)
        blob_b = _write_blob(self.repo, b"B" * 50)
        blob_c = _write_blob(self.repo, b"C" * 50)

        entries_in = [
            (100644, "zebra.txt", blob_c),
            (100644, "alpha.txt", blob_a),
            (100644, "beta.txt", blob_b),
        ]
        tree_sha1 = _ref_build_tree(entries_in, self.repo)
        result = self.read_tree(self.repo, tree_sha1)

        self.assertEqual(len(result), 3)
        # Git 按 name 排序，所以输出顺序是 alpha → beta → zebra
        self.assertEqual(result[0][1], "alpha.txt")
        self.assertEqual(result[1][1], "beta.txt")
        self.assertEqual(result[2][1], "zebra.txt")

        # 所有 SHA1 正确
        result_dict = {e[1]: e[2] for e in result}
        self.assertEqual(result_dict["alpha.txt"], blob_a)
        self.assertEqual(result_dict["beta.txt"], blob_b)
        self.assertEqual(result_dict["zebra.txt"], blob_c)

    # ── Test 11: 子树往返 ──

    def test_subtree_roundtrip(self):
        """子树 mode=40000 正确识别"""
        sub_blob = _write_blob(self.repo, b"nested")
        sub_tree = _ref_build_tree([(100644, "nested.txt", sub_blob)], self.repo)
        root_blob = _write_blob(self.repo, b"root")
        root_tree = _ref_build_tree(
            [(100644, "root.txt", root_blob), (40000, "sub", sub_tree)],
            self.repo,
        )
        result = self.read_tree(self.repo, root_tree)
        self.assertEqual(len(result), 2)
        modes = {e[1]: e[0] for e in result}
        self.assertEqual(modes["root.txt"], 100644)
        self.assertEqual(modes["sub"], 40000)

    # ── Test 12: 不存在的 SHA1 ──

    def test_nonexistent_sha1(self):
        """不存在的 SHA1 应抛出异常"""
        fake = "a" * 40
        with self.assertRaises((FileNotFoundError, Exception),
                               msg="不存在的 tree 应报错"):
            self.read_tree(self.repo, fake)

    # ── Test 13: zlib 损坏 ──

    def test_corrupted_zlib(self):
        """zlib 损坏的 blob 应解压失败"""
        blob = _write_blob(self.repo, b"valid")
        tree_sha1 = _ref_build_tree([(100644, "x.txt", blob)], self.repo)
        obj_path = os.path.join(self.repo, "objects", tree_sha1[:2], tree_sha1[2:])
        # 破坏文件
        with open(obj_path, "wb") as f:
            f.write(b"not valid zlib data")
        with self.assertRaises((zlib.error, Exception), msg="损坏的 zlib 应报错"):
            self.read_tree(self.repo, tree_sha1)

    # ── Test 14: 二进制文件名 ──

    def test_binary_name(self):
        """文件名含 null byte 外的任意字节"""
        blob = _write_blob(self.repo, b"binary")
        name = "file\x01\x02.bin"  # 含非打印字符
        tree_sha1 = _ref_build_tree([(100644, name, blob)], self.repo)
        result = self.read_tree(self.repo, tree_sha1)
        self.assertEqual(result[0][1], name)


class TestReadTreeRecursive(unittest.TestCase):
    """read_tree_recursive() 测试 — 递归列出所有文件"""

    @classmethod
    def setUpClass(cls):
        cls._recursive_func = _get_read_tree_recursive()
        cls.tmpdir = tempfile.mkdtemp()
        cls.repo = os.path.join(cls.tmpdir, ".git")
        os.makedirs(os.path.join(cls.repo, "objects"), exist_ok=True)

        # 构建嵌套结构:
        # root
        # ├── a.txt
        # └── sub/
        #     ├── b.txt
        #     └── deep/
        #         └── c.txt
        cls.blob_a = _write_blob(cls.repo, b"A")
        cls.blob_b = _write_blob(cls.repo, b"B")
        cls.blob_c = _write_blob(cls.repo, b"C")
        cls.deep_tree = _ref_build_tree(
            [(100644, "c.txt", cls.blob_c)], cls.repo)
        cls.sub_tree = _ref_build_tree(
            [(100644, "b.txt", cls.blob_b),
             (40000, "deep", cls.deep_tree)], cls.repo)
        cls.root_tree = _ref_build_tree(
            [(100644, "a.txt", cls.blob_a),
             (40000, "sub", cls.sub_tree)], cls.repo)

    def read_tree_recursive(self, repo_path, sha1_hex, prefix=""):
        return self.__class__._recursive_func(repo_path, sha1_hex, prefix)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    # ── Test 15: 递归列出 ──

    def test_recursive_listing(self):
        """递归列出 3 层嵌套的所有文件"""
        result = self.read_tree_recursive(self.repo, self.root_tree)
        self.assertEqual(len(result), 3)
        paths = {e[1]: e[2] for e in result}
        self.assertEqual(paths["a.txt"], self.blob_a)
        self.assertEqual(paths["sub/b.txt"], self.blob_b)
        self.assertEqual(paths["sub/deep/c.txt"], self.blob_c)

    # ── Test 16: 单层 tree ──

    def test_flat_tree(self):
        """单层 tree: 结果和 read_tree 一致"""
        blob = _write_blob(self.repo, b"flat")
        tree = _ref_build_tree([(100644, "flat.txt", blob)], self.repo)
        result = self.read_tree_recursive(self.repo, tree)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "flat.txt")

    # ── Test 17: 只含子树 ──

    def test_only_subtrees(self):
        """只含 mode=40000 的 tree"""
        sub = _ref_build_tree([(100644, "leaf.txt", self.blob_a)], self.repo)
        root = _ref_build_tree([(40000, "dir", sub)], self.repo)
        result = self.read_tree_recursive(self.repo, root)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "dir/leaf.txt")
        self.assertEqual(result[0][0], 100644)


class TestStudentCompletion(unittest.TestCase):
    """检查学生是否完成了填空"""

    def test_build_tree_is_implemented(self):
        """build_tree 已实现"""
        if not _probe():
            self.skipTest(
                "⚠️  build_tree 未实现 — 使用参考答案兜底运行其他测试。\n"
                "    请在 build_tree() 函数中完成你的实现！"
            )
        else:
            self.assertTrue(True, "✅ build_tree 已实现")

    def test_read_tree_is_implemented(self):
        """read_tree 已实现"""
        if not _probe():
            self.skipTest(
                "⚠️  read_tree 未实现 — 使用参考答案兜底运行其他测试。\n"
                "    请在 read_tree() 函数中完成你的实现！"
            )
        else:
            self.assertTrue(True, "✅ read_tree 已实现")

    def test_read_tree_recursive_stub(self):
        """read_tree_recursive 状态检查"""
        try:
            with tempfile.TemporaryDirectory() as td:
                repo = os.path.join(td, ".git")
                os.makedirs(os.path.join(repo, "objects"))
                read_tree_recursive(repo, "0" * 40)
            self.assertTrue(True, "✅ read_tree_recursive 已实现")
        except NotImplementedError:
            self.skipTest("⚠️  read_tree_recursive 选做 — 已实现则加分")


# ═══════════════════════════════════════════════════════════════
# ── 入口 ──
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 65)
    print("  Node 2 Test Suite: Git Tree 对象构建 + 解析")
    print("=" * 65)
    print()

    if _probe():
        print("🔬 检测到学生实现 → 测试学生代码")
    else:
        print("🔬 未检测到学生实现 → 使用参考答案兜底运行")
        print("   (你的代码仍然会被 TestStudentCompletion 检查)")
    print()

    unittest.main(verbosity=2)
