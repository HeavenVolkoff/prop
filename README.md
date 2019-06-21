# Prop

![alt text](https://img.shields.io/badge/HeavenVolkoff/prop-black.svg?style=for-the-badge&logo=github "Project Badge")
![alt text](https://img.shields.io/github/tag/HeavenVolkoff/prop.svg?label=version&style=for-the-badge "Version Badge")
![alt test](https://img.shields.io/github/license/HeavenVolkoff/prop.svg?style=for-the-badge "License Badge")

Promises with opinions for asyncio and Python 3.6+

> This is a revitalization of a promise submodule previously included in another project of mine: [aRx](https://github.com/HeavenVolkoff/aRx). For older revisions of the code check there.

## Summary

+ [docs](./docs):
    > Folder containing project's documentation
+ [src](./src):
    > Folder containing project's source code
+ [tests](./tests):
    > Folder containing project's unit tests
+ [tools](./tools):
    > Folder containing tools for formatting and organizing the code

## Examples

```python
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
```


## Installation

> Comming soon...

## License

All of the source code in this repository is available under the Mozilla Public License 2.0 (MPL).
Those that require reproduction of the license text in the distribution are given [here](./LICENSE.md).

## Copyright

    Copyright (c) 2018 Vítor Augusto da Silva Vasconcellos. All rights reserved.
