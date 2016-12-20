import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

def calculate_fip(name, year):
    """
    Takes in the name (str) of a desired player and a desired year (str) and
    calculates that player's final FIP for that season.
    """

    player_url = ('http://www.espn.com/mlb/players?search={}&alltime=true&statusId=1'
    .format(name))

    try:
        soup = get_stats_soup(player_url)
    except AttributeError:
        return "No stats could be found for this player"
    except:
        raise

    stats = get_stats(soup, year)

    if stats:
        FIP = calculate_pure_fip(stats, year) + calculate_fip_constant(year)
        return ('%.2f' % FIP)
    else:
        return "No stats found for the given name and/or year"


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


def get_stats(soup, year):
    """
    Scrapes FanGraphs for the necessary basic pitching statistics to calculate
    FIP, xFIP, and SIERA.
    """

    tables = soup.find_all('table', attrs = {'class':'tablehead'})
    first_table = tables[0]
    last_table = tables[len(tables) - 1]

    def get_stats_for_desired_year(table, year):
        """
        Checks a table for the correct season and returns a list of stats for
        that season.
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
    extra_dict = get_stats_for_desired_year(last_table, year)

    stats_dict = dict(main_dict.items() + extra_dict.items())

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


def calculate_fip_constant(year):
    """
    Calculates the FIP constant.
    """

    pitching_url = ('http://www.espn.com/mlb/stats/team/_/stat/pitching/year/{}'
                    .format(year))
    batting_url = ('http://www.espn.com/mlb/stats/team/_/stat/batting/year/{}'
                   .format(year))
    exp_batting_url = (
    'http://www.espn.com/mlb/stats/team/_/stat/batting/year/{}/type/expanded'
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

    batting_stats = get_averages(batting_url)
    exp_batting_stats = get_averages(exp_batting_url)
    batting_dict = dict(batting_stats.items() + exp_batting_stats.items())
    pitching_dict = get_averages(pitching_url)

    lgERA = float(pitching_dict['ERA'])
    lgHR = float(batting_dict['HR'])
    lgBB = float(pitching_dict['BB'])
    lgHBP = float(batting_dict['HBP'])
    lgK = float(pitching_dict['SO'])
    lgIP = float(pitching_dict['IP'])

    return lgERA - ((13 * lgHR) + (3 * (lgBB + lgHBP)) - (2 * lgK)) / (lgIP)
