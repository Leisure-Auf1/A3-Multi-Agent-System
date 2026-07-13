#!/usr/bin/env python3
"""
Node 1 测试 — Git Blob 对象 SHA1 计算 + zlib 解压读取

学生画像: visual_learner_hates_magic
  - 底层逻辑控
  - 极度讨厌机械记忆git命令
  - 必须看懂.git/objects物理存储结构
  - 喜: 图解SHA1+手动仿真二进制格式
  - 恶: 罗列命令而不解释字节变化

测试覆盖:
  T1-T6: sha1_file 正确性测试
  T7-T8: read_blob 正确性测试
  T9:    sha1_file 确定性测试（幂等）
  T10:   read_blob 错误处理
  T11:   大文件 sha1_file 测试
  T12:   Probe 兜底 —— 和真实 git 命令交叉比对

用法:
  # 测试学生的 exercise.py
  python outputs/node-1-tests.py

  # 测试参考 solution.py
  python outputs/node-1-tests.py --solution
"""

import hashlib
import os
import subprocess
import sys
import tempfile
import zlib
import unittest
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# Probe 机制: 尝试从 exercise.py 导入，失败则 fallback 到 solution.py
# ═══════════════════════════════════════════════════════════════

def _resolve_implementation(force_solution: bool = False):
    """
    返回 (sha1_file, read_blob, source_name) 三元组。

    优先级:
      1. --solution 标志 → 强制导入 solution.py
      2. exercise.py 中有任何非 pass 的实现 → 使用 exercise.py
      3. fallback 到 solution.py
    """
    if force_solution:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import solution
        return staticmethod(solution.sha1_file), staticmethod(solution.read_blob), "solution.py"

    # 尝试从 exercise.py 导入
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import exercise

        # 检查是否真的实现了（不只是 pass stub）
        import inspect
        sha1_src = inspect.getsource(exercise.sha1_file)
        readblob_src = inspect.getsource(exercise.read_blob)

        sha1_implemented = "pass" not in sha1_src.split("# TODO")[0] if "# TODO" in sha1_src else True
        readblob_implemented = "pass" not in readblob_src.split("# TODO")[0] if "# TODO" in readblob_src else True

        if sha1_implemented or readblob_implemented:
            # 至少有一个实现了，使用 exercise
            return staticmethod(exercise.sha1_file), staticmethod(exercise.read_blob), "exercise.py"
        else:
            print("[Probe] exercise.py 中两个函数都还是 pass stub，fallback 到 solution.py")
    except (ImportError, SyntaxError) as e:
        print(f"[Probe] 无法导入 exercise.py ({e})，fallback 到 solution.py")
    except Exception:
        pass

    # Fallback
    import solution
    return staticmethod(solution.sha1_file), staticmethod(solution.read_blob), "solution.py"


# ═══════════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════════

