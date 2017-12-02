<img src="http://icons.iconarchive.com/icons/aha-soft/jewelry/128/Sapphire-icon.png" align="right"/>

# S A P h I R E

_**S**imple **API** **R**everse **E**ngineering **h**elper_



## Rationale

S A P h I R E is a tool to assist reverse engineering of arbitrary API flows seen in the wild. Flows like Authentication protocols which are often proprietary, undocumented and stuffed with minified JS rendering them completely obfuscated.

It Isolates "tokens" like 

* Cookies
* Headers
* URL parameters
* Form fields 

...and highlight them to make the underlying logic obvious. 



## Selling Points

- [x] **Auto-decodes tokens** (html/url) to spare the reverser of these easy but tiring chores
- [x] **Ignores standard tokens** like [common Headers](/common_headers.txt) (e.g.  `Accept` / `Content-type` ) headers or `?encoding=utf-8` params.
- [x] **Filters out irrelevant requests && Ignores media/junk/...** with prompts at runtime.


- [x] **Highlights common tokens** with common colors : The ones repeated throughout the (massive) flows

      Although in a manual examination, a trained eye will see the business logic being implemented, the volume of data is sometimes too much for a human to connect the dots

      *Bonus: Configurable colors*

- [x] **Extracts the flow from the browser**: in HAR files, see Usage below.

      No need for MITM proxies / network sniffing to capture the flow. 

      No more certificate installing, pinning-bypasses.



## Usage

First manually carry out the flow (assumed Chrome): Open Dev Tools -> `Network` -> Check `Preserve Log`, clear it and... -> ( do the flow ) -> Right click -> `Save as HAR with content`. Then:

<a href="https://asciinema.org/a/WNwagDpjbWv0DS8o0GIpEmEsc?autoplay=1" target="_blank"><img src="https://asciinema.org/a/ykIH6IrDNe7V1lXMdfcUv3dQh.png" /></a>



### Options
`-c, --color` Determines the way the tokens will be colored (meaningful only in flow_print mode) Possible Values:
0. ` off` no funky colors and stuff

1. `by-type` rather dumb, fuzz around the colors for each type, no affiliation

2. `try-match` *the suggested and default mode*, Color every token that occurs more than once, all-occurancies with the same color!

3. `try-match-all` can't live without colors? Color every token and same ones get the same color.

   ​


`-x, --expand` Specify how to spread the different tokens of each category (meaningful only in flow_print mode) Possible Values:

* `h` for Horizontal expansion. This will lead to a summarized view focusing more on the flow . like: 

```

 ____________________________________________________________________________________________________________________
|         #4|18:53:43.42                                                                                             |
|        GET|akispetretzikis.com /xtcore.js                                                                          |
| ----------+----------------------------------------------------------------------------------------------------... |
|     cookie|__atuvc=1|48 __atuvs=5a1b0d78ddce9c96000 xtvrn=$568522$ cookies_accept=1 _eproductions.gr_session=BA... |
 ____________________________________________________________________________________________________________________
 


```

* `v` for Vertical expansion, *the default view*. Now we see the tokens in detail occupying more screen real estate per-request. 

```
 _____________________________________________________________________
|       #160|20:15:48.27                                              |
|        GET|cdn.syndication.twimg.com /widgets/timelines/44954441... |
| ----------+-----------------------------------------------------... |
|        url|callback=__twttr.callbacks.tl_i0_449544415724326914_ol... |
|           |dnt=false                                       |
|           |domain=akispetretzikis.com                      |
|           |lang=en                                         |
|           |suppress_response_codes=true                    |
|           |t=1679889                                                |
|           |tz=GMT+0200                                              |
|     cookie|lang=en                                         |
 _____________________________________________________________________
                                                                       __________________________________________________________________
                                                                      |  200                                                             |
                                                                      | -------------------------------------------------------------... |
                                                                      | rsp_header|x-cache=MISS                                          |
                                                                      |           |x-served-by=cache-tw-par1-2-TWPAR1           |
                                                                      |           |x-response-time=247                                   |
                                                                      |           |x-timer=S1511900149.759974,VS0,VE258                  |
                                                                      |           |x-connection-hash=c043173fd3fa017e6d127140aa898aa6... |
                                                                       __________________________________________________________________



```






## TODOs

- [x] Flow-print with colors

- [ ] smart decoding: url / html / ~~base64~~ / ~~gzip~~ 

- [ ] tokens from: scraping  `<input type=hidden value>` from html

- [ ] ignore junk tokens (like locale, encoding, lang)

- [ ] Flow-graph w. GUI lib ( `matplotlib` / `pyqt` / ... ?)

- [ ] Prepare Release:

      * Installation directives 
        * `pip install -r requirements` if any external modules
        * write functions of termcolor I used in separate file and eliminate external dependancies (since that's the only one!), after-all I already have one termcolor-related but not included


      * Write a Use Case section with a flow that is revealed. Must highlight most of:
        * smart decoding 
        * tokens leading to curl- ing

      * "Fuzz" cmd line parameters and inputs as manual testing

      * explain common-headers trick

      * explain why smart decoding can't work:

        * When to stop? -> When is it a valid word? 
        * Arbitrary schemes could be used, prefer manual (out of the "low-hanging fruit" mentality of the tool)

        ​

      ​


## Gotchas
* UTF8 will probably result in sth ugly...







## Debugging

Use https://toolbox.googleapps.com/apps/har_analyzer/ for a tool as close as the Browser's Dev. Tab (after closing it)

Included example .har files

Flow to highlight (required): (couldn't verify)

1. ```http
   GET - https://gameboard.pentestcyprus.org/login
   ```

   ```http
   200 OK
   Set-Cookie: XSRF-TOKEN=zkfyWcef2k4FE9G9nvYgnX1V-Nyp7A55KlK7cvJyEWN41ZDC; Path=/
   ```

   ​


2. ```http
   POST - https://gameboard.pentestcyprus.org/api/session
   Cookie: XSRF-TOKEN=xkHyWUII2A8AH8B_aWKZxyluCrthK8SOGhal5YCWoL9VdFVk
   XSRF-TOKEN: xkHyWUII2A8AH8B_aWKZxyluCrthK8SOGhal5YCWoL9VdFVk

   {"email":"leo.tsaou@gmail.com","password":"t4nTjmew%p2J"}
   ```

   ```http
   200 OK
   Set-Cookie: session=eyJhZG1pbiI6ZmFsc2UsImV4cGlyZXMiOjE1MDg5NjYwMjksInRlYW0iOjU1LCJ1c2VyIjo1Nn0.DNKB_Q.9Uo78wftOMJ7367H5acwsZVRa3Q

   {
     "redirect": null,
     "user": {
       "uid": 56,
       "admin": false,
       "email": "leo.tsaou@gmail.com",
       "nick": "LAripping",
       "registrationToken": "842015666",
       "team_tid": 55
     },
     "team": {
       "tid": 55,
       "score": 2392,
       "name": "LAripping",
       "code": "866b726b1e45"
     }
   }
   ```

   ​
