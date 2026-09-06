import unittest

from app.services.passwords import hash_password, verify_password


class PasswordTests(unittest.TestCase):
    def test_hash_is_salted_and_verifiable(self):
        password = "ClaveSegura123"
        first = hash_password(password)
        second = hash_password(password)
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password(password, first))
        self.assertFalse(verify_password("ClaveIncorrecta123", first))

    def test_rejects_weak_password(self):
        with self.assertRaises(ValueError):
            hash_password("corta")

    def test_malformed_hash_fails_closed(self):
        self.assertFalse(verify_password("ClaveSegura123", "no-es-un-hash"))
        self.assertFalse(verify_password("ClaveSegura123", None))


if __name__ == "__main__":
    unittest.main()
