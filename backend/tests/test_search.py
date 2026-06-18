from fastapi.testclient import TestClient

from app.main import app


def login_as(username: str, password: str) -> TestClient:
    client = TestClient(app)
    client.__enter__()
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return client


def ensure_librarian(admin_client, username: str) -> TestClient:
    admin_client.post(
        "/api/users", json={"username": username, "password": "librarianpw1", "role": "librarian"}
    )
    return login_as(username, "librarianpw1")


def seed_library(client: TestClient, tag: str) -> dict:
    """Seed a small, isolated library for one test. The shared test DB persists
    across the whole pytest session, so every distinguishing field (category/
    edition name, title, notes) is tagged with a per-test marker word -- search
    assertions combine their real term with `tag` so results from other tests'
    seeded data (e.g. other "Tolkien" books) never leak into an exact-set check.
    """
    fantasy = client.post("/api/categories", json={"name": f"Fantasy {tag}"}).json()
    scifi = client.post("/api/categories", json={"name": f"Sci-Fi {tag}"}).json()
    paperback = client.post("/api/editions", json={"name": f"Paperback {tag}"}).json()
    hardcover = client.post("/api/editions", json={"name": f"Hardcover {tag}"}).json()

    hobbit = client.post(
        "/api/books",
        json={
            "title": f"The Hobbit {tag}",
            "author": "J.R.R. Tolkien",
            "category_id": fantasy["id"],
            "edition_id": paperback["id"],
            "notes": f"A wizard, a dwarf company, and a reluctant burglar. {tag}",
        },
    ).json()
    fellowship = client.post(
        "/api/books",
        json={
            "title": f"The Fellowship of the Ring {tag}",
            "author": "J.R.R. Tolkien",
            "category_id": fantasy["id"],
            "edition_id": hardcover["id"],
            "notes": f"The ring must be destroyed in the fires of Mount Doom. {tag}",
        },
    ).json()
    dune = client.post(
        "/api/books",
        json={
            "title": f"Dune {tag}",
            "author": "Frank Herbert",
            "category_id": scifi["id"],
            "edition_id": paperback["id"],
            "notes": f"A desert planet, spice, and a prophecy. {tag}",
        },
    ).json()

    return {
        "fantasy": fantasy,
        "scifi": scifi,
        "paperback": paperback,
        "hardcover": hardcover,
        "hobbit": hobbit,
        "fellowship": fellowship,
        "dune": dune,
    }


def titles(response_json) -> set[str]:
    return {b["title"] for b in response_json}


def test_search_matches_title(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian1")
    try:
        tag = "tagsearch1"
        seed = seed_library(librarian_client, tag)
        response = librarian_client.get("/api/books", params={"q": f"Hobbit {tag}"})
        assert response.status_code == 200
        assert titles(response.json()) == {seed["hobbit"]["title"]}
    finally:
        librarian_client.__exit__(None, None, None)


def test_search_matches_author_across_multiple_books(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian2")
    try:
        tag = "tagsearch2"
        seed = seed_library(librarian_client, tag)
        response = librarian_client.get("/api/books", params={"q": f"Tolkien {tag}"})
        assert response.status_code == 200
        assert titles(response.json()) == {seed["hobbit"]["title"], seed["fellowship"]["title"]}
    finally:
        librarian_client.__exit__(None, None, None)


def test_search_matches_notes(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian3")
    try:
        tag = "tagsearch3"
        seed = seed_library(librarian_client, tag)
        response = librarian_client.get("/api/books", params={"q": f"spice {tag}"})
        assert response.status_code == 200
        assert titles(response.json()) == {seed["dune"]["title"]}
    finally:
        librarian_client.__exit__(None, None, None)


def test_search_matches_category_and_edition_name(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian4")
    try:
        tag = "tagsearch4"
        seed = seed_library(librarian_client, tag)

        by_category = librarian_client.get("/api/books", params={"q": f"Sci-Fi {tag}"})
        assert titles(by_category.json()) == {seed["dune"]["title"]}

        by_edition = librarian_client.get("/api/books", params={"q": f"Hardcover {tag}"})
        assert titles(by_edition.json()) == {seed["fellowship"]["title"]}
    finally:
        librarian_client.__exit__(None, None, None)


def test_search_prefix_matching(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian5")
    try:
        tag = "tagsearch5"
        seed = seed_library(librarian_client, tag)
        response = librarian_client.get("/api/books", params={"q": f"Tolk {tag}"})
        assert titles(response.json()) == {seed["hobbit"]["title"], seed["fellowship"]["title"]}
    finally:
        librarian_client.__exit__(None, None, None)


def test_search_combines_with_category_filter_as_and(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian6")
    try:
        tag = "tagsearch6"
        seed = seed_library(librarian_client, tag)

        matches = librarian_client.get(
            "/api/books", params={"q": f"Tolkien {tag}", "category_id": seed["fantasy"]["id"]}
        )
        assert titles(matches.json()) == {seed["hobbit"]["title"], seed["fellowship"]["title"]}

        no_matches = librarian_client.get(
            "/api/books", params={"q": f"Tolkien {tag}", "category_id": seed["scifi"]["id"]}
        )
        assert titles(no_matches.json()) == set()
    finally:
        librarian_client.__exit__(None, None, None)


def test_search_multi_word_query_is_anded(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian7")
    try:
        tag = "tagsearch7"
        seed = seed_library(librarian_client, tag)
        response = librarian_client.get("/api/books", params={"q": f"ring fires {tag}"})
        assert titles(response.json()) == {seed["fellowship"]["title"]}
    finally:
        librarian_client.__exit__(None, None, None)


def test_search_no_results_returns_empty_list(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian8")
    try:
        seed_library(librarian_client, "tagsearch8")
        response = librarian_client.get("/api/books", params={"q": "nonexistentbookterm"})
        assert response.status_code == 200
        assert response.json() == []
    finally:
        librarian_client.__exit__(None, None, None)


def test_blank_query_falls_back_to_browse(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian9")
    try:
        seed_library(librarian_client, "tagsearch9")
        blank = librarian_client.get("/api/books", params={"q": "   "})
        no_q = librarian_client.get("/api/books")
        assert blank.status_code == 200
        assert titles(blank.json()) == titles(no_q.json())
    finally:
        librarian_client.__exit__(None, None, None)


def test_search_handles_special_characters_without_error(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian10")
    try:
        seed_library(librarian_client, "tagsearch10")
        for tricky_query in ['"unterminated', "foo: bar", "(parens)", "AND OR NOT", "foo*bar"]:
            response = librarian_client.get("/api/books", params={"q": tricky_query})
            assert response.status_code == 200, (tricky_query, response.text)
    finally:
        librarian_client.__exit__(None, None, None)


def test_search_respects_pagination(admin_client):
    librarian_client = ensure_librarian(admin_client, "search_librarian11")
    try:
        tag = "tagsearch11"
        seed_library(librarian_client, tag)
        page = librarian_client.get("/api/books", params={"q": f"Tolkien {tag}", "limit": 1})
        assert page.status_code == 200
        assert len(page.json()) == 1
    finally:
        librarian_client.__exit__(None, None, None)
