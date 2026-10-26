# Library Management System

Stack: HTML/CSS/JS (Fetch API) + Python Flask + SQLite. Node tooling is optional.

## Run

```
pip install -r requirements.txt
python app.py            # open http://127.0.0.1:5000
```

The SQLite database (`library.db`) is created automatically on first run.

## Optional Node tooling

```
npm install
npm run format           # Prettier
npm run lint             # ESLint
npm run dev              # live-server on :5500, proxying /api to Flask (start Flask first)
```

## Tests

```
python -m unittest test_api.py
```

## API

| Method   | Endpoint                    | Purpose                                         |
|----------|-----------------------------|-------------------------------------------------|
| GET      | /api/books?q=               | List / search by title, author, ISBN, category  |
| POST     | /api/books                  | Add a book                                      |
| DELETE   | /api/books/<id>             | Delete a book (blocked if issued)               |
| POST     | /api/books/<id>/issue       | Issue to a member (blocked if unavailable)      |
| POST     | /api/books/<id>/return      | Return a book (blocked if not issued)           |
| GET/POST | /api/members                | List / add members                              |
