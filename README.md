# API reversing tool

## <u>Name</u>

S A P h I R E (with an image)

**S**imple **API** **R**everse **E**ngineering



## <u>Description</u>

 Tool to assist reverse engineering of arbitrary API flows like Authentication protocols. Note that we only care about the tokens like ... Predictable Metadata like the `User-Agent` / `Content-type` headers or `?encoding=utf-8` params are ignored and the user can then manually add them to his requests



## <u>Usage</u>

```bash
$./saphire.py www.ratpack.gr.har 
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
Enter req/resp divider pct. (ENTER -> default=50%): 75
Divider set to 75
Request-info will span 153/204 chars. Responses start on 154
 _________________________________________________________________________________________________________________________________________________________ 
|        #0|20:27:48.93                                                                                                                                    |
|       GET|www.ratpack.gr /sports/story/4758/10-pragmata-poy-einai-kalytera-apo-toys-amyntikoys-tis-liverpoyl                                             |
|----------+-------------------------------------------------------------------------------------------------------------------------------------------... |
|    cookie|IN_HASH=ampshare%3Dhttp%3A%2F%2Fwww.ratpack.gr%2Fsports%2Fstory%2F4758%2F10-pragmata-poy-einai-kalytera-apo-toys-amyntikoys-tis-liverpoyl t... |
 _________________________________________________________________________________________________________________________________________________________ 


 _________________________________________________________________________________________________________________________________________________________ 
|        #1|20:27:48.31                                                                                                                                    |
|       GET|www.linkedin.com /analytics/                                                                                                                   |
|----------+-------------------------------------------------------------------------------------------------------------------------------------------... |
|       url|wt=framework type=widgetJSTracking trackingInfo=%7Bp%3A%7Bbl%3A2%2Cbe%3A3%2Cfl%3A1926%7D%7D trk=cws-fwk-anonymous 1509395268315= or=http%3A... |
|    cookie|bscookie="v=1&20170103174718edc72a8e-4b42-48f6-81aa-d6f1f680028aAQFq5m_7Ny5W7IYK1dUALXY36YYFaeBC" wutan=1PaUAiICdum7s0CjuL3Mcx5sjL9vAIZn96P... |
 _________________________________________________________________________________________________________________________________________________________ 


 _________________________________________________________________________________________________________________________________________________________ 
|        #2|20:27:48.32                                                                                                                                    |
|      POST|zdwidget3-bs.sphereup.com /zoomd/SearchUi/GetToken                                                                                             |
|----------+-------------------------------------------------------------------------------------------------------------------------------------------... |
 _________________________________________________________________________________________________________________________________________________________ 


 _________________________________________________________________________________________________________________________________________________________ 
|        #3|20:27:48.34                                                                                                                                    |
|      POST|zdwidget3-bs.sphereup.com /zoomd/SearchUi/GetToken                                                                                             |
|----------+-------------------------------------------------------------------------------------------------------------------------------------------... |
 _________________________________________________________________________________________________________________________________________________________ 


 _________________________________________________________________________________________________________________________________________________________ 
|        #4|20:27:48.34                                                                                                                                    |
|      POST|zdwidget3-bs.sphereup.com /zoomd/SearchUi/GetToken                                                                                             |
|----------+-------------------------------------------------------------------------------------------------------------------------------------------... |
 _________________________________________________________________________________________________________________________________________________________ 


 _________________________________________________________________________________________________________________________________________________________ 
|        #6|20:27:48.74                                                                                                                                    |
|      POST|prod-sb-appanalytics-us1.servicebus.windows.net /usagelogs/messages                                                                            |
|----------+-------------------------------------------------------------------------------------------------------------------------------------------... |
|req_header|authorization=sharedaccesssignature sr=prod-sb-appanalytics-us1.servicebus.windows.net&sig=s7oq%2bzxzybtltv3sx%2f0kfabj9wfer1miocznsmwwcm4%... |
 _________________________________________________________________________________________________________________________________________________________ 


 _________________________________________________________________________________________________________________________________________________________ 
|        #7|20:27:49.13                                                                                                                                    |
|       GET|fonts.googleapis.com /css                                                                                                                      |
|----------+-------------------------------------------------------------------------------------------------------------------------------------------... |
|       url|family=Roboto:100,100i,300,300i,400,400i,500,500i,700,700i,900,900i subset=greek,greek-ext                                                     |
|req_header|x-chrome-uma-enabled=1 x-client-data=cje2yqeipbbjaqilmmobcpqcygeiqz3kaqjsncobcnueygeiqkpkaq==                                                  |
 _________________________________________________________________________________________________________________________________________________________ 

```











## Intended Usage

* Need to work despite HTTPS / Cert pinning so
* ***Chrome extension*** 
* so lang=JS
* Click ext -> Start recording -> <do flow> -> click ext -> Stop recording -> Draw in dialog and offer to Save files





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