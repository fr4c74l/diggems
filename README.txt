To have this fully working, you will need an implementation of
 Basic HTTP Push Relay Protocol
(http://pushmodule.slact.net/protocol.html) running in the same
host, serving subscribers on http://localhost/event?id=<channel_id>
and publisher on http://localhost/ctrl_event?id=<channel_id>

I am using NGiNX_HTTP_Push_Module, found in
http://pushmodule.slact.net/
