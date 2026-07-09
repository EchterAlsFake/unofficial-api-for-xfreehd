import re
from selectolax.lexbor import LexborHTMLParser

REGEX_THUMBNAIL = re.compile(r'data-img="(.*?)"')
REGEX_VIDEO_DURATION = re.compile(r'og:video:duration" content="(.*?)"')

def extractor_search(html_content: str) -> list[dict]:
    parser = LexborHTMLParser(html_content)
    video_list = []

    # Target the main grid columns containing the videos
    video_nodes = parser.css("div.col-xs-6.col-sm-6.col-md-4.col-lg-4")

    for node in video_nodes:
        # Use .css_first() to find single child elements safely
        link_el = node.css_first("a.video-link")
        if not link_el:
            continue

        url = link_el.attributes.get("href", "").strip()

        title_el = node.css_first("span.video-title-new")
        title = title_el.text(strip=True) if title_el else ""

        # Extract Thumbnail Image URL
        img_el = node.css_first("img.img-responsive2")
        thumb_url = img_el.attributes.get("data-src") or img_el.attributes.get("src") if img_el else ""

        # Extract Duration
        duration_el = node.css_first("div.duration-new")
        duration = duration_el.text(strip=True) if duration_el else ""

        # Extract Views
        views_el = node.css_first("div.video-views-new")
        views = views_el.text(strip=True) if views_el else ""

        # Extract Rating Percentage
        rating_el = node.css_first("div.video-rating-new b")
        rating = rating_el.text(strip=True) if rating_el else ""

        # Append data dictionary to the list
        video_list.append({
            "url": url,
            "title": title,
            "thumbnail": thumb_url,
            "length": duration,
            "views": views,
            "rating": rating
        })

    return video_list
