import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

def get_soup(url):
    """
    Takes in a url and returns the parsed BeautifulSoup code for that url with
    handling capabilities if the request 'bounces'.
    """

    s = requests.Session()

    retries = Retry(
        total = 10,
        backoff_factor = 0.1,
        status_forcelist = [500, 502, 503, 504]
        )

    s.mount('http://', HTTPAdapter(max_retries = retries))

    return BeautifulSoup(s.get(url).text, 'html.parser')


def get_stats_soup(url):
    """
    Takes in the url of the players' ESPN bio and returns the soup code for the
    player's stats page.
    """

    player_soup = get_soup(url)
    back_half = player_soup.find('a', text = 'Stats').get('href')
    stats_url = 'http://www.espn.com' + back_half

    return get_soup(stats_url)


def convert_name_to_soup(name):
    """
    Takes a player's name and returns the soup for that player's stats page.
    """

    player_url = ('http://www.espn.com/mlb/players?search={}&alltime=true&statusId=1'
    .format(name))

    try:
        return get_stats_soup(player_url)
    except AttributeError:
        return None
    except:
        raise


def get_stats(soup, year):
    """
    Scrapes ESPN.com for a player's statistics for the desired season and
    returns a dict containing those stats.
    """

    tables = soup.find_all('table', attrs = {'class':'tablehead'})
    first_table = tables[0]
    last_table = tables[len(tables) - 1]
    second_to_last_table = tables[len(tables) - 2]

    def get_stats_for_desired_year(table, year):
        """
        Checks a player's stats table for the correct season and returns a list
        of stats for that season.
        """

        # Retrieve the table's headers
        header_soup = table.find('tr', attrs = {'class':'colhead'})
        categories = []
        headers = ['SEASON', 'TEAM',]

        for header in header_soup:
            categories.append(header)

        for header in categories[4:]:
            headers.append(header.get_text())

        # Retrieve the table's contents for the desired season
        all_seasons = table.find_all('tr', attrs = {'class':['evenrow','oddrow']})
        correct_seasons = []

        for season in all_seasons:
            correct_year = season.find('td', text = year)
            if correct_year:
                correct_seasons.append(season)

        if not correct_seasons:
            stats = []
        elif len(correct_seasons) == 1:
            stats = correct_seasons[0].get_text().split()
            if stats:
                team_GP = stats.pop(1)
                team = team_GP[:3]
                GP = team_GP[3:]
                stats.insert(1, team)
                stats.insert(2, GP)
        else:
            for team in correct_seasons:
                if team.find('td', text = 'Total'):
                    stats = team.get_text().split()
                    team_GP = stats.pop(1)
                    team = team_GP[:5]
                    GP = team_GP[5:]
                    stats.insert(1, team)
                    stats.insert(2, GP)
                    break

        if stats:
            WHIP_ERA = stats.pop()
            WHIP = WHIP_ERA[:4]
            ERA = WHIP_ERA[4:]
            stats.append(WHIP)
            stats.append(ERA)

        stats_dict = {}
        for header, stat in zip(headers, stats):
            stats_dict[header] = stat

        return stats_dict

    main_dict = get_stats_for_desired_year(first_table, year)
    misc_dict = get_stats_for_desired_year(second_to_last_table, year)
    misc_dict_ii = get_stats_for_desired_year(last_table, year)

    stats_dict = dict(main_dict.items() +
                      misc_dict.items() +
                      misc_dict_ii.items())

    return stats_dict


def calculate_pure_fip(stats, year):
    """
    Calculates FIP before adjusting by the FIP constant.
    """

    HR = float(stats['HR'])
    BB = float(stats['BB'])
    HBP = float(stats['HBP'])
    K = float(stats['SO'])
    IP = float(stats['IP'])

    return ((13 * HR) + (3 * (BB + HBP)) - (2 * K)) / (IP)


def calculate_pure_xfip(stats, year):
    """
    Calculates xFIP before adjusting by the FIP constant.
    """

    league_averages = get_league_averages(year)

    lgHRFB = float(league_averages['HR']) / float(league_averages['FB'])
    FB = float(stats['FB'])
    BB = float(stats['BB'])
    HBP = float(stats['HBP'])
    K = float(stats['SO'])
    IP = float(stats['IP'])

    return ((13 * (FB * lgHRFB)) + (3 * (BB + HBP)) - (2 * K)) / (IP)


