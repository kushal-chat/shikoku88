import os
import json
import base64
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import pandas
import datasets
import csv

BASE_URL = "https://omairi.club/api/spots/{spot_id}/goshuin?page={page}"
MAX_POSTS = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://omairi.club/spots/82856/goshuin", # example goshuin
}

def get_content(url: str):
    """
    Fetch HTML content and parse temple metadata.
    Returns:
        name
        kana
        area
        description
    """
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.find("div", class_=["spot_name"])

    name = title.find("h1").get_text(strip=True)
    kana = title.find("p", class_="spot_name_kana").get_text(strip=True)
    area = title.find("p", class_="spot_title_area").get_text(strip=True)

    try:
        desc = soup.find("div", class_=["spot_desc_all"]).get_text(strip=True)
    except Exception:
        desc = soup.find("div", class_=["spot_attr_inner main"]).get_text(strip=True)

    return name, kana, area, desc


def _extract_posts(json_obj):
    """
    Handle both shapes:
    - list of posts
    - {"data": {"posts": [...]}}
    """
    if isinstance(json_obj, list):
        return json_obj
    if isinstance(json_obj, dict):
        if "data" in json_obj and isinstance(json_obj["data"], dict):
            if "posts" in json_obj["data"]:
                return json_obj["data"]["posts"]
        if "posts" in json_obj:
            return json_obj["posts"]
    return []

def get_images_and_dates(spot_id: int, max_pages: int | None = None):
    page = 1
    image_urls = []
    dates = []

    while True:
        if max_pages is not None and page > max_pages:
            break

        url = BASE_URL.format(spot_id=spot_id, page=page)
        print(f"GET {url}")
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print("Non-200 status, stopping:", r.status_code)
            break

        data = r.json()
        posts = _extract_posts(data)
        if not posts:
            print("No posts in response, stopping.")
            break

        images_taken = 0

        for post in posts:
            date = post.get("created_at") or post.get("visited_date")
            img = post.get("post_picture_800")

            if img:
                dates.append(date)
                image_urls.append(img)
                images_taken += 1

                if images_taken >= 3:  # stop after 3 per page
                    break

            if len(image_urls) >= MAX_POSTS:
                break

        if len(image_urls) >= MAX_POSTS:
            break

        page += 1

    return dates, image_urls


def download_images(image_urls, dest_dir="downloads", spot_id=None):
    os.makedirs(dest_dir, exist_ok=True)
    paths = []

    for idx, url in enumerate(image_urls, start=1):
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path) or f"image_{idx}.jpg"

        if spot_id is not None:
            filename = f"{spot_id}_{idx}_" + filename

        filepath = os.path.join(dest_dir, filename)
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)

        paths.append(filepath)

    return paths


def img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


instruction = "以下の御朱印情報から、神社名・所在地・由来をJSON形式で教えてください。"

def get_bando_33():
    URL = "https://omairi.club/collections/bando33"
    response = requests.get(URL, headers=HEADERS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    collection = soup.find("div", class_=["collection_items_inner"])
    ids = []

    # Find all <a> tags that have a "name" attribute
    for a in collection.find_all("a", attrs={"name": True}):
        name = a["name"]
        # optionally keep only purely numeric ones
        if name.isdigit():
            ids.append(int(name))
        else:
            ids.append(name)  # or skip if you only want numbers

    return ids
    
if __name__ == "__main__":

    spot_ids = get_bando_33() 
    out_csv = "goshuin/metadata.csv"

    # Open CSV for writing
    with open(out_csv, "w", encoding="utf-8", newline="") as fout:
        writer = csv.writer(fout)
        writer.writerow([
            "file_name",
            "spot_id",
            "name",
            "kana",
            "area",
            "background",
            "date"
        ])

        for spot_id in spot_ids:
            print(spot_id)
            name, kana, area, desc = get_content(f"https://omairi.club/spots/{spot_id}")
            print("Metadata:", name, kana, area)

            dates, image_urls = get_images_and_dates(spot_id, max_pages=5)
            print(f"Got {len(image_urls)} images for spot {spot_id}")

            image_paths = download_images(image_urls, dest_dir="goshuin/train", spot_id=spot_id)

            # Write one row per image
            for img_path, date in zip(image_paths, dates):
                writer.writerow([
                    os.path.basename(img_path),
                    spot_id,
                    name,
                    kana,
                    area,
                    desc,
                    date
                ])
                print("wrote to csv")

    print("completed writing to metadata.csv")