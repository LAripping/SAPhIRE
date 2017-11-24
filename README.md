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

<a href="https://asciinema.org/a/7mgi3oTOy1M0SaVI0uNFnV0bw?autoplay=1" target="_blank"><img src="https://asciinema.org/a/7mgi3oTOy1M0SaVI0uNFnV0bw.png" /></a>




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