class TestSha1File(unittest.TestCase):
    """sha1_file 正确性测试"""

    @classmethod
    def setUpClass(cls):
        force = "--solution" in sys.argv
        cls.sha1_file, cls.read_blob, cls.source = _resolve_implementation(force)
        print(f"\n{'='*60}")
        print(f"测试目标: {cls.source}")
        print(f"{'='*60}")

    def _make_temp_file(self, content: bytes) -> str:
        """创建临时文件并写入内容，返回路径"""
        tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False)
        tmp.write(content)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    # ── T1: "hello world\n" ──────────────────────────────────

    def test_t1_hello_world_newline(self):
        """T1: b'hello world\\n' (12字节) → a0423484..."""
        path = self._make_temp_file(b"hello world\n")
        result = self.sha1_file(path)
        expected = "3b18e512dba79e4c8300dd08aeb37f8e728b8dad"
        self.assertEqual(
            result, expected,
            f"\n输入: b'hello world\\n' (12字节)"
            f"\n预期 SHA1: {expected}"
            f"\n你的 SHA1: {result}"
            f"\n提示: 头部应该是 b'blob 12\\x00' (共8字节)，"
            f"拼接后共20字节送入 SHA1"
        )

    # ── T2: "hello world" (无换行) ───────────────────────────

    def test_t2_hello_world_no_newline(self):
        """T2: b'hello world' (11字节) → 95d09f2b..."""
        path = self._make_temp_file(b"hello world")
        result = self.sha1_file(path)
        expected = "95d09f2b10159347eece71399a7e2e907ea3df4f"
        self.assertEqual(
            result, expected,
            f"\n输入: b'hello world' (11字节，无换行)"
            f"\n预期 SHA1: {expected}"
            f"\n你的 SHA1: {result}"
            f"\n提示: 头部应该是 b'blob 11\\x00'"
        )

    # ── T3: 空文件 ───────────────────────────────────────────

    def test_t3_empty_file(self):
        """T3: 空文件 (0字节) → e69de29b..."""
        path = self._make_temp_file(b"")
        result = self.sha1_file(path)
        expected = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
        self.assertEqual(
            result, expected,
            f"\n输入: b'' (0字节，空文件)"
            f"\n预期 SHA1: {expected}"
            f"\n你的 SHA1: {result}"
            f"\n提示: 头部应该是 b'blob 0\\x00'"
        )

    # ── T4: 单字符 ───────────────────────────────────────────

    def test_t4_single_char(self):
        """T4: b'A' (1字节) → 正确 SHA1"""
        path = self._make_temp_file(b"A")
        result = self.sha1_file(path)
        expected = "8c7e5a667f1b771847fe88c01c3de34413a1b220"
        self.assertEqual(
            result, expected,
            f"\n输入: b'A' (1字节)"
            f"\n预期 SHA1: {expected}"
            f"\n你的 SHA1: {result}"
            f"\n提示: 头部应该是 b'blob 1\\x00'"
        )

    # ── T5: Unicode 内容 ─────────────────────────────────────

    def test_t5_unicode_content(self):
        """T5: UTF-8 多字节内容 '你好' → 正确 SHA1"""
        path = self._make_temp_file("你好".encode("utf-8"))
        result = self.sha1_file(path)
        expected = "f3ca6104089db6e23891a35bfa058d287281c476"
        self.assertEqual(
            result, expected,
            f"\n输入: '你好'.encode('utf-8') (6字节)"
            f"\n预期 SHA1: {expected}"
            f"\n你的 SHA1: {result}"
            f"\n提示: 头部应该是 b'blob 6\\x00'，"
            f"长度是字节数(6)，不是字符数(2)"
        )

    # ── T6: 二进制内容 ───────────────────────────────────────

    def test_t6_binary_content(self):
        """T6: 含 NUL 字节的二进制内容 → 正确处理"""
        content = bytes(range(256))  # 0x00 到 0xFF
        path = self._make_temp_file(content)
        result = self.sha1_file(path)

        # 手动计算预期值
        header = f"blob 256\0".encode()
        store = header + content
        expected = hashlib.sha1(store).hexdigest()

        self.assertEqual(
            result, expected,
            f"\n输入: bytes(range(256)) (256字节，含 NUL)"
            f"\n预期 SHA1: {expected}"
            f"\n你的 SHA1: {result}"
            f"\n提示: 使用二进制模式读文件，NUL 字节不能截断内容"
        )

    # ── T7: 确定性（幂等） ───────────────────────────────────

    def test_t7_deterministic(self):
        """T7: 同一内容多次计算，结果始终相同"""
        path = self._make_temp_file(b"deterministic test\n")
        results = [self.sha1_file(path) for _ in range(5)]
        self.assertEqual(len(set(results)), 1,
                         f"5次计算结果不一致: {results}")

    # ── T8: 大文件 ───────────────────────────────────────────

    def test_t8_large_file(self):
        """T8: 1MB 文件 — 验证大文件也能正确哈希"""
        content = b"x" * (1024 * 1024)  # 1 MB
        path = self._make_temp_file(content)

        result = self.sha1_file(path)

        header = f"blob {len(content)}\0".encode()
        store = header + content
        expected = hashlib.sha1(store).hexdigest()

        self.assertEqual(result, expected,
                         f"1MB 文件 SHA1 不匹配——检查你是否一次性读完了全部内容")


