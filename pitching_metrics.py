from util import *

def calculate_fip(name, year):
    """
    Takes in the name (str) of a desired player and a desired year (str) and
    calculates that player's final FIP for that season.
    """

    soup = convert_name_to_soup(name)

    if soup:
        stats = get_stats(soup, year)
    else:
        return "No stats found for the given player"

    if stats:
        FIP = calculate_pure_fip(stats, year) + calculate_fip_constant(year)
        return ('%.2f' % FIP)
    else:
        return "No stats found for the given year"


def calculate_xfip(name, year):
    """
    Takes in the name (str) of a desired player and a desired year (str) and
    calculates that player's final xFIP for that season.
    """

    soup = convert_name_to_soup(name)

    if soup:
        stats = get_stats(soup, year)
    else:
        return "No stats found for the given player"

    if stats:
        xFIP = calculate_pure_xfip(stats, year) + calculate_fip_constant(year)
        return ('%.2f' % xFIP)
    else:
        return "No stats found for the given year"


def calculate_siera(name, year):
    """
    """

    return []
