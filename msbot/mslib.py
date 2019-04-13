import json
import requests
import msbot.settings
from msbot.spoiler import Spoiler

url_base = 'http://mythicspoilerapi.dungeonmastering.net/'


def getCardsBySet(setname):
    """
    :type setname: String
    :rtype: List[Spoiler]
    """
    url = url_base + 'APIv2/cards/by/set'
    payload = {'key': msbot.settings.API_KEY, 'param': setname}
    r = requests.get(url, params=payload)
    cards = json.loads(r.text[1:len(r.text)-1])['item']
    output = ''
    spoiler_list = []
    for card in cards:
        spoiler_list.append(Spoiler(card))
    return spoiler_list


def getLatestSpoilers():
    """
    :rtype: List[string]
    """
    url = url_base + 'APIv2/cards/by/spoils'
    payload = {'key': msbot.settings.API_KEY}
    try:
        r = requests.get(url, params=payload)
    except Exception as e:
        print('MythicSpoiler Connection Error')
    else:
        try:
            print(r.text)
            cards = json.loads(r.text[1:len(r.text)-1])['item']
        except ValueError:
            print('JSON error')
            return []
        else:
            output = ''
            url_list = []
            for card in cards:
                url_list.append(
                    url_base + 'card_images/new_spoils/' + card['cardUrl'])
            return url_list