import requests
import PlexAniSync
import anilist
import logging
from yaml import dump
from datetime import datetime
from anilist import find_id_best_match


anilist.ANILIST_ACCESS_TOKEN = PlexAniSync.ANILIST_ACCESS_TOKEN
anilist.logger.setLevel(logging.CRITICAL)


def get_years_for_season(sid, season_num):
    episodes = requests.get(f"http://192.168.1.169:8989/api/episode?api-key=db7040c91fe44fa48f8a8c88324b8e4b&seriesId={sid}").json()
    return list(set([datetime.fromisoformat(x['airDate']).year for x in episodes
                     if x['seasonNumber'] == season_num and x.get('airDate')]))

def make_ordinal(n):
    '''
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    '''
    n = int(n)
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    return str(n) + suffix


def match_all_titles(series):
    season_matches = []
    for season in series['seasons']:
        season_num = season['seasonNumber']
        if season_num == 0:
            continue
        elif season_num == 1:
            alt_title_nums = (-1, 1)
        else:
            alt_title_nums = (season_num, )
        alternate_titles = [x['title'] for x in series['alternateTitles'] if
                            (x.get('sceneSeasonNumber') or x.get('seasonNumber')) in alt_title_nums]
        if season_num == 1:
            alternate_titles.append(series['title'])
        if season_num > 1 and f'{series["title"]} S{season_num}' in alternate_titles:
            for s1_title in [x['title'] for x in series['alternateTitles'] if
                             (x.get('sceneSeasonNumber') or x.get('seasonNumber')) in (-1, 1)] + [series['title']]:
                alternate_titles.extend([
                    f'{s1_title} Season {season_num}',
                    f'{s1_title} {make_ordinal(season_num)} Season',
                    f'{s1_title} {season_num}'
                ])
        matches = []
        possible_years = get_years_for_season(series['id'], season_num)
        if season_num == 1 and series['year'] not in possible_years:
            possible_years.append(series['year'])
        for title in set(alternate_titles):
            for year in possible_years:
                match = find_id_best_match(title, year)
                if match:
                    matches.append(match)
        if len(set(matches)) == 1:
            season_matches.append((season_num, matches[0]))
        elif len(set(matches)) > 1:
            print(f"Multiple matches for {series['title']}: {', '.join([str(x) for x in matches])}")
            season_matches.append((season_num, matches[0]))
        elif not matches:
            if series['title'] == 'Little Witch Academia':
                season_matches.append((1, 21858))
            elif series['title'] == 'Love Live!' and season_num == 2:
                season_matches.append((2, 19111))
            else:
                print(f"No matches for {series['title']} season {season_num}")
                continue
    return season_matches

def map_from_sonarr():
    sonarr_series_unfiltered = requests.get("http://192.168.1.169:8989/api/series?api-key=db7040c91fe44fa48f8a8c88324b8e4b").json()
    sonarr_series = [x for x in sonarr_series_unfiltered if x['seriesType'] == 'anime']
    with open('custom_mappings.ini', 'w', encoding='utf-8') as f:
        for series in sonarr_series:
            matches = match_all_titles(series)
            for season, match in matches:
                f.write(f"{series['title']}^{season}^{match}\n")

def ini_to_yaml():
    with open('custom_mappings.ini', 'r', encoding='utf-8') as f:
        mappings = f.read()
    mapping_dict = {}
    for mapping in mappings.splitlines():
        title, season, anilist = mapping.split("^")
        if title not in mapping_dict:
            mapping_dict[title] = []
        mapping_dict[title].append({
            "season": int(season),
            "anilist-id": int(anilist),
        })
    output_format = {'entries': []}
    for k, v in mapping_dict.items():
        output_format['entries'].append({
            'title': k,
            'seasons': v
        })
    with open('custom_mappings.yaml', 'w', encoding='utf-8') as f:
        f.write(dump(output_format))


if __name__ == '__main__':
    map_from_sonarr()