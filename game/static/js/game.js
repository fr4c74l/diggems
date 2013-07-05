// Copyright 2011 Lucas Clemente Vella
// Software distributed under Affero GPL, see http://gnu.org/licenses/agpl.txt

var ctx;
var mine;
var move_request = new XMLHttpRequest();
var event_request = new XMLHttpRequest();

var images = {};

var nt = window.webkitNotifications;
var last_nt;

function LastClick(m, n, player, bombed) {
    this.m = m;
    this.n = n;
    this.tile = mine[m][n];
    this.player = player;
    this.bombed = bombed;
    if(bombed) {
	this.min_x = Math.max(0, m - 2);
	this.size_x = Math.min(15, m + 2) - this.min_x + 1;
	this.min_y = Math.max(0, n - 2);
	this.size_y = Math.min(15, n + 2) - this.min_y + 1;
    }
}

LastClick.prototype.draw = function() {
    var MARK_COLOR = [
	'rgb(255,0,0)',
	'rgb(0,0,255)'
    ];

    ctx.strokeStyle = MARK_COLOR[this.player-1];
    if(this.bombed) {
	ctx.strokeRect(this.min_x*26 + 2, this.min_y*26 + 2,
		       this.size_x*26 - 5, this.size_y*26 - 5);
    } else {
	ctx.strokeRect(this.tile.x + 2, this.tile.y + 2, 21, 21);
    }
}

LastClick.prototype.clear = function() {
    if(this.bombed) {
	for(var i = 0; i < this.size_x; ++i) {
	    mine[this.min_x + i][this.min_y].draw();
	    mine[this.min_x + i][this.min_y + this.size_y - 1].draw();
	}
	for(var i = 1; i < (this.size_y - 1); ++i) {
	    mine[this.min_x][this.min_y + i].draw();
	    mine[this.min_x + this.size_x - 1][this.min_y + i].draw();
	}
    } else {
	this.tile.draw();
    }
}

function last_click_decode(player, encoded) {
    var bombed;
    var v = [];

    bombed = encoded.charAt(0) == 'b';
    for(var j = 1; j < 3; ++j)
    	v[j-1] = parseInt(encoded.charAt(j), 16);

    return new LastClick(v[0], v[1], player, bombed);
}

var last_click = [null, null];

// T.N.T. stuff:
var tnt = {
    'allowed': false,
    'active': false
};

/* Configure T.N.T. display according to state. */
function display_tnt() {
    var obj = document.getElementById('tnt');
    if (!obj) {
	return;
    }
    if(tnt.allowed && !params.tnt_used) {
	obj.src = images['tnt'].src;
	if (params.player == params.state) {
	    obj.className = tnt.active ? 'tntbtn in' : 'tntbtn out';
	} else {
	    obj.className = '';
	}
    } else {
	obj.src = images[params.tnt_used ? 'explosion' : 'crate'].src;
	obj.className = '';
    }
}

function toggle_tnt(ev) {
    var button = document.getElementById('tnt');

    if(params.tnt_used || !tnt.allowed) {
	tnt.active = false;
    } else {
	// TODO: marker over the T.N.T. area.
	if(!tnt.active) {
	    tnt.active = true;
	}
	else {
	    tnt.active = false;
	}
    }

    display_tnt();
}

// Class Tile
function Tile(x0,y0) {
  this.s = '?';
  this.x = x0 * 26;
  this.y = y0 * 26;
}

