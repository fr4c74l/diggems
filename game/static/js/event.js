function Event(channel_url) {
    this.url = channel_url;
    this.handlers = {};
    this.stopped = false;
    this.error_count = 0;
    this.send_queue = [];
    this._is_sent_scheduled = false;

    this._reconnect_timer = null;

    this._build_socket();
}

Event.parser = /^(.)\n(\d+)\n([^]*)/;

Event.prototype._callback = function(ev) {
    var parsed = ev.data.match(Event.parser);
    var handler_key = parsed[1];
    var seqnum = parseInt(parsed[2]);
    var handler = this.handlers[handler_key];

    // The conditional logic is inverted for the case where
    // this.last_seqnum is undefined: the message must be processed.
    if(handler && !(seqnum <= handler.last_seqnum)) {
	var msg = parsed[3];
	handler.call(msg);
	handler.last_seqnum = seqnum;
    }
};

Event.prototype._do_reconnect = function() {
    this._reconnect_timer = null;
    this._build_socket();
}

Event.prototype._on_problem = function() {
    if (this.socket) {
	this.socket.close();
	this.socket = null;
    }
    
    if (!this.stopped && this._reconnect_timer === null) {
	/* We should not have stopped, so try to reconnect, but
	 * do not enter into tight loop trying to do so. */
	this.error_count = Math.min(this.error_count + 1, 10);

	if(this.error_count > 1) {
	    var delay = (this.error_count - 1) * 500;
	    this.socket = null;
	    this._reconnect_timer = setTimeout(this._do_reconnect.bind(this), delay);
	} else
	    this._build_socket();
    }
};

Event.prototype._on_connect = function() {
    // Upon successful connection, error count can be reset...
    this.error_count = 0;

    // Send the last_seqnum for every message type:
    var seqnums = {};
    for (id in this.handlers) {
	seqnums[id] = this.handlers[id].last_seqnum;
    }
    this.socket.send(JSON.stringify(seqnums));

    // Send any pending message
    this._do_send();
}

Event.prototype.send = function(msg_type, msg) {
    msg = msg_type + '\n' + msg;
    this.send_queue.push(msg);
    this._do_send();
};

Event.prototype._scheduled_send = function() {
    this._is_sent_scheduled = false;
    this._do_send();
}

Event.prototype._schedule_send_later = function() {
    if (!this._is_sent_scheduled) {
	this._is_sent_scheduled = true;
	setTimeout(this._scheduled_send.bind(this), 50);
    }
}

Event.prototype._do_send = function() {
    while (this.send_queue.length) {
	var msg = this.send_queue[0];

	if (!this.socket || this.socket.readyState > 1) {
	    // Reconnect...
	    clearTimeout(this._reconnect_timer);
	    this._build_socket();
	} else if (this.socket.readyState == 0) {
	    return;
	} else if (this.socket.bufferedAmount == 0 || (this.socket.bufferedAmount + msg.length) < 4096) {
	    // Shitty WebSockt doesn't have a way to tell the maximum size of
	    // the send buffer, so I will just assume it is of 4k size...
	    // Also, I can never be sure it was actually sent, but whatever...
	    this.socket.send(msg);
	    this.send_queue.shift();
	} else {
	    // Buffer too full, scheduled to retry later.
	    this._schedule_send_later();
	    return;
	}
    }
}

Event.prototype._build_socket = function() {
    if (this._reconnect_timer) {
	clearTimeout(this._reconnect_timer);
	this._reconnect_timer = null;
	this.error_count = Math.max(this.error_count - 1, 0);
    }

    this.socket = new WebSocket(this.url);
    this.socket.onmessage = this._callback.bind(this);

    this.socket.onopen = this._on_connect.bind(this);

    var error_handler = this._on_problem.bind(this);
    this.socket.onerror = error_handler;
    this.socket.onclose = error_handler;
};

Event.prototype.register_handler = function(id, func, last_seqnum) {
    this.handlers[id] = {'call': func, 'last_seqnum': last_seqnum};
};

Event.prototype.stop = function() {
    this.stopped = true;
    clearTimeout(this._reconnect_timer);
    if (this.socket) {
	this.socket.close();
    }
};
