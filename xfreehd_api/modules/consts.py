import re

REGEX_THUMBNAIL = re.compile(r'data-img="(.*?)"')
REGEX_VIDEO_DURATION = re.compile(r'og:video:duration" content="(.*?)"')