Tile.prototype.draw = function() {
    var TEXT_COLOR = [
	'rgb(0,0,255)',
	'rgb(0,160,0)',
	'rgb(255,0,0)',
	'rgb(0,0,127)',
	'rgb(160,0,0)',
	'rgb(0,255,255)',
	'rgb(160,,160)',
	'rgb(0,0,0)'
    ];

    if(this.s >= 0 && this.s <= 8) {
	ctx.fillStyle = 'rgb(255,216,161)';
	ctx.fillRect(this.x, this.y, 25, 25);
	if(this.s > 0) {
	    ctx.fillStyle = TEXT_COLOR[this.s-1];
	    ctx.fillText(this.s, this.x + 12.5, this.y + 12.5);
	}
    }
    else if(this.s == 'r' || this.s == 'b') {
	ctx.fillStyle = 'rgb(251,170,56)';
	ctx.fillRect(this.x, this.y, 25, 25);
	var icon = images[(this.s == 'b') ? 'saphire' : 'ruby'];
	ctx.drawImage(icon, this.x + 2, this.y + 5);
    }
    else {
	ctx.fillStyle = 'rgb(227,133,0)';
	ctx.fillRect(this.x, this.y, 25, 25);

	if(this.s == 'x') {
	    var icon = images[(params.state == 3) ? 'ruby' : 'saphire'];
	    ctx.globalCompositeOperation = 'lighter';
	    ctx.drawImage(icon, this.x + 2, this.y + 5);
	    ctx.globalCompositeOperation = 'source-over';
	}
    }
};

function update_points() {
    var p1 = 0;
    var p2 = 0;

    for(var i = 0; i < 16; ++i) 
	for(var j = 0; j < 16; ++j){
	    if(mine[i][j].s == 'r')
		++p1;
	    else if(mine[i][j].s == 'b')
		++p2;
	}

    if(params.player == 1)
	tnt.allowed = p2 > p1;
    else
	tnt.allowed = p1 > p2;

    display_tnt();

    var hidden = 51 - p1 - p2;
    document.getElementById('p1_pts').innerHTML = String(p1);
    document.getElementById('p2_pts').innerHTML = String(p2);
    document.getElementById('h_pts').innerHTML = String(hidden);

    var prop1, prop2;
    if (p1 > p2) {
	prop1 = 1;
	prop2 = p2 / p1;
    } else if (p2 > p1) {
	prop2 = 1;
	prop1 = p1 / p2;
    } else {
	prop1 = prop2 = 1;
    }
    
    var g = hidden * 5;
    var rem_total = 255 - g;
    var r = g + Math.round(prop1 * rem_total);
    var b = g + Math.round(prop2 * rem_total);
    var bg_color = 'rgba(' + r + ',' + g + ',' + b + ',0.25)'
    document.getElementById('game_box').style.background = bg_color;
}

function close_last_nt() {
    if(last_nt) {
	last_nt.cancel();
	last_nt = null;
    }
}

function notify_state(msg) {
    // Sound stuff
    var ring = document.getElementById('ring');
    ring.play();

    // Notification stuff
    if(!nt
       || nt.checkPermission() != /* nt.PERMISSION_ALLOWED */ 0
       || document.visibilityState == "visible")
	return;

    if(msg != '') {
	try{
	    close_last_nt();
	    last_nt = nt.createNotification('/static/images/icon32.png', 'DigGems: Jogo ' + params.game_id, msg);
	    last_nt.show();
	} catch(err) {
	    // Do nothing...
	}
    }
}

// TODO: localization
function set_state(state) {
    var msg;
    if(params.player) {
	if(state == params.player) {
	    msg = 'Sua vez! Jogue!';
	}
	else if(state == 1 || state == 2) {
	    msg = 'Aguarde sua vez.';
	}
	else if(state == 3 || state == 4) {
	    msg = 'O jogo acabou, ';
	    if((state - 2) == params.player) {
		if(auth.fb) {
		    /*document.getElementById('brag_button')
		    .style.setProperty('visibility', 'visible', null);*/
		}
		msg += 'você venceu!';
	    }
	    else
		msg += 'você perdeu.';
	}
	else
	    return; // What else can I do?

	if(params.state != state && (state == params.player || state > 2))
	    notify_state(msg);
    } else {
	// Spectator mode.
	var state_msgs =
	    ['',
	     'Vez do vermelho.',
	     'Vez do azul.',
	     'O jogo acabou, o vermelho venceu.',
	     'O jogo acabou, o azul venceu.'];
	msg = state_msgs[state];
    }
    var msg_box = document.getElementById('message');
    if (!params.state && state) {
	// Just started the game, prepare box for messages
	msg_box.innerHTML = '';
	msg_box.className += " big";
    }
    msg_box.innerHTML = msg;
    params.state = state;
}

