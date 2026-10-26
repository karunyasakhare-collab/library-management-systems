"""Edge-case tests. Run: python -m unittest test_api.py"""

import os
import tempfile
import unittest

import app as lib


class LibraryTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        lib.app.config.update(DB_PATH=self.path, TESTING=True)
        lib.init_db()
        self.c = lib.app.test_client()
        self.book = self.c.post(
            "/api/books", json={"title": "Dune", "author": "Frank Herbert", "isbn": "111"}
        ).get_json()
        self.member = self.c.post(
            "/api/members", json={"name": "Asha", "email": "a@x.com"}
        ).get_json()

    def tearDown(self):
        os.remove(self.path)

    def test_search_non_existent_book(self):
        r = self.c.get("/api/books?q=nothing-here")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), [])

    def test_search_by_author_and_isbn(self):
        self.assertEqual(len(self.c.get("/api/books?q=herbert").get_json()), 1)
        self.assertEqual(len(self.c.get("/api/books?q=111").get_json()), 1)

    def test_cannot_issue_unavailable_book(self):
        url = f"/api/books/{self.book['id']}/issue"
        self.assertEqual(self.c.post(url, json={"member_id": self.member["id"]}).status_code, 200)
        self.assertEqual(self.c.post(url, json={"member_id": self.member["id"]}).status_code, 409)

    def test_issue_requires_valid_member(self):
        url = f"/api/books/{self.book['id']}/issue"
        self.assertEqual(self.c.post(url, json={"member_id": 999}).status_code, 400)
        self.assertEqual(self.c.post(url, json={}).status_code, 400)

    def test_return_book_not_issued(self):
        self.assertEqual(self.c.post(f"/api/books/{self.book['id']}/return").status_code, 409)

    def test_issue_return_cycle(self):
        bid = self.book["id"]
        self.c.post(f"/api/books/{bid}/issue", json={"member_id": self.member["id"]})
        self.assertEqual(self.c.post(f"/api/books/{bid}/return").status_code, 200)
        self.assertTrue(self.c.get("/api/books").get_json()[0]["available"])

    def test_duplicate_isbn_and_missing_fields(self):
        self.assertEqual(
            self.c.post("/api/books", json={"title": "x", "author": "y", "isbn": "111"}).status_code,
            409,
        )
        self.assertEqual(self.c.post("/api/books", json={"title": "x"}).status_code, 400)

    def test_member_validation(self):
        self.assertEqual(self.c.post("/api/members", json={"name": "B"}).status_code, 400)
        self.assertEqual(
            self.c.post("/api/members", json={"name": "B", "email": "nope"}).status_code, 400
        )
        self.assertEqual(
            self.c.post("/api/members", json={"name": "B", "email": "a@x.com"}).status_code, 409
        )

    def test_delete(self):
        self.assertEqual(self.c.delete("/api/books/999").status_code, 404)
        self.assertEqual(self.c.delete(f"/api/books/{self.book['id']}").status_code, 200)

    def test_cannot_delete_issued_book(self):
        bid = self.book["id"]
        self.c.post(f"/api/books/{bid}/issue", json={"member_id": self.member["id"]})
        self.assertEqual(self.c.delete(f"/api/books/{bid}").status_code, 409)

    def test_index_served(self):
        self.assertEqual(self.c.get("/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
