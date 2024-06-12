import os
import sqlite3
from contextlib import contextmanager
from validation import Movie, Show, convert_minutes, get_current_timestamp,  printable_title

DATABASE_PATH = f"{os.getcwd()}/list.db"


###########################################
# --------------) General (---------------#
###########################################

@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        yield conn
    finally:
        conn.close()


def released(release_time: int) -> int:
    return int(release_time <= get_current_timestamp())


def execute_query(query: str, params: tuple = ()) -> list | None:
    with get_connection() as db:
        try:
            cursor = db.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()


def commit_query(query: str, params: tuple = ()) -> None:
    with get_connection() as db:
        try:
            cursor = db.cursor()
            cursor.execute(query, params)
            db.commit()
        finally:
            cursor.close()


def entry_exists(table_name: str, simkl_id: int) -> int:
    query = '''
            SELECT EXISTS
            (SELECT 1 FROM {} WHERE simklID = ?);
        '''.format(table_name)

    results = execute_query(query, (simkl_id,))
    exists, = results[0]
    return exists


###########################################
# --------------) Update (----------------#
###########################################

def get_unreleased_ids(table_name: str) -> list | None:
    query = '''
            SELECT simklID
            FROM {}
            WHERE isReleased = 0;
        '''.format(table_name)

    ids = execute_query(query, ())
    return ids


def update_entry(table_name: str, media: Movie | Show) -> None:
    query = '''
            UPDATE {}
            SET isReleased = ?, releaseTime = ?, runtime = ?, rating = ?
            WHERE simklID = ?;
        '''.format(table_name)

    commit_query(query, (released(media.release_timestamp), media.release_timestamp, media.runtime,
                         media.ratings.imdb.rating, media.simkl_id))


###########################################
# --------------) Remove (----------------#
###########################################

def get_owned_entries(table_name: str, search_string: str, user_id: int) -> list[dict]:
    query = '''
            SELECT simklID, title 
            FROM {} 
            WHERE LOWER(title) LIKE ?
            AND userID = ?
            LIMIT 25;
        '''.format(table_name)

    results = execute_query(query, (f'%{search_string.lower()}%', user_id))
    return [
        {
            "name": title,
            "value": simkl_id
        }
        for simkl_id, title in results
    ]


def remove_entry(table_name: str, simkl_id: int, user_id: int) -> None:
    query = '''
            DELETE FROM {}
            WHERE simklID = ?
            AND userID = ?;
        '''.format(table_name)

    commit_query(query, (simkl_id, user_id))


###########################################
# -------------) To Watch (---------------#
###########################################

def insert(media: Movie | Show, user_name: str, user_id: int) -> None:
    query = '''
            INSERT INTO {} (simklID, imdbID, title, isReleased, releaseTime, runtime, rating, addedAt, userName, userID)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        '''.format(media.table_name)

    commit_query(query, (media.ids.simkl, media.ids.imdb, media.title, released(media.release_timestamp),
                         media.release_timestamp, media.runtime, media.imdb_rating, get_current_timestamp(),
                         user_name, user_id))


def get_to_watch_data(table_name: str) -> tuple:
    query = '''
            SELECT simklID, title, runtime, rating, isReleased, releaseTime 
            FROM {} 
            WHERE watchedAt = 0
            ORDER BY addedAt ASC;
        '''.format(table_name)

    results = execute_query(query)
    titles, runtimes, ratings = [], [], []

    for simkl_id, title, runtime, rating, is_released, release_time in results:
        # TITLE: Avatar 5 (in 8 years)
        title_output = [f"[{printable_title(title)}](https://simkl.com/{table_name}/{simkl_id}/)"]
        if not is_released:
            title_output.append(f"(<t:{release_time}:R>)")
        titles.append(" ".join(title_output))

        # RUNTIME: 1h 42m
        runtimes.append(convert_minutes(runtime))

        # RATING: ★ 9.3
        if float(rating):
            ratings.append("★ {:.1f}".format(float(rating)))
        else:
            ratings.append("★ N/A")

    return titles, runtimes, ratings


def search_to_watch_titles(table_name: str, search_string: str) -> list[dict]:
    query = '''
            SELECT simklID, title 
            FROM {} 
            WHERE LOWER(title) LIKE ?
            AND watchedAt = 0
            LIMIT 25;
        '''.format(table_name)
    results = execute_query(query, (f'%{search_string.lower()}%',))

    return [
        {
            "name": title,
            "value": simkl_id
        }
        for simkl_id, title in results
    ]


def select_random_simkl_id(table_name: str) -> int:
    query = '''
            SELECT simklID 
            FROM {} 
            WHERE watchedAt = 0
            AND isReleased = 1
            ORDER BY RANDOM()
            LIMIT 1;
        '''.format(table_name)
    title, = execute_query(query)[0]
    return title


def get_to_watch_owner_data(table_name: str, simkl_id: int) -> list | None:
    query = '''
            SELECT userID, addedAt
            FROM {}
            WHERE simklID = ?
            AND watchedAt = 0;
        '''.format(table_name)

    results = execute_query(query, (simkl_id,))
    return results


###########################################
# --------------) Watched (---------------#
###########################################

def set_watched(table_name: str, simkl_id: int) -> None:
    query = '''
            UPDATE {}
            SET watchedAt = ?
            WHERE simklID = ?;
        '''.format(table_name)

    commit_query(query, (get_current_timestamp(), simkl_id))


def get_watched_data(table_name: str) -> tuple[list[str], list[str], str]:
    query = '''
            SELECT title, watchedAt 
            FROM {} 
            WHERE watchedAt != 0
            ORDER BY title GLOB '[a-z]*' DESC, LOWER(title);
        '''.format(table_name)
    results = execute_query(query)
    titles, watched_at = [], []

    for title, watched_at_time in results:
        titles.append(printable_title(title))
        watched_at.append(f'<t:{watched_at_time}:R>')

    return titles, watched_at, 'ㅤ'


if __name__ == '__main__':
    pass
