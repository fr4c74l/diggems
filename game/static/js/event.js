function Event(channel_url, last_known_change) {
    this.url = channel_url;
    this.last_etag = null;
    this.last_change = null;
    this.request = new XMLHttpRequest();
    this.error_count = 0;
    this.handlers = {};
    
    this._timer = null;

    this._register_event();
}

Event.prototype._callback = function() {
	if (this.request.readyState == 4) {
	    if(this.request.status == 200) {
		this.error_count = 0;
		this.last_etag = this.request.getResponseHeader('Etag');
		this.last_change = this.request.getResponseHeader('Last-Modified');

                var data = this.request.responseText;
                // TODO: assert charAt(1) is '\n'
		this.handlers(data.charAt(0))(this.request.responseText.slice(2));
		this._register_event();
	    }
	    else {
		// If this is the first error, try again right away
		// If not, delay some time before trying again
		if(this.error_count)
		    this.error_count = Math.min(this.error_count + 1, 10);
		else
		    this.error_count = 1;

		if(this.error_count > 1) {
		    var delay = (this.error_count - 1) * 500;
		    this._timer = setTimeout(this._register_event, delay);
		}
		else
		    this._register_event();
	    }
	}
};

Event.prototype._register_event = function() {
        this.request.open('GET', this.url, true);
        if(this.last_etag)
            this.request.setRequestHeader('If-None-Match', this.last_etag);
        if (this.last_change)
            this.request.setRequestHeader('If-Modified-Since', this.last_change);
        this.request.onreadystatechange = this._callback.bind(this);
        this.request.send(null);
};

Event.prototype.register_handler = function(id, func) {
    this.handlers[id] = func;
};

Event.prototype.stop = function() {
    clearTimeout(this._timer);
    this.request.abort();
};
