// Copyright 2011 Lucas Clemente Vella
// Software distributed under Affero GPL, see http://gnu.org/licenses/agpl.txt

var ctx;
var mine;
var move_request = new XMLHttpRequest();
var event_request = new XMLHttpRequest();

var images = {};

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

// Bomb things:
var bomb = {
    'allowed': false,
    'active': false
};

/* Displays the bomb if it is to be shown. */
function display_bomb() {
    var visible = !params.bomb_used && bomb.allowed;
 
    document.getElementById('bomb')
	.style.setProperty('visibility',
			   visible ? 'visible' : 'hidden', null);
}

function toggle_bomb(ev) {
    var button = document.getElementById('bomb');

    if(params.bomb_used || !bomb.allowed) {
	bomb.active = false;
	display_bomb();
	return;
    }

    // TODO: marker over the bomb area
    //var canvas =  document.getElementById('game_canvas');

    if(!bomb.active) {
	bomb.active = true;
	button.style.setProperty('background-color', 'red', null);
	//toggle_bomb.move_event = canvas.addEventListener('move', on_click, false);
    }
    else {
	bomb.active = false;
	button.style.removeProperty('background-color');
    }
}

// Class Tile
function Tile(x0,y0) {
  this.s = '?';
  this.x = x0*26;
  this.y = y0*26;
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
    }
};

function load_img(name) {
    var img = new Image();
    img.src = "/static/images/" + name + ".png";
    images[name] = img;
}

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
	bomb.allowed = p2 > p1;
    else
	bomb.allowed = p1 > p2;

    display_bomb();

    document.getElementById('p1_pts').innerHTML = String(p1);
    document.getElementById('p2_pts').innerHTML = String(p2);
}

// TODO: localization
function set_state(state) {
    var msg;
    if(params.player) {
	if(state == params.player) {
	    msg = 'Sua vez!';
	}
	else if(state == 1 || state == 2) {
	    msg = '';
	}
	else if(state == 3 || state == 4) {
	    msg = 'Fim de jogo. ';
	    if((state - 2) == params.player)
		msg += 'Você venceu!';
	    else
		msg += 'Você perdeu.';
	}
	else
	    return; // What else can I do?
    } else {
	// Spectator mode.
	var state_msgs =
	    ['',
	     'Vez do vermelho.',
	     'Vez do azul.',
	     'Vermelho venceu.',
	     'Azul venceu.'];
	msg = state_msgs[state];
    }

    document.getElementById('message').innerHTML = msg;
    params.state = state;
}

function handle_event(msg) {
    var lines = msg.split('\n');
    var seq_num = parseInt(lines[0]);

    if(seq_num <= params.seq_num)
	return;
    params.seq_num = seq_num;

    var new_state = parseInt(lines[1]);
    set_state(new_state);
    if(lines.length <= 2)
	return;

    var player = parseInt(lines[2]);
    var lclick = last_click_decode(player, lines[3]);
    var parser = /(\d+),(\d+):(.)/;

    for(var i = 4; i < lines.length; ++i) {
	var res = parser.exec(lines[i]);
	if(res) {
	    var m = parseInt(res[1]);
	    var n = parseInt(res[2]);

	    // Just suppose correct valid values were delivered...

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

    m = ev.clientX + document.body.scrollLeft +
	document.documentElement.scrollLeft - this.offsetLeft;
    n = ev.clientY + document.body.scrollTop +
        document.documentElement.scrollTop - this.offsetTop;

    m = Math.floor(m / 26);
    n = Math.floor(n / 26);

    if(!bomb.active && mine[m][n].s != '?')
	return;

    // TODO: indicate activity

    var url = '/game/'+ params.game_id + '/move/?m=' + m + '&n=' + n;
    var bombed = false;
    if(bomb.active) {
	url += '&bomb=y';
	bombed = true;
    }
    move_request.open('GET', url, true);
    move_request.onreadystatechange = function(ev){
	if (move_request.readyState == 4) {
	    if(move_request.status == 200) {
		// TODO: find a more reliable way to know if the bomb was used
		if(bombed) {
		    params.bomb_used = true;
		    toggle_bomb();
		}
	    }
	    // TODO: else: treat error
	    // TODO: stop activity indication
	}
    };
    move_request.send(null);
}

function init() {
    var canvas = document.getElementById('game_canvas');
    if (!canvas || !canvas.getContext) {
	// Panic return
	// TODO: add friendly message explaining why IE sucks
	return;
    }

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
	// Wait for user
	canvas.addEventListener('click', on_click, false);
	document.getElementById('bomb').addEventListener('click', toggle_bomb, false);
    }
}

// Load Images
load_img("saphire");
load_img("ruby");

window.addEventListener('load', init, false);
