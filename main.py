import os
import requests
from urllib.parse import urlparse
# from unsloth import to_sharegpt
from bs4 import BeautifulSoup

BASE_URL = "https://omairi.club/api/spots/{spot_id}/goshuin?page={page}"
MAX_POSTS = 5

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://omairi.club/spots/85532/goshuin",
}

def _get_temple_metadata(temple_soup: BeautifulSoup):
    """
    Extract prefecture, city, and temple name.
    """
    title = temple_soup.find("div", class_=["spot_name"])

    name = title.find("h1").get_text(strip=True)
    kana = title.find("p", class_="spot_name_kana").get_text(strip=True)
    area = title.find("p", class_="spot_title_area").get_text(strip=True)

    desc = temple_soup.find("div", class_=["spot_desc_all"]).get_text(strip=True)
    return name, kana, area, desc

def get_content(url: str):
    """
    Fetch HTML content and parse temple metadata.
    """
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    temple_metadata = _get_temple_metadata(soup)

    return temple_metadata


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

        for post in posts:
            # prefer exact timestamp, fall back to visited_date if you want
            date = post.get("created_at") or post.get("visited_date")
            img = post.get("post_picture_800")

            if img:
                dates.append(date)
                image_urls.append(img)

            if len(image_urls) >= MAX_POSTS:
                break

        if len(image_urls) >= MAX_POSTS:
            break

        page += 1

    return dates, image_urls


def download_images(image_urls, dest_dir="downloads", spot_id=None):
    os.makedirs(dest_dir, exist_ok=True)

    for idx, url in enumerate(image_urls, start=1):
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path) or f"image_{idx}.jpg"

        # optionally prefix spot_id
        if spot_id is not None:
            filename = f"{spot_id}_{idx}_" + filename

        filepath = os.path.join(dest_dir, filename)
        print(f"Downloading {url} -> {filepath}")

        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)


instruction = "以下の御朱印情報から、神社名・所在地・由来をJSON形式で教えてください。"

def convert_to_conversation(sample):
    conversation = [
        { "role": "user",
          "content" : [
            {"type" : "text",  "text"  : instruction},
            {"type" : "image", "image" : sample["image"]} ]
        },
        { "role" : "assistant",
          "content" : [
            {"type" : "text",  "text"  : sample["caption"]} ]
        },
    ]
    return { "messages" : conversation }
pass

if __name__ == "__main__":
    spot_id = 78625
    print(get_content(f"https://omairi.club/spots/{spot_id}"))

    # dates, image_urls = get_images_and_dates(spot_id, max_pages=5)

    # print(f"Got {len(image_urls)} posts")
    # for d, u in zip(dates, image_urls):
    #     print(d, u)

    # download_images(image_urls, dest_dir="downloads", spot_id=spot_id)