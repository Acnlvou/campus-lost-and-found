"""密码散列与 CSRF 令牌的单元测试（覆盖 app/core/security.py）。"""

import re

import pytest

from app.core.security import hash_password, new_csrf, verify_password

HASH_PATTERN = re.compile(r"^pbkdf2_sha256\$\d+\$[0-9a-f]{32}\$[0-9a-f]{64}$")


class TestHashPassword:
    def test_output_matches_documented_format(self):
        stored = hash_password("Campus123!")
        assert HASH_PATTERN.match(stored), stored

    def test_iteration_count_is_strong_enough(self):
        _, iterations, _, _ = hash_password("Campus123!").split("$")
        assert int(iterations) == 260_000

    def test_salt_is_random_for_same_password(self):
        first = hash_password("Campus123!")
        second = hash_password("Campus123!")
        assert first != second
        assert first.split("$")[2] != second.split("$")[2]

    def test_plaintext_is_never_embedded(self):
        assert "Campus123!" not in hash_password("Campus123!")

    def test_supports_empty_and_unicode_passwords(self):
        assert verify_password("", hash_password(""))
        assert verify_password("密码123", hash_password("密码123"))


class TestVerifyPassword:
    def test_accepts_correct_password(self):
        assert verify_password("Campus123!", hash_password("Campus123!"))

    @pytest.mark.parametrize(
        "candidate",
        ["Campus123", "campus123!", "Campus123! ", "", "Campus123!!"],
    )
    def test_rejects_wrong_password(self, candidate):
        assert not verify_password(candidate, hash_password("Campus123!"))

    @pytest.mark.parametrize(
        "stored",
        [
            "",
            "not-a-hash",
            "pbkdf2_sha256$260000$deadbeef",  # 缺少 digest
            "pbkdf2_sha256$not-a-number$deadbeef$deadbeef",  # 迭代次数非数字
            "pbkdf2_sha256$260000$zzzz$deadbeef",  # salt 非十六进制
            "bcrypt$12$abcd$ef01",  # 未知算法但格式可解析
        ],
    )
    def test_malformed_hash_returns_false_instead_of_raising(self, stored):
        assert verify_password("Campus123!", stored) is False

    def test_rejects_tampered_digest(self):
        stored = hash_password("Campus123!")
        prefix, iterations, salt, digest = stored.split("$")
        flipped = ("0" if digest[0] != "0" else "1") + digest[1:]
        assert not verify_password("Campus123!", f"{prefix}${iterations}${salt}${flipped}")


class TestNewCsrf:
    def test_is_48_hex_characters(self):
        token = new_csrf()
        assert len(token) == 48
        assert re.fullmatch(r"[0-9a-f]{48}", token)

    def test_tokens_are_not_reused(self):
        tokens = {new_csrf() for _ in range(200)}
        assert len(tokens) == 200
