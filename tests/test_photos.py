import yaml

from chore_tracker import photos
from chore_tracker.main import LISTS_PATH, PHOTOS_DIR

JPG = b"\xff\xd8\xff\xe0" + b"jpegdata"
PNG = b"\x89PNG\r\n\x1a\n" + b"pngdata"
GIF = b"GIF89a" + b"gifdata"
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 "


def _add(client, item="milk", list_name="Groceries"):
    return client.post(f"/api/lists/{list_name}/items", json={"item": item})


def _put(client, data, item="milk", list_name="Groceries", filename="p.png"):
    return client.put(
        f"/api/lists/{list_name}/photo",
        data={"item": item},
        files={"file": (filename, data, "application/octet-stream")},
    )


def test_sniff():
    assert photos.sniff(JPG) == "jpg"
    assert photos.sniff(PNG) == "png"
    assert photos.sniff(GIF) == "gif"
    assert photos.sniff(b"GIF87a..") == "gif"
    assert photos.sniff(WEBP) == "webp"
    assert photos.sniff(b"hello world") is None
    assert photos.sniff(b"") is None


def test_image_url_key_everywhere(client):
    r = _add(client)
    assert r.json()["items"][0]["image_url"] is None
    assert client.get("/api/lists").json()[0]["items"][0]["image_url"] is None
    r = client.put("/api/lists/Groceries/items", json={"item": "milk", "done": True})
    assert r.json()["items"][0]["image_url"] is None
    r = client.post("/api/lists/Groceries/clear")
    assert r.json()["items"] == []
    _add(client)
    r = _put(client, PNG)
    assert r.json()["items"][0]["image_url"].startswith("/api/photos/")
    r = client.delete("/api/lists/Groceries/photo/milk")
    assert r.json()["items"][0]["image_url"] is None


def test_upload_serve_roundtrip(client):
    _add(client)
    r = _put(client, PNG)
    assert r.status_code == 200
    url = r.json()["items"][0]["image_url"]
    got = client.get(url)
    assert got.status_code == 200
    assert got.content == PNG
    assert got.headers["content-type"] == "image/png"
    assert "immutable" in got.headers["cache-control"]


def test_replace_deletes_old_file(client):
    _add(client)
    first = _put(client, PNG).json()["items"][0]["image_url"].rsplit("/", 1)[1]
    second = _put(client, JPG).json()["items"][0]["image_url"].rsplit("/", 1)[1]
    assert first != second
    assert not (PHOTOS_DIR / first).exists()
    assert (PHOTOS_DIR / second).exists()


def test_remove(client):
    _add(client)
    name = _put(client, PNG).json()["items"][0]["image_url"].rsplit("/", 1)[1]
    r = client.delete("/api/lists/Groceries/photo/milk")
    assert r.status_code == 200
    assert not (PHOTOS_DIR / name).exists()
    assert client.get(f"/api/photos/{name}").status_code == 404


def test_too_big_and_not_photo(client):
    _add(client)
    r = _put(client, b"\xff\xd8\xff" + b"0" * photos.MAX_BYTES)
    assert r.status_code == 413
    assert r.json()["detail"] == "Photo is too big (max 10 MB)"
    r = _put(client, b"just text")
    assert r.status_code == 415
    assert r.json()["detail"] == "That file isn't a photo. Use JPEG, PNG, WebP or GIF."


def test_404_wins_over_body_checks(client):
    _add(client)
    big = b"0" * (photos.MAX_BYTES + 5)
    for body in (big, b"text"):
        r = _put(client, body, list_name="Nope")
        assert r.status_code == 404
        assert r.json()["detail"] == "List 'Nope' not found"
        r = _put(client, body, item="eggs")
        assert r.status_code == 404
        assert r.json()["detail"] == "'eggs' is not on Groceries"
    assert client.delete("/api/lists/Nope/photo/milk").status_code == 404
    assert client.delete("/api/lists/Groceries/photo/eggs").status_code == 404


def test_bad_photo_names_are_json_404(client):
    for url in ("/api/photos/..%2Fconfig.yaml", "/api/photos/a/b.png", "/api/photos/notaphoto.png"):
        r = client.get(url)
        assert r.status_code == 404
        assert r.json()["detail"] == "Photo not found"


def test_readd_bought_keeps_photo_then_replace(client):
    _add(client)
    first = _put(client, PNG).json()["items"][0]["image_url"]
    client.put("/api/lists/Groceries/items", json={"item": "milk", "done": True})
    r = _add(client)
    assert r.json()["items"][0]["image_url"] == first
    second = _put(client, WEBP).json()["items"][0]["image_url"]
    assert second != first
    assert not (PHOTOS_DIR / first.rsplit("/", 1)[1]).exists()


def test_lists_yaml_without_image_loads(client):
    LISTS_PATH.write_text(yaml.dump({"lists": [{"name": "Old", "items": [{"name": "x", "done": False}]}]}))
    items = client.get("/api/lists").json()[0]["items"]
    assert items == [{"name": "x", "done": False, "image_url": None}]


def _name(url):
    return url.rsplit("/", 1)[1]


def test_delete_item_removes_photo(client):
    _add(client)
    _add(client, "eggs")
    url = _put(client, PNG).json()["items"][0]["image_url"]
    keep = _put(client, JPG, item="eggs").json()["items"][1]["image_url"]
    client.delete("/api/lists/Groceries/items/milk")
    assert not (PHOTOS_DIR / _name(url)).exists()
    assert client.get(url).status_code == 404
    assert client.get(keep).status_code == 200


def test_clear_removes_only_bought_photos(client):
    for n in ("milk", "eggs", "tea"):
        _add(client, n)
    urls = {n: _put(client, PNG, item=n).json()["items"][["milk", "eggs", "tea"].index(n)]["image_url"] for n in ("milk", "eggs", "tea")}
    client.put("/api/lists/Groceries/items", json={"item": "milk", "done": True})
    client.put("/api/lists/Groceries/items", json={"item": "tea", "done": True})
    _add(client, "tea")  # re-added: not done, keeps its photo
    client.post("/api/lists/Groceries/clear")
    assert not (PHOTOS_DIR / _name(urls["milk"])).exists()
    assert client.get(urls["milk"]).status_code == 404
    assert client.get(urls["eggs"]).status_code == 200
    assert client.get(urls["tea"]).status_code == 200


def test_delete_list_removes_photos(client):
    _add(client)
    url = _put(client, PNG).json()["items"][0]["image_url"]
    assert client.delete("/api/lists/Groceries").status_code == 200
    assert not (PHOTOS_DIR / _name(url)).exists()
    assert client.get(url).status_code == 404