class TestReadBlob(unittest.TestCase):
    """read_blob 正确性测试（需要构造 .git/objects/ 结构）"""

    @classmethod
    def setUpClass(cls):
        force = "--solution" in sys.argv
        cls.sha1_file, cls.read_blob, cls.source = _resolve_implementation(force)

    def setUp(self):
        """创建临时 Git 仓库结构"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmpdir.name) / "test-repo"
        self.objects = self.repo / ".git" / "objects"
        self.objects.mkdir(parents=True)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_blob(self, content: bytes) -> str:
        """在临时仓库中创建一个 blob 对象，返回其 SHA1"""
        byte_count = len(content)
        header = f"blob {byte_count}\0".encode()
        store = header + content

        sha1_hex = hashlib.sha1(store).hexdigest()

        obj_dir = self.objects / sha1_hex[:2]
        obj_dir.mkdir(exist_ok=True)
        obj_path = obj_dir / sha1_hex[2:]
        obj_path.write_bytes(zlib.compress(store))

        return sha1_hex

    # ── T9: 读取简单 blob ────────────────────────────────────

    def test_t9_read_simple_blob(self):
        """T9: 写入 b'hello git' 作为 blob，读取验证"""
        content = b"hello git"
        sha1 = self._write_blob(content)

        result = self.read_blob(str(self.repo), sha1)
        self.assertEqual(
            result, content,
            f"\n写入内容: {content!r}"
            f"\nSHA1: {sha1}"
            f"\n读取结果: {result!r}"
            f"\n提示: 解压后在第一个 \\x00 处切分"
        )

    # ── T10: 读取空 blob ─────────────────────────────────────

    def test_t10_read_empty_blob(self):
        """T10: 读取空内容 blob"""
        content = b""
        sha1 = self._write_blob(content)

        result = self.read_blob(str(self.repo), sha1)
        self.assertEqual(
            result, content,
            f"\n写入内容: b'' (空)"
            f"\nSHA1: {sha1}"
            f"\n读取结果: {result!r}"
            f"\n提示: 空 blob 的存储是 b'blob 0\\x00'，"
            f"解压后 NUL 在位置5，返回空 bytes"
        )

    # ── T11: 读取含 NUL 字节的 blob ──────────────────────────

    def test_t11_read_binary_blob(self):
        """T11: 写入含 NUL 字节的二进制内容，读取验证"""
        content = b"before\0after"  # 中间有个 NUL
        sha1 = self._write_blob(content)

        result = self.read_blob(str(self.repo), sha1)
        self.assertEqual(
            result, content,
            f"\n写入内容: b'before\\x00after'"
            f"\nSHA1: {sha1}"
            f"\n读取结果: {result!r}"
            f"\n提示: 用 raw.index(b'\\x00') 只找第一个 NUL，"
            f"内容中的 NUL 不会被误切"
        )

    # ── T12: 不存在的 SHA1 应该报错 ──────────────────────────

    def test_t12_nonexistent_sha1(self):
        """T12: 请求不存在的 blob，应该抛出 FileNotFoundError"""
        fake_sha1 = "a" * 40  # 全是 'a' 的 40 字符 SHA1
        with self.assertRaises(
            (FileNotFoundError, OSError),
            msg=f"\nSHA1: {fake_sha1}"
                f"\n预期: FileNotFoundError 或 OSError"
                f"\n提示: 文件不存在时 Path.read_bytes() 会抛出 FileNotFoundError"
        ):
            self.read_blob(str(self.repo), fake_sha1)


# ═══════════════════════════════════════════════════════════════
# Probe: 与真实 Git 命令交叉比对
# ═══════════════════════════════════════════════════════════════

class TestGitProbe(unittest.TestCase):
    """Probe 测试 —— 如果你装了 git，和真实 git hash-object 交叉比对"""

    @classmethod
    def setUpClass(cls):
        force = "--solution" in sys.argv
        cls.sha1_file, cls.read_blob, cls.source = _resolve_implementation(force)

        # 检查 git 是否可用
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
            self.skipTest("git 命令不可用，跳过 probe 测试")

        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmpdir.name) / "probe-repo"

        # 初始化 git 仓库
        subprocess.run(
            ["git", "init", str(self.repo)],
            capture_output=True, check=True
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def _git_hash_object(self, content: bytes) -> str:
        """用 git hash-object --stdin 计算 SHA1"""
        result = subprocess.run(
            ["git", "-C", str(self.repo), "hash-object", "--stdin"],
            input=content,
            capture_output=True,
            timeout=10,
        )
        return result.stdout.decode().strip()

    def _git_hash_object_write(self, content: bytes) -> str:
        """用 git hash-object -w --stdin 写入对象并返回 SHA1"""
        result = subprocess.run(
            ["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"],
            input=content,
            capture_output=True,
            timeout=10,
        )
        return result.stdout.decode().strip()

    # ── Prob1: sha1_file 与 git hash-object 比对 ─────────────

    def test_probe1_sha1_vs_git(self):
        """Prob1: sha1_file 与 git hash-object 对多种输入输出一致"""
        test_inputs = [
            b"hello world\n",
            b"hello world",
            b"",
            b"test",
            b"a" * 1000,        # 1KB 重复字符
            "你好世界".encode("utf-8"),
            bytes(range(256)),   # 全二进制
        ]

        for content in test_inputs:
            with self.subTest(content=content):
                # 写入临时文件
                tmp = tempfile.NamedTemporaryFile(
                    mode="wb", suffix=".txt", delete=False,
                    dir=self.tmpdir.name
                )
                tmp.write(content)
                tmp.close()

                try:
                    our_sha1 = self.sha1_file(tmp.name)
                    git_sha1 = self._git_hash_object(content)

                    self.assertEqual(
                        our_sha1, git_sha1,
                        f"\n内容: {content[:50]!r}..."
                        f"\n我们的 SHA1: {our_sha1}"
                        f"\nGit 的 SHA1: {git_sha1}"
                        f"\n长度: {len(content)} 字节"
                    )
                finally:
                    os.unlink(tmp.name)

    # ── Prob2: read_blob 与 git cat-file 比对 ────────────────

    def test_probe2_read_vs_git(self):
        """Prob2: read_blob 与 git cat-file -p 输出一致"""
        test_contents = [
            b"hello world\n",
            b"",
            b"binary \x00\x01\x02\xff content",
            "多字节 UTF-8 🎉".encode("utf-8"),
        ]

        for content in test_contents:
            with self.subTest(content=content):
                # 用 git 写入对象
                sha1 = self._git_hash_object_write(content)

                # 我们的 read_blob
                our_content = self.read_blob(str(self.repo), sha1)

                self.assertEqual(
                    our_content, content,
                    f"\nGit SHA1: {sha1}"
                    f"\n原始内容: {content!r}"
                    f"\n我们读到的: {our_content!r}"
                )

    # ── Prob3: 双向验证 —— 写入后 Git 能读 ──────────────────

    def test_probe3_bidirectional(self):
        """Prob3: 我们用 Python 写入 blob，Git 能 cat-file 读回来"""
        content = b"written by python, read by git\n"

        # 用 Python 的方式构造并写入 blob
        byte_count = len(content)
        header = f"blob {byte_count}\0".encode()
        store = header + content
        sha1_hex = hashlib.sha1(store).hexdigest()

        obj_dir = self.repo / ".git" / "objects" / sha1_hex[:2]
        obj_dir.mkdir(parents=True, exist_ok=True)
        obj_path = obj_dir / sha1_hex[2:]
        obj_path.write_bytes(zlib.compress(store))

        # Git 能读回来
        result = subprocess.run(
            ["git", "-C", str(self.repo), "cat-file", "-p", sha1_hex],
            capture_output=True, timeout=10,
        )

        self.assertEqual(
            result.stdout, content,
            f"\n我们写入的 SHA1: {sha1_hex}"
            f"\n我们写入的内容: {content!r}"
            f"\nGit cat-file 输出: {result.stdout!r}"
            f"\nGit stderr: {result.stderr.decode()}"
            f"\n提示: 如果 git 报 'not a valid object name'，"
            f"检查 zlib 压缩是否正确"
        )


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 打印测试说明
    force_solution = "--solution" in sys.argv
    target = "solution.py" if force_solution else "exercise.py (probe fallback → solution.py)"

    print("╔══════════════════════════════════════════════════════╗")
    print("║  Node 1 测试套件 — Git Blob 对象仿真                ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  目标: {target:<44s} ║")
    print("║  测试: T1-T8 (sha1_file) + T9-T12 (read_blob)      ║")
    print("║  Probe: Prob1-Prob3 (与真实 git 交叉比对)           ║")
    print("║  选项: --solution  强制测试 solution.py             ║")
    print("╚══════════════════════════════════════════════════════╝")

    # 移除 --solution 参数，避免 unittest 误解
    if "--solution" in sys.argv:
        sys.argv.remove("--solution")

    unittest.main(verbosity=2)
