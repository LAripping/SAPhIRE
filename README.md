<img src="http://icons.iconarchive.com/icons/aha-soft/jewelry/128/Sapphire-icon.png" align="right"/>

# S A P h I R E

_**S**imple **API** **R**everse **E**ngineering **h**elper_

>  *Never again shall one be limited by HTTPS / SSL-pinning* 		
>
>  [--John Lock](https://i.ytimg.com/vi/f3KwdmzHapI/maxresdefault.jpg)





## <u>Rationale</u>

S A P h I R E is a tool to assist reverse engineering of arbitrary API flows seen in the wild. Flows like Authentication protocols which are often proprietary, undocumented, stuffed with minified JS rendering them completely obfuscated.

A trained eye will see the business logic being implemented but the volume of data is sometimes exceeding.

So SAPhIRE (yes, I cheated on the name) Isolates "tokens" like Cookies / Headers / URL parameters / Form fields and highlight them to make the underlying logic obvious. Note that we only care about non-standard tokens like uncommon Headers (e.g. not `Accept` / `Content-type` ) headers or `?encoding=utf-8` params.

It's still a **WIP** and very pre-mature but as you can see from the demo execution below, basic functionality and primitive output printing do work.



## <u>Usage</u>

First manually carry out the flow (assumed Chrome): Open Dev Tools -> `Network` -> Check `Preserve Log`, clear it and... -> ( do the flow ) -> Right click -> `Save as HAR with content`. Then:

```bash
./saphire.py www.ratpack.gr.har 
[+] Read 8 entries
Filter by domain? (ENTER for no): ratpack.gr
Ignore media/fonts/css/... junk? (Y/n): 
[+] 8 Entries in for token recognition
[+] Read in 94 common headers to ignore
[+] Recognized 16 tokens in req with time 807.327999999
[+] Recognized 22 tokens in req with time 247.620660999
[+] Recognized 1 tokens in req with time 14.2885690006
[+] Recognized 1 tokens in req with time 0.592000000936
[+] Recognized 6 tokens in req with time 188.6017
[+] Recognized 0 tokens in req with time 196.678657999
[+] Recognized 4 tokens in req with time 166.731935
[+] Recognized 6 tokens in req with time 788.225202
Print 10 random tokens?(y/N): 
Enter req/resp divider pct. (ENTER -> default=50%): 
Request-info will span 116/232 chars. Responses start on 117
 ____________________________________________________________________________________________________________________ 
|         #0|20:27:48.93                                                                                             |
|        GET|www.ratpack.gr /sports/story/4758/10-pragmata-poy-einai-kalytera-apo-toys-amyntikoys-tis-liverpoyl      |
| ----------+----------------------------------------------------------------------------------------------------... |
|     cookie|IN_HASH=ampshare%3Dhttp%3A%2F%2Fwww.ratpack.gr%2Fsports%2Fstory%2F4758%2F10-pragmata-poy-einai-kalyt... |
 ____________________________________________________________________________________________________________________ 
                                                                                                                       ________________________________________________________________________________________________________________ 
                                                                                                                     |   200 OK                                                                                                        |
                                                                                                                     |  -----------------------------------------------------------------------------------------------------------... |
                                                                                                                     |  resp_header|x-powered-by=php/5.6.26 x-micro-cache=hit                                                          |
                                                                                                                       ________________________________________________________________________________________________________________ 


 ____________________________________________________________________________________________________________________ 
|         #1|20:27:48.31                                                                                             |
|        GET|www.linkedin.com /analytics/                                                                            |
| ----------+----------------------------------------------------------------------------------------------------... |
|        url|wt=framework type=widgetJSTracking trackingInfo=%7Bp%3A%7Bbl%3A2%2Cbe%3A3%2Cfl%3A1926%7D%7D trk=cws-... |
|     cookie|bscookie="v=1&20170103174718edc72a8e-4b42-48f6-81aa-d6f1f680028aAQFq5m_7Ny5W7IYK1dUALXY36YYFaeBC" wu... |
 ____________________________________________________________________________________________________________________ 
                                                                                                                       ________________________________________________________________________________________________________________ 
                                                                                                                     |   200                                                                                                           |
                                                                                                                     |  -----------------------------------------------------------------------------------------------------------... |
                                                                                                                     |  resp_header|x-li-uuid=ueuungbz8hrafmawqisaaa== x-li-pop=prod-idb2 x-li-proto=http/2 x-li-fabric=prod-lva1      |
                                                                                                                       ________________________________________________________________________________________________________________ 


 ____________________________________________________________________________________________________________________ 
|         #2|20:27:48.32                                                                                             |
|       POST|zdwidget3-bs.sphereup.com /zoomd/SearchUi/GetToken                                                      |
| ----------+----------------------------------------------------------------------------------------------------... |
 ____________________________________________________________________________________________________________________ 
                                                                                                                       ________________________________________________________________________________________________________________ 
                                                                                                                     |   307 Internal Redirect                                                                                         |
                                                                                                                     |  -----------------------------------------------------------------------------------------------------------... |
                                                                                                                     |  resp_header|non-authoritative-reason=delegate                                                                  |
                                                                                                                       ________________________________________________________________________________________________________________ 


 ____________________________________________________________________________________________________________________ 
|         #3|20:27:48.34                                                                                             |
|       POST|zdwidget3-bs.sphereup.com /zoomd/SearchUi/GetToken                                                      |
| ----------+----------------------------------------------------------------------------------------------------... |
 ____________________________________________________________________________________________________________________ 
                                                                                                                       ________________________________________________________________________________________________________________ 
                                                                                                                     |   307 Internal Redirect                                                                                         |
                                                                                                                     |  -----------------------------------------------------------------------------------------------------------... |
                                                                                                                     |  resp_header|non-authoritative-reason=delegate                                                                  |
                                                                                                                       ________________________________________________________________________________________________________________ 


 ____________________________________________________________________________________________________________________ 
|         #4|20:27:48.34                                                                                             |
|       POST|zdwidget3-bs.sphereup.com /zoomd/SearchUi/GetToken                                                      |
| ----------+----------------------------------------------------------------------------------------------------... |
 ____________________________________________________________________________________________________________________ 
                                                                                                                       ________________________________________________________________________________________________________________ 
                                                                                                                     |   200 OK                                                                                                        |
                                                                                                                     |  -----------------------------------------------------------------------------------------------------------... |
                                                                                                                     |  resp_header|x-aspnetmvc-version=5.2 x-aspnet-version=4.0.30319 x-powered-by=asp.net p3p=cp="idc dsp cor adm... |
                                                                                                                       ________________________________________________________________________________________________________________ 


 ____________________________________________________________________________________________________________________ 
|         #6|20:27:48.74                                                                                             |
|       POST|prod-sb-appanalytics-us1.servicebus.windows.net /usagelogs/messages                                     |
| ----------+----------------------------------------------------------------------------------------------------... |
| req_header|authorization=sharedaccesssignature sr=prod-sb-appanalytics-us1.servicebus.windows.net&sig=s7oq%2bzx... |
 ____________________________________________________________________________________________________________________ 
                                                                                                                       ________________________________________________________________________________________________________________ 
                                                                                                                     |   201 Created                                                                                                   |
                                                                                                                     |  -----------------------------------------------------------------------------------------------------------... |
                                                                                                                       ________________________________________________________________________________________________________________ 


 ____________________________________________________________________________________________________________________ 
|         #7|20:27:49.13                                                                                             |
|        GET|fonts.googleapis.com /css                                                                               |
| ----------+----------------------------------------------------------------------------------------------------... |
|        url|family=Roboto:100,100i,300,300i,400,400i,500,500i,700,700i,900,900i subset=greek,greek-ext              |
| req_header|x-chrome-uma-enabled=1 x-client-data=cje2yqeipbbjaqilmmobcpqcygeiqz3kaqjsncobcnueygeiqkpkaq==           |
 ____________________________________________________________________________________________________________________ 
                                                                                                                       ________________________________________________________________________________________________________________ 
                                                                                                                     |   200                                                                                                           |
                                                                                                                     |  -----------------------------------------------------------------------------------------------------------... |
                                                                                                                     |  resp_header|link=<https://fonts.gstatic.com>; rel=preconnect; crossorigin alt-svc=quic=":443"; ma=2592000; ... |
                                                                                                                       ________________________________________________________________________________________________________________ 



```



## <u>TODOs</u>

- [ ] Flow-print with colors
- [ ] Flow-graph w. GUI lib (`matplotlib`?)





#### **Behold** 

from this point and on the README contains random notes and scraps from the development. So that's it! Read no more.











## Intended Usage

* Need to work despite HTTPS / Cert pinning so
* ***Chrome extension*** 
* so lang=JS

  ​





- [ ] permission to read Reqs/Resps? 

      ​

 * If not ***HAR parser***.    
 * Click Dev Tools -> Network -> <do flow> -> Right click -> Save as HAR with content. 
 * HARs are just a json files
* so lang=Python
* Display flow in terminal , if flag draw in ext file , save all








## Internals


* isolate Reqs / Resps 

* Filter by domains

* Ignore data (styles / fonts / media / images / `data:` urls)

* Recognize important tokens:

  * URL parameters (`entry[request][querysting][0][name]`)
  * Form fields (all types)
  * Cookies
  * important Headers  (non-std)
  * Plain JSON in Resp bodies 
  * HTML scrape form input fields in Resp bodies

* Decode tokens 

  * base64
  * gzip
  * url-decode
  * html-decode
  * hex
  * ascii hex

  recursive

  [Smart decoding](https://portswigger.net/burp/help/decoder.html) 

* Output: Required Reqs, for each


  * Method
  * URL
  * tokens

* Graph with colored tokens throughout the flow (Left2Right / Top2Bottom)









## Debugging

Use https://toolbox.googleapps.com/apps/har_analyzer/ and  [this .har](gameboard.pentestcyprus.org.har) 

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