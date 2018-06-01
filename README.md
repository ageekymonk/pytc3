# Pytc3 [WIP]
**This is not production Ready yet.**
[![Latest Version](https://badge.fury.io/py/pytc3.svg)](https://pypi.python.org/pypi/pytc3/)
[![Travis CI Build Status](https://travis-ci.org/ageekymonk/pytc3.svg?branch=master)](https://travis-ci.org/ageekymonk/pytc3)

Python interface to the [REST
API](https://confluence.jetbrains.com/display/TCD10/REST+API) of
[TeamCity](https://www.jetbrains.com/teamcity/)

## Installation

```
pip install pytc3
```

## Examples

### Connect to server

```python
from pytc3 import TeamCity

# This initialises the Client with the settings passed. <port> has to be an integer.
tc = TeamCity('account', 'password', 'server', <port>)
```

or specify no parameters and it will read settings from environment
variables:

- `TEAMCITY_USER`
- `TEAMCITY_PASSWORD`
- `TEAMCITY_HOST`
- `TEAMCITY_PORT` (Defaults to 80 if not set)

```python
from pytc3 import TeamCity

# Initialises with environment variables: TEAMCITY_{USER,PASSWORD,HOST,PORT}
tc = TeamCity()
```

### Getting data

You can also look at
[sample.py](https://github.com/ageekymonk/pytc3/blob/master/sample.py)

## Acknowledgements

This is a heavily-modified fork of https://github.com/SurveyMonkey/pyteamcity so many thanks are due to [SurveyMonkey](https://github.com/SurveyMonkey)