function blue_player_display(info) {
    var name = document.getElementById('p2_name');
    if (info && info.length == 2) {
	var uid = info[0];
	var pname = info.slice(1).join('<br \>');

	var link = document.getElementById('p2_link');
	link.href = "//facebook.com/" + uid + "/";
	link.className += " undlin";

	var pic = document.getElementById('p2_pic');
	pic.src = "//graph.facebook.com/" + uid + "/picture";
	pic.style.display = "inline-block";

	name.innerHTML = pname;
    } else {
	name.innerHTML = "Visitante";
    }
}

function handle_event(msg) {
    var lines = msg.split('\n');
    var seq_num = parseInt(lines[0]);

    if(seq_num <= params.seq_num)
	return;
    params.seq_num = seq_num;

    var new_state = parseInt(lines[1]);
    var old_state = params.state;
    set_state(new_state);
    if(old_state == 0) {
	// The second (blue) player just connected.
	// Display know info about the other player.
	blue_player_display(lines.slice(2));
	return;
    }

    var player = parseInt(lines[2]);
    var lclick = last_click_decode(player, lines[3]);
    
    if (player == params.player && lclick.bombed) {
	params.tnt_used = true;
	tnt.active = false;
    }
    
    var parser = /(\d+),(\d+):(.)/;
    for(var i = 4; i < lines.length; ++i) {
	var res = parser.exec(lines[i]);
	if(res) {
	    var m = parseInt(res[1]);
	    var n = parseInt(res[2]);

	    // Just assume correct valid values were delivered...

	    mine[m][n].s = res[3];
	    mine[m][n].draw();
	}
    }

    if(last_click[player-1])
	last_click[player-1].clear();
    last_click[player-1] = lclick;
    lclick.draw();

    update_points();
}

function register_event() {
    if(params.state >= 3 || register_event.last_status == 410)
	return; // Game is over

    event_request.open('GET', '/event/'+ params.channel, true);
    if(register_event.etag)
	event_request.setRequestHeader('If-None-Match', register_event.etag);
    event_request.setRequestHeader('If-Modified-Since', params.last_change);
    event_request.onreadystatechange = function(ev){
	if (event_request.readyState == 4) {
	    register_event.last_status == event_request.status;
	    if(event_request.status == 200) {
		register_event.error_count = 0;
		register_event.etag = event_request.getResponseHeader('Etag')
		params.last_change = event_request.getResponseHeader('Last-Modified')

		handle_event(event_request.responseText);
		register_event();
	    }
	    else {
		// If this is the first error, try again right away
		// If not, delay some time before trying again
		if(register_event.error_count)
		    register_event.error_count = Math.min(register_event.error_count + 1, 10);
		else
		    register_event.error_count = 1;

		if(register_event.error_count > 1) {
		    var delay = (register_event.error_count - 1) * 500;
		    setTimeout(register_event, delay);
		}
		else
		    register_event();
	    }
	}
    }
    event_request.send(null);
}

