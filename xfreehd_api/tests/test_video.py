from base_api import DownloadConfigRAW

from ..api import Client, Video
import pytest


SAMPLE_HTML = """<div class="row">
			<div class="col-lg-9 col-md-8 cp-7">
				<div>

					<div class="video-container" style="height: 68px; background-color: black;">
	<div class="fluid_video_wrapper fluid_player_layout_default" id="fluid_video_wrapper_hdPlayer" style="width: 100%; height: 100%;"><video id="hdPlayer" preload="metadata" playsinline="" webkit-playsinline="" data-img="https://image.xfreehd.com/media/videos/tmb33/1074729/1b.jpg" data-vtt="https://beta.xfreehd.com/media/fluid/vtt.php?id=1074729&amp;time=1044&amp;offset=10" data-thumbs="https://image.xfreehd.com/media/videos/slides/1074/1074729.jpg" data-target="https://beta.xfreehd.com/video/1074729/trucker-randy-did-it-again" data-logo="" style="height: 100%; width: 100%; cursor: none;">
                <source src="https://lb.xfreehd.com/248300433dcb62ed7efc189b12da07ec83b73467.mp4" title="SD" type="video/mp4"><source src="https://lb.xfreehd.com/8974cfa8f132e4d10578ea974401cc9c36971773.mp4" title="HD" type="video/mp4"></video></div>
</div>
				</div>
				
					
				<div class="pull-left m-l-5">
					<div class="pull-left m-t-15">
						<div class="videoLikeError font-weight-bold p-3 hidden"></div>
						<a href="#" class="videoLikeBtn mr-2" id="vote_like_1074729">
							<span class="btn num">
								27
							</span>
							<span class="btn icon">
								<i class="fas fa-thumbs-up"></i>
							</span></a>
						<a href="#" class="videoDisLikeBtn" id="vote_dislike_1074729">
							<span class="btn icon">
								<i class="fas fa-thumbs-down"></i>
							</span>
							<span class="btn num">
								24
							</span></a>
					
					</div>				
				</div>
				<div id="embed_video_box" class="m-t-15" style="display: none;">
					<div class="form-group">
   <textarea name="video_embed_code" rows="6" id="video_embed_code" class="form-control">&lt;iframe width="540" height="380" src="https://beta.xfreehd.com/embed/1074729" frameborder="0" allowfullscreen&gt;&lt;/iframe&gt;</textarea>
					</div>
				</div>
				<div class="pull-left user-container">
					<div class="row">
						<div class="col-xs-4 col-sm-3">
							<a rel="nofollow" href="https://beta.xfreehd.com/user/sodu"><img class="medium-avatar" src="https://beta.xfreehd.com/media/users/943373.jpg"></a>
						</div>
						<div class="col-xs-8 col-sm-9">
							<div>
								<a rel="nofollow" href="https://beta.xfreehd.com/user/sodu" class="standard-link">
									<strong>sodu</strong>
								</a>
							</div>
							<div>
								<button class="videox_subscribe btn btn-sm pt-1 pb-1 pl-2 pr-2" data-id="943373">
									<i class="fas fa-fw fa-rss"></i> <span class="hidden-xs">Subscribe</span>
									<span class="sbadge sbadge-0">2K</span>
								</button>
							</div>
						</div>
					</div>
				</div>
				
				<div class="pull-right big-views font-weight-bold hidden-xs">
					<span class="text-white">2 days ago, </span>
					<span class="text-white">9.6K</span>  views				</div>
				<div class="pull-right big-views-xs font-weight-bold visible-xs pt-0">
					<span class="text-white">2 days ago</span><br>
					<span class="text-white">9.6K</span> views					
				</div>					
				<div class="clearfix"></div>
				<div class="m-t-10 p-bold overflow-hidden">
					Categories: <a class="standard-link" href="https://beta.xfreehd.com/videos/teen">Teen</a>
						, <a class="standard-link" href="https://beta.xfreehd.com/videos/anal">Anal</a>
						, <a class="standard-link" href="https://beta.xfreehd.com/videos/creampie">Creampie</a>
				</div>
				<div class="videoTagsSpace m-t-10 m-b-15 p-bold overflow-hidden">
					Tags:
					<a class="tag" href="https://beta.xfreehd.com/tag/american">american</a>
					<a class="tag" href="https://beta.xfreehd.com/tag/old+and+young">old and young</a>
					<a class="tag" href="https://beta.xfreehd.com/tag/rimming">rimming</a>
				</div>
			</div>
		</div>"""


def test_extract_sample_html():
    data = Video._extract_html(SAMPLE_HTML)
    assert data["title"] == "Trucker Randy Did It Again"
    assert data["likes"] == "27"
    assert data["dislikes"] == "24"
    assert data["publish_date"] == "2 days ago"
    assert data["views"] == "9.6K"
    assert data["author"] == "sodu"
    assert data["author_url"] == "https://beta.xfreehd.com/user/sodu"
    assert data["author_thumbnail"] == "https://beta.xfreehd.com/media/users/943373.jpg"
    assert data["author_subscribers"] == "2K"
    assert data["thumbnail"] == "https://image.xfreehd.com/media/videos/tmb33/1074729/1b.jpg"
    assert data["length"] == "1044"
    assert data["categories"] == ["Teen", "Anal", "Creampie"]
    assert data["tags"] == ["american", "old and young", "rimming"]
    assert len(data["cdn_urls"]) == 2
    assert data["embed_url"] == "https://beta.xfreehd.com/embed/1074729"
    assert data["rating"] == "53%"


@pytest.mark.asyncio
async def test_all():
    client = Client()
    url = "https://beta.xfreehd.com/video/929816/tap-out-pmv"
    video = await client.get_video(url)
    assert isinstance(video.title, str) and len(video.title) > 0
    assert isinstance(video.likes, str) and len(video.likes) > 0
    assert isinstance(video.dislikes, str) and len(video.dislikes) > 0
    assert isinstance(video.publish_date, str) and len(video.publish_date) > 0
    assert isinstance(video.views, str) and len(video.views) > 0
    assert isinstance(video.categories, list) and len(video.categories) > 0
    assert isinstance(video.tags, list) and len(video.tags) > 0
    assert isinstance(video.author, str) and len(video.author) > 0
    assert isinstance(video.author_url, str) and len(video.author_url) > 0
    assert isinstance(video.author_thumbnail, str) and len(video.author_thumbnail) > 0
    assert isinstance(video.author_subscribers, str) and len(video.author_subscribers) > 0
    assert isinstance(video.thumbnail, str) and len(video.thumbnail) > 0
    assert isinstance(video.cdn_urls, list) and len(video.cdn_urls) > 0
    assert isinstance(video.embed_url, str) and len(video.embed_url) > 0
    assert isinstance(video.length, str) and len(video.length) > 0
    assert isinstance(video.rating, str) and len(video.rating) > 0
    assert video.video_qualities() == [480, 720]
    assert await video.download(DownloadConfigRAW(quality="sd")) is True
    assert await video.download(DownloadConfigRAW(quality="hd")) is True
