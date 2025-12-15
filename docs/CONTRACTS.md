\# GEO-ADS — Contracts



\## HTTP

\- GET /advertisements

&nbsp; -> \[ { id:int, name:str, image\_url:str|null, zone:str } ]



\- GET /layout

&nbsp; -> Zone\[] (in-memory)



\- POST /placements/recommend\_and\_assign/advertisements/{ad\_id}?x=\&y=\&radius=

&nbsp; -> AdPlacement



AdPlacement:

{

&nbsp; ad\_id: int,

&nbsp; screen\_id: str,

&nbsp; zone\_id: str,

&nbsp; x: float,

&nbsp; y: float,

&nbsp; screen\_type?: str|null,

&nbsp; ad\_category?: str|null,

&nbsp; time\_window?: str|null,

&nbsp; assigned\_at: iso-datetime

}



\## WebSockets

\- WS /ws/ads

&nbsp; Server -> client:

&nbsp; { v:1, type:"ads\_list", data: Advertisement\[] }



\- WS /ws/placements

&nbsp; Server -> client (on connect):

&nbsp; { v:1, type:"placements\_snapshot", data: AdPlacement\[] }



&nbsp; Server -> client (on assign):

&nbsp; { v:1, type:"placement\_assigned", data: AdPlacement }