def get_league_averages(year):
    """
    Returns a dictionary containing the league averages for various statistics
    for the desired year.
    """

    pitching_url = ('http://www.espn.com/mlb/stats/team/_/stat/pitching/year/{}'
                    .format(year))
    batting_url = ('http://www.espn.com/mlb/stats/team/_/stat/batting/year/{}'
                   .format(year))
    exp_batting_url = (
    'http://www.espn.com/mlb/stats/team/_/stat/batting/year/{}/type/expanded'
    .format(year))

    exp_batting_ii_url = (
    'http://www.espn.com/mlb/stats/team/_/stat/batting/year/{}/type/expanded-2'
    .format(year))

    def get_averages(url):
        """
        Returns the headers and MLB averages for a given ESPN MLB team
        statistics page.
        """

        soup = get_soup(url)

        # Retrieve headers
        header_column = soup.find('td', text = 'LEAGUE AVERAGES').parent
        headers = []

        for header in header_column:
            headers.append(header.get_text())

        # Retrieve the MLB averages
        mlb_avgs = soup.find('td', text = 'Major League Baseball').parent
        stats = []

        for stat in mlb_avgs:
            stats.append(stat.get_text())

        stats_dict = {}

        for header, stat in zip(headers, stats):
            stats_dict[header] = stat

        return stats_dict

    league_averages = dict(get_averages(batting_url).items() +
                           get_averages(exp_batting_url).items() +
                           get_averages(exp_batting_ii_url).items() +
                           get_averages(pitching_url).items()
                           )

    return league_averages


def calculate_fip_constant(year):
    """
    Calculates the FIP constant. The actual value will differ slightly from
    this calculated value because the actual value assigns different weightings
    based on the run environment of a given year.
    """

    league_averages = get_league_averages(year)

    lgERA = float(league_averages['ERA'])
    lgHR = float(league_averages['HR'])
    lgBB = float(league_averages['BB'])
    lgHBP = float(league_averages['HBP'])
    lgK = float(league_averages['SO'])
    lgIP = float(league_averages['IP'])

    return lgERA - ((13 * lgHR) + (3 * (lgBB + lgHBP)) - (2 * lgK)) / (lgIP)


def get_fip_constant(year):
    """
    Retrieves the FIP constant from a FanGraphs page.
    """

    weightings = get_weightings(year)

    return float(weightings['cFIP'])


def get_weightings(year):
    """
    Takes in a year (str) and returns a list containing the necessary WOBA
    constants for that year.
    """

    url = 'http://www.fangraphs.com/guts.aspx?type=cn'
    soup = get_soup(url)

    headers = soup.find('a', text = 'Season').parent.parent
    correct_weightings = soup.find('td', text = year).parent

    def clean_soup(dirty_soup):
        """
        Takes in a soup element and returns a list of desired strings
        extracted from the soup code.
        """

        new_list = []

        for item in dirty_soup:
            new_list.append(item)

        new_list.pop(0)
        new_list.pop()
        final_list = []

        for item in new_list:
            final_list.append(item.get_text())

        return final_list

    header_list = clean_soup(headers)
    weightings_list = clean_soup(correct_weightings)

    weightings_dict = {}

    for header, weighting in zip(header_list, weightings_list):
        weightings_dict[header] = weighting

    return weightings_dict


def get_woba(stats, weightings):
    """
    Takes in a dict of statistics and a dict of WOBA weightings and calculates
    the batter's WOBA using the WOBA formula.
    """

    uBB = float(stats['BB']) - float(stats['IBB'])
    HBP = float(stats['HBP'])
    extra_bases = float(stats['2B']) + float(stats['3B']) + float(stats['HR'])
    singles = float(stats['H']) - extra_bases
    doubles = float(stats['2B'])
    triples = float(stats['3B'])
    HR = float(stats['HR'])
    AB = float(stats['AB'])
    SF = float(stats['SF'])

    wBB = float(weightings['wBB'])
    wHBP = float(weightings['wHBP'])
    w1B = float(weightings['w1B'])
    w2B = float(weightings['w2B'])
    w3B = float(weightings['w3B'])
    wHR = float(weightings['wHR'])

    numerator = ((wBB * uBB) + (wHBP * HBP) + (w1B * singles) +
                 (w2B * doubles) + (w3B * triples) + (wHR * HR))

    denominator = AB + uBB + SF + HBP

    return numerator / denominator
