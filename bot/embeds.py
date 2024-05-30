import math
import interactions
from datetime import datetime
from validation import Movie, Show


###########################################
# --------------) General (---------------#
###########################################

def find_max_title_len(movie_titles: list[str], tv_titles: list[str] = None) -> int:
    if tv_titles is None:
        tv_titles = []

    if "http" in movie_titles[0]:
        return max(((len(title)-24) for title in (movie_titles + tv_titles)))

    return max(map(len, movie_titles + tv_titles))


###########################################
# -------------) MainEmbed (--------------#
###########################################

class MainEmbed:
    def __init__(self, title: str, color: int, movie_data, tv_data, column_titles, chunk_size: int = 15):
        self.title = title
        self.color = color
        self.movie_data = movie_data
        self.tv_data = tv_data
        self.column_titles = column_titles
        self.chunk_size = chunk_size

        self.buffer = 4 + find_max_title_len(movie_data[0], tv_data[0])
        self.line = '⏤' * min(int(self.buffer * 0.65), 34)
        self.blank_spaces = "ㅤ" * min(math.ceil(self.buffer / 4), 16)

    def build_embed(self) -> interactions.Embed:
        embed = interactions.Embed(title=self.title, color=self.color)
        movie_fields = self._create_media_fields("Movies", self.movie_data)
        tv_fields = self._create_media_fields("Shows", self.tv_data)
        embed.fields = movie_fields + tv_fields

        return embed

    def _create_media_fields(self, header_title: str, media_data) -> list[dict]:
        fields = [self._create_header(header_title)]
        fields.extend(self._create_chunked_fields(media_data))

        return fields

    def _create_header(self, title: str) -> dict[str, str]:
        return {
            "name": "ㅤ",
            "value": f"{self.line}\n{self.blank_spaces}**{title}**\n{self.line}",
            "inline": False
        }

    def _create_chunked_fields(self, media_data) -> list[dict]:
        fields = []

        for i in range(0, len(media_data[0]), self.chunk_size):
            columns = [media_data[j][i:i + self.chunk_size] for j in range(3)]

            for column in columns:
                fields.append({
                    "name": "ㅤ",
                    "value": '\n'.join(column) if column else "ㅤ",
                    "inline": True
                })

        if fields:
            for i, column_title in enumerate(self.column_titles):
                fields[i]["name"] = column_title

        return fields


###########################################
# --------------) Watched (---------------#
###########################################

class WatchedEmbed(MainEmbed):
    def __init__(self, movie_data: tuple, tv_data: tuple):
        title = "Watched"
        color = 0xff0000
        column_titles = ("Title", "Watched", "ㅤ")
        chunk_size = 35

        super().__init__(title, color, movie_data, tv_data, column_titles, chunk_size)


###########################################
# -------------) To Watch (---------------#
###########################################

class ToWatchEmbed(MainEmbed):
    def __init__(self, movie_data: tuple, tv_data: tuple):
        title = "To Watch"
        color = 0x87ff00
        column_titles = ("Title", "Runtime", "IMDb")

        super().__init__(title, color, movie_data, tv_data, column_titles)


###########################################
# -----------) PreviewEmbed (-------------#
###########################################

class PreviewEmbed:
    IMDB_URL_PATTERN = "https://imdb.com/title/{}"
    SHORT_IMDB_URL_PATTERN = "imdb.com/title/{}"
    POSTER_URL_PATTERN = "https://simkl.in/posters/{}_m.webp"

    def __init__(self, media: Movie | Show, color: int, title: str):
        self.media: Movie | Show = media
        self.base_fields: list[dict] = self._create_base_fields()
        self.color: int = color
        self.title: str = title

    def build_embed(self) -> interactions.Embed:
        embed = self._init_embed()
        embed.author = self._create_author()
        embed.fields = self._create_fields() + self.base_fields

        return embed

    def _create_base_fields(self):
        return [
            {"name": "Runtime", "value": self.media.printable_runtime, "inline": True},
            {"name": "IMDb", "value": self.media.printable_imdb_rating, "inline": True},
            {"name": "Rating", "value": self.media.certification, "inline": True},
            {"name": "Genres", "value": self.media.printable_genres, "inline": False},
            {"name": "Description", "value": self.media.overview, "inline": False},
            {"name": "Release Date", "value": self._format_release_date(), "inline": False}
        ]

    def _format_release_date(self) -> str:
        release_timestamp = self.media.release_timestamp
        if release_timestamp:
            date_time = datetime.fromtimestamp(release_timestamp)
            readable_release = " ".join([chunk.lstrip('0') for chunk in date_time.strftime('%B %d, %Y').split()])
            return f"{readable_release} (<t:{release_timestamp}:R>)"

        return "N/A"

    def _init_embed(self) -> interactions.Embed:
        return interactions.Embed(
            title=self.media.title,
            url=self.IMDB_URL_PATTERN.format(self.media.ids.imdb),
            color=self.color,
            thumbnail=interactions.EmbedAttachment(url=self.POSTER_URL_PATTERN.format(self.media.poster))
        )

    def _create_author(self) -> interactions.EmbedAuthor:
        imdb_id = self.media.ids.imdb
        short_url = self.SHORT_IMDB_URL_PATTERN.format(imdb_id)
        url = self.IMDB_URL_PATTERN.format(imdb_id)
        emoji = "🎥" if self.title == "Movie" else "📺"
        
        return interactions.EmbedAuthor(
            name=f"{emoji} {self.title} 🞄 {short_url}",
            url=url,
        )

    def _create_fields(self) -> list[dict]:
        # OVERRIDE
        pass
    

###########################################
# -----------) Movie Preview (------------#
###########################################

class MoviePreviewEmbed(PreviewEmbed):
    def __init__(self, movie: Movie, color: int):
        super().__init__(movie, color, "Movie")

    def _create_fields(self) -> list[dict]:
        return [
            {"name": "Director", "value": self.media.director, "inline": True},
            {"name": "Budget", "value": self.media.printable_budget, "inline": True},
            {"name": "Revenue", "value": self.media.printable_revenue, "inline": True},
        ]


###########################################
# ------------) TV Preview (--------------#
###########################################

class TVPreviewEmbed(PreviewEmbed):
    def __init__(self, show: Show, color: int):
        super().__init__(show, color, "TV Show")

    def _create_fields(self) -> list[dict]:
        return [
            {"name": "Episodes", "value": str(self.media.total_episodes), "inline": True},
            {"name": "Status", "value": self.media.printable_status, "inline": True},
            {"name": "Network", "value": self.media.network, "inline": True},
        ]


if __name__ == '__main__':
    pass
