"""isort:skip_file"""
import asks
import lxml.html

from prop import Promise
from asyncio import get_event_loop

loop = get_event_loop()

p = (
    Promise(asks.get("https://en.wikipedia.org/wiki/Main_Page"), loop=loop)
    .then(
        lambda response: lxml.html.fromstring(response.text).xpath(
            '//*[contains(text(), "Did you know...")]/../following-sibling::*/ul//li'
        )
    )
    .catch(
        # In case the request fails or lxml can't parse the response, continues with empty list
        lambda _: []
    )
    .then(lambda lis: "\n".join(("Did you know:", *(li.text_content() for li in lis))))
    .then(print)
)

loop.run_until_complete(p)
