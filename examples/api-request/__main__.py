import lxml.html
import asks
from prop import Promise
from asyncio import get_event_loop

loop = get_event_loop()

p = Promise(asks.get("https://en.wikipedia.org/wiki/Main_Page"), loop=loop) \
        .then(lambda response: lxml.html.fromstring(response.text).getroot()) \
        .then(lambda doc_root: doc_rooot.xpath('//*[contains(test(), "Did you know...")]/../following-sibling::*//li')) \
        .then(print) \
        .catch(print)

loop.run_until_complete(p)