function on_click(ev) {
    if(ev.button != 0 || params.player != params.state)
	return;

    var m;
    var n;
    if (ev.offsetX !== undefined && ev.offsetY !== undefined) {
	m = ev.offsetX;
	n = ev.offsetY;
    } else {
	var totalOffsetX = 0;
	var totalOffsetY = 0;
	var currentElement = this;

	do{
	    totalOffsetX += currentElement.offsetLeft - currentElement.scrollLeft;
	    totalOffsetY += currentElement.offsetTop - currentElement.scrollTop;
	} while(currentElement = currentElement.offsetParent);

	m = ev.clientX - totalOffsetX;
	n = ev.clientY - totalOffsetY;
    }

    m = Math.floor(m / 26);
    n = Math.floor(n / 26);

    if(!tnt.active && mine[m][n].s != '?')
	return;

    close_last_nt();

    // TODO: indicate activity

    var url = '/game/'+ params.game_id + '/move/?m=' + m + '&n=' + n;
    if(tnt.active) {
	url += '&tnt=y';
    }
    move_request.open('POST', url, true);
    move_request.onreadystatechange = function(ev){
	if (move_request.readyState == 4) {
	    if(move_request.status == 200) {
		// TODO: stop activity indication
	    }
	    // TODO: else: treat error
	}
    };
    move_request.send(null);
}

function init() {
    // TODO: find a better way to deal with sound
    // Bogus browsers won't allow me to play the sound repeatedely
    // without reloading it.
    var ring = document.getElementById('ring');
    ring.addEventListener('ended', function() { ring.load(); }, false);

    var canvas = document.getElementById('game_canvas');
    
    if (!canvas || !canvas.getContext) {
	// Panic return
	// TODO: add friendly message explaining why IE sucks
	return;
    }

    // Set shovel cursor in game_canvas area
    canvas.style.cursor = 'url(/static/images/shovel.png),auto';
        
    mine = new Array(16);
    for (var i=0; i < 16; ++i) {
	mine[i] = new Array(16);
	for (var j=0; j < 16; ++j)
	    mine[i][j] = new Tile(i,j);
    }

    if(params.mine)
	for(var i = 0; i < 256; ++i)
	    mine[Math.floor(i/16)][i%16].s = params.mine.charAt(i);

    // Text presets
    ctx = canvas.getContext('2d');
    ctx.font = "17pt Arial, Helvetica, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    // Strokes presets
    ctx.lineJoin = 'round';
    ctx.lineWidth = 3;

    // Shadows presets
    // TODO: Fix buggy shadows drawing...
    ctx.shadowOffsetX = 1;
    ctx.shadowOffsetY = 1;
    ctx.shadowBlur = 1;
    ctx.shadowColor = "black";

    // Draw map
    for(var i = 0; i < 16; ++i)
	for(var j = 0; j < 16; ++j)
	    mine[i][j].draw();

    // Draw movement marks
    if(params.p1_last_move) {
	last_click[0] = last_click_decode(1, params.p1_last_move);
	last_click[0].draw();
    }
    if(params.p2_last_move) {
	last_click[1] = last_click_decode(2, params.p2_last_move);
	last_click[1].draw();
    }

    // Put display in current state
    set_state(params.state);
    update_points();

    // Receive updates from server
    register_event();

    if(params.player) { // Not a spectator
	// Expect for user input
	canvas.addEventListener('click', on_click, false);
	document.getElementById('tnt').addEventListener('click', toggle_tnt, false);
    }
    
    // Everything is setup, show the canvas
    canvas.style.setProperty('visibility', 'visible', null);
}

// Will publish the result of a match to the wall.
// ATTENTION: This thing is completely unsafe and fakeable!
// TODO: FIX SECURITY PROBLEM!
function publish_results()
{
    if((params.state - 2) != params.player
       || !auth.fb)
	return;

    var dialog = {
        method: 'feed',
	// TODO: put right link here
        link: 'http://vella.no-ip.org/',
        picture: 'http://vella.no-ip.org/static/images/logo.png',
        name: 'Resultado DigGems',
        caption: 'Partida Ganha',
        description: 'Using Dialogs to interact with users.'
    };
}

function load_img(name) {
    var img = new Image();
    img.src = "/static/images/" + name + ".png";
    images[name] = img;
}

// Load resources
load_img("saphire");
load_img("ruby");
load_img("crate");
load_img("tnt");
load_img("explosion");

window.addEventListener('load', init, false);
