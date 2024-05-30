from humanize import intword
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, field_validator


###########################################
# --------------) General (---------------#
###########################################

def get_current_timestamp() -> int:
    return int(datetime.now().timestamp())


def convert_to_unix(date_string: str, dt_format: str) -> int:
    date_obj = datetime.strptime(date_string, dt_format)
    if date_obj.year <= 1969:
        return 0

    unix_timestamp = int(date_obj.timestamp())
    return unix_timestamp


def convert_minutes(total_minutes: int) -> str:
    if not total_minutes:
        return "N/A"

    hours = int(total_minutes) // 60
    minutes = int(total_minutes) % 60
    output = []

    if hours:
        output.append(f"{hours}h")
    if minutes:
        output.append(f"{minutes}m")

    return " ".join(output)


def printable_title(title: str):
    max_length = 40

    if len(title) > max_length:
        return title[:max_length - 3].rstrip() + "..."
    return title


###########################################
# ---------------) Media (----------------#
###########################################

class IMDb(BaseModel):
    rating: Union[float, int, None] = 0


class Ratings(BaseModel):
    imdb: Optional[IMDb] = None


class Ids(BaseModel):
    simkl: Optional[int] = 0
    imdb: Optional[str] = "tt0"


# noinspection PyNestedDecorators
class Media(BaseModel):
    title: str
    year: Optional[int] = 0
    ids: Optional[Ids] = None
    poster: Optional[str] = "N/A"
    runtime: Optional[int] = 0
    ratings: Optional[Ratings] = None
    overview: Optional[str] = "N/A"
    genres: Optional[list[str]] = ["N/A"]
    certification: Optional[str] = "N/A"

    @field_validator(
        "overview", "certification", "director", "total_episodes",
        "network", "released", "first_aired",
        check_fields=False
    )
    @classmethod
    def make_strings_printable(cls, v):
        return v or "N/A"

    @field_validator(
        "runtime", "total_episodes",
        check_fields=False
    )
    @classmethod
    def default_integers(cls, v):
        return v or 0

    @property
    def imdb_rating(self):
        try:
            return self.ratings.imdb.rating
        except AttributeError:
            return 0.0

    @property
    def printable_imdb_rating(self):
        if self.imdb_rating:
            return f"★ {self.imdb_rating:.1f}"
        return "★ N/A"

    @property
    def printable_runtime(self):
        if self.runtime:
            return convert_minutes(self.runtime)
        return "N/A"

    @property
    def printable_genres(self):
        if self.genres:
            return ", ".join(self.genres)
        return "N/A"


###########################################
# ---------------) Movie (----------------#
###########################################

class Movie(Media):
    released: Optional[str]
    director: Optional[str]
    budget: Optional[int]
    revenue: Optional[int]

    @property
    def release_timestamp(self):
        try:
            return convert_to_unix(self.released, "%Y-%m-%d")
        except ValueError:
            return 0

    @property
    def printable_budget(self):
        if isinstance(self.budget, int):
            return f"${intword(self.budget)}"
        return "N/A"

    @property
    def printable_revenue(self):
        if isinstance(self.revenue, int):
            return f"${intword(self.revenue)}"
        return "N/A"

    @property
    def table_name(self):
        return "movies"


###########################################
# ---------------) Show (-----------------#
###########################################

class Show(Media):
    first_aired: Optional[str]
    total_episodes: Optional[int]
    status: Optional[str]
    network: Optional[str]

    @property
    def release_timestamp(self):
        try:
            return convert_to_unix(self.first_aired, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            return 0

    @property
    def printable_status(self):
        if self.status and self.status != "tba":
            return self.status.title()
        return "N/A"

    @property
    def table_name(self):
        return "tv"


if __name__ == '__main__':
    pass
