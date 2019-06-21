# Internal
from asyncio import get_event_loop

# External
import lxml.html

# External
import asks
from prop import Promise

loop = get_event_loop()

p = (
    Promise(asks.get("https://en.wikipedia.org/wiki/Main_Page"), loop=loop)
    .then(lambda response: lxml.html.fromstring(response.text))
    .then(
        lambda doc_root: doc_root.xpath(
            '//*[contains(text(), "Did you know...")]/../following-sibling::*/ul//li'
        )
    )
    .catch(lambda _: [])
    .then(lambda lis: "\n".join(li.text_content() for li in lis))
    .then(lambda text: "Did you know:\n" + text)
    .then(print)
)

loop.run_until_complete(p)
