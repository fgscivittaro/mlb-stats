from util import *

def calculate_woba(name, year):
    """
    Takes in the name (str) of a desired player and a desired year (str) and
    calculates that player's WOBA for that season.
    """

    soup = convert_name_to_soup(name)

    if soup:
        stats = get_stats(soup, year)
    else:
        return "No stats found for the given player"

    if stats:
        weightings = get_weightings(year)
        wOBA = get_woba(stats, weightings)
        return ('%.2f' % wOBA)
    else:
        return "No stats found for the given year"
