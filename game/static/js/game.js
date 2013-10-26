// Copyright 2011 Lucas Clemente Vella
// Copyright 2013 Fractal Jogos e Tecnologia
// Software distributed under Affero GPL, see http://gnu.org/licenses/agpl.txt

var ctx;
var mine;
var event;
var button_request = new XMLHttpRequest();

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
  this.hover = false;
  this.x = x0 * 26;
  this.y = y0 * 26;
  
  // Activity indication
  this.blink_state = 0;
  this.ai = null;
}

Tile.prototype.draw = function() {
    if (this.blink_state) {
	var color = this.hover ? [251,170,56] : [227,133,0];
	for (var i = 0; i < 3; ++i) {
	    var delta = 200 - color[i];
	    color[i] = Math.round(color[i] + delta * this.blink_state);
	}
	ctx.fillStyle = 'rgb(' + color[0] + ',' + color[1] + ',' + color[2] + ')';
    } else {
	ctx.fillStyle = this.hover ? 'rgb(251,170,56)' : 'rgb(227,133,0)';
    }
    ctx.fillRect(this.x, this.y, 25, 25);
};

Tile.TEXT_COLOR = [
    'rgb(0,0,255)',
    'rgb(0,160,0)',
    'rgb(255,0,0)',
    'rgb(0,0,127)',
    'rgb(160,0,0)',
    'rgb(0,255,255)',
    'rgb(160,,160)',
    'rgb(0,0,0)'
];

Tile.prototype.set_state = function(s) {
    if (s == this.s)
	return;
    this.s = s;

    if (s == 0) {
	this.draw = function() {
	    ctx.fillStyle = 'rgb(255,216,161)';
	    ctx.fillRect(this.x, this.y, 25, 25);
	};
    } else if(s > 0 && s <= 8) {
	var text_color = Tile.TEXT_COLOR[s - 1];
	this.draw = function() {
	    ctx.fillStyle = 'rgb(255,216,161)';
	    ctx.fillRect(this.x, this.y, 25, 25);
	    ctx.fillStyle = text_color;
	    ctx.fillText(this.s, this.x + 12.5, this.y + 12.5);
	};
    } else if(s == 'r' || s == 'b') {
	var icon = images[(s == 'b') ? 'saphire' : 'ruby'];
	this.draw = function() {
	    ctx.fillStyle = 'rgb(251,170,56)';
	    ctx.fillRect(this.x, this.y, 25, 25);
	    ctx.drawImage(icon, this.x + 2, this.y + 5);
	};
    } else if(s == 'x') {
	var icon = images[(params.state == 3) ? 'ruby' : 'saphire'];
	this.draw = function() {
	    ctx.fillStyle = 'rgb(227,133,0)';
	    ctx.fillRect(this.x, this.y, 25, 25);

	    ctx.globalCompositeOperation = 'lighter';
	    ctx.drawImage(icon, this.x + 2, this.y + 5);
	    ctx.globalCompositeOperation = 'source-over';
	};
    } else {
	this.draw = Tile.prototype.draw;
    }
}

// Class ActivityIndicator
function ActivityIndicator(tile) {
    this.tile = tile;
    if (tile.ai)
	tile.ai.clear();
    tile.ai = this;

    this.start_time = (new Date()).getTime();
    this.timer = setInterval(function() {
	var t = ((new Date()).getTime() - this.start_time) * ActivityIndicator.SPEED;
	this.tile.blink_state = (1 + Math.sin(t)) / 2;
	this.tile.draw();
    }.bind(this), 50);

    ActivityIndicator.all[tile.x + ',' + tile.y] = this;
}

ActivityIndicator.SPEED = Math.PI / 500; // Two full blinks per second...
ActivityIndicator.all = {};

ActivityIndicator.prototype.clear = function() {
    clearInterval(this.timer);

    delete ActivityIndicator.all[this.tile.x + ',' + this.tile.y];
    this.tile.blink_state = 0;
    this.tile.ai = null;
    this.tile.draw();

    this.tile = null;
}

ActivityIndicator.clear_all = function() {
    for (var ai in ActivityIndicator.all) {
	ActivityIndicator.all[ai].clear();
    }
}
// End of class ActivityIndicator

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

// Class Title Blinker
function TitleBlinker(msg) {
    this.original = document.title;
    this.changed = msg;
    this.blinking = false;
    this.is_displaying = false;
}

TitleBlinker.prototype.blink = function() {
    if (this.is_displaying) {
	document.title = this.original;
    } else {
	document.title = this.changed;
    }
    this.is_displaying = !this.is_displaying;
}

TitleBlinker.prototype.setBlinking = function(to_blink) {
    if (to_blink == this.blinking)
	return;
    if (to_blink) {
	this.timer = window.setInterval(this.blink.bind(this), 1000);
    } else if (this.timer) {
	document.title = this.original;
	window.clearInterval(this.timer);
	this.timer = null;
    }
    this.blinking = to_blink;
}

var your_turn_blinker = new TitleBlinker(gettext('Your turn! Play!'));

function close_last_nt() {
    if(last_nt) {
	last_nt.cancel();
	last_nt = null;
    }
}

function notify_state(msg) {
    // Sound stuff
    var ring = document.getElementById('ring');
    try{
        ring.play();
    }
    catch(e){
    }

    // Notification stuff
    if(!nt
       || nt.checkPermission() != /* nt.PERMISSION_ALLOWED */ 0
       || document.visibilityState == "visible")
	return;

    if(msg != '') {
	try{
	    close_last_nt();
	    last_nt = nt.createNotification('/static/images/icon32.png', gettext('DigGems: Game ') + params.game_id, msg);
	    last_nt.show();
	} catch(err) {
	    // Do nothing...
	}
    }
}

/* TODO: localization
States:
 0 -> Game has not started yet
 1 -> Player's 1 turn
 2 -> Player's 2 turn
 X + 2 -> Player X won
 X + 4 -> Game ended abnormally and player X won
*/
<<<<<<< HEAD
function set_state(state) {
    var msg = '';
    if(params.player) {
	    var cursor;
	    var hover_indicator;
	    if(state == params.player) {
	        msg = gettext('Your turn! Play!');
	    
	    // Set shovel cursor in game_canvas area
	    cursor = 'url(' + images['shovel'].src + '),auto';

	    // Mark the to be affected tiles
	    hover_indicator = highlight_tile;
	}
	else {
	    // Not my turn, set default cursor...
	    cursor = 'default';
	    
	    // Stop any tile that could be blinking
	    ActivityIndicator.clear_all();

	    // and stop highlighting tiles:
	    hover_indicator = null;
	    highlight_tile.clear();

		if(state == 1 || state == 2) {
		    msg = gettext('Wait for your turn.');
		}
		else if(state >= 3 && state <= 6) {
			msg = gettext('Game over, ');
			if(((state + 1) % 2) + 1 == params.player) {
				if(is_fb_auth()) {
				/*document.getElementById('brag_button')
				.style.setProperty('visibility', 'visible', null);*/
				}
				msg += gettext('you win!');
			}
			else
				msg += gettext('you lose.');
            
            document.getElementById("give_up").style.setProperty('visibility', 'hidden', null);
            document.getElementById("rematch_box").style.display = 'block';
            document.getElementById("rematch_button").style.display = 'block';
            
            timer.rematch_time = Math.round(params.time_left);
            timer.id = window.setInterval(timer, 1000);
            timer();

			game_over_notification(msg);
		}
		else
			return; // What else can I do?
	}

    var canvas = document.getElementById('game_canvas');
	canvas.style.cursor = cursor;
	canvas.onmousemove = hover_indicator;
	// Blink title to alert user, if its turn.
	your_turn_blinker.setBlinking(state == params.player);
	if(params.state != state && (state == params.player || state > 2))
		notify_state(msg);
	} else {
		// Spectator mode.
		var state_msgs =
			['',
			 gettext("Red's turn."),
			 gettext("Blue's turn."),
			 gettext('Game is over, red player won.'),
			 gettext('Game is over, blue player won.'),
			 gettext('Game is over, red player won by resignation.'),
			 gettext('Game is over, blue player won by resignation.')];
		msg = state_msgs[state];
	}
	var msg_box = document.getElementById('message');

    if (!params.state && state) {
		if(params.player)
			document.getElementById("chat_interact").style.display="block";
		// Just started the game, prepare box for messages
		msg_box.className += " big";
        document.getElementById("abort_button").style.display="none";
	    document.getElementById("give_up").style.display="block";
	}

	msg_box.innerHTML = msg;

    params.state = state;
}

/* In case updated user information came from the async
 * event channel with message type 'p', like when player
 * two joins the game, chages the user info display. */
function handle_player_data_event(data) {
    var pnum = parseInt(data.charAt(0));
    data = JSON.parse(data.slice(2));

    pnum = 'p' + pnum + '_';

    var name = data.name.capitalize();
    function update_set(name_id, link_id, pic_id, pic_size, pic_class) {
	var obj_name = document.getElementById(name_id);
	obj_name.innerHTML = '';
	obj_name.appendChild(document.createTextNode(name));

	var obj_link = document.getElementById(link_id);
	if (data.profile_url) {
	    obj_link.href = data.profile_url;
	    obj_link.classList.add('undlin');
	} else {
	    obj_link.removeAttribute('href');
	    obj_link.classList.remove('undlin');
	}

	var obj_pic = document.getElementById(pic_id);
	if (!obj_pic) {
	    obj_pic = document.createElement('img');
	    obj_pic.id = pic_id;
	    obj_pic.width = obj_pic.height = pic_size;
	    obj_link.insertBefore(obj_pic, obj_link.firstChild);
	    if (pic_class) {
		obj_pic.classList.add(pic_class);
	    }
	}
	obj_pic.src = data.pic_url;
    }

    update_set(pnum + 'name', pnum + 'link', pnum + 'pic', 40);
    update_set(pnum + 'rname', pnum + 'rlink', pnum + 'rpic', 60, 'rematch_player_pic');
}

function handle_event_rematch(msg)
{
  var m = JSON.parse(msg);
  if (m.p1_click)
  {
    document.getElementById('rematch_status_p1').style.visibility='visible';
  }

  if (m.p2_click)
  {
    document.getElementById('rematch_status_p2').style.visibility='visible';
  }

  if (m.p1_click && m.p2_click && m.game_id)
  {
    var url = '/game/' + m.game_id;
    window.location = url;
  }
}

function timer()
{
  timer.rematch_time = timer.rematch_time - 1;
  document.getElementById('rematch_button').innerHTML = gettext("Rematch ") + "(" + timer.rematch_time+ ")";
  if (timer.rematch_time <= 0)
  {
    document.getElementById("rematch_button").style.display = 'none';
    clearInterval(timer.id);
    return;
  }
}

//TODO: Implement a library for all game animations
function game_over_notification(msg) {
	var go_msg = document.getElementById('game_over_msg');
	$("#game_over").css('display', 'block').animate({'left':'2%', 'bottom':'50%'},500);
	go_msg.innerHTML = msg;
}

function load_text_animation(text_id) {
	var text = $(text_id).text()
	setInterval(function(){
		for (i = 1; i <= 3; i++) {
			setTimeout(function() {
				$(text_id).append(".");
			}, i * 500);
		}
		$(text_id).html(text);
	}, 2000);
}

function hidden_invite_menu() {
	$('#load_menu').animate({'top':'-50%'},500,function(){
		$('#overlay').fadeOut('fast');
	});
	return false;
}

function handle_event(msg, seq_num) {
    var lines = msg.split('\n');

    if(seq_num <= params.seq_num)
	    return;
    params.seq_num = seq_num;

    var new_state = parseInt(lines[0]);
    set_state(new_state);

	if (new_state != 0 && params.seq_num == 2 ){
		hidden_invite_menu();
		// show message box
		document.getElementById('message').style.setProperty('display', 'block', null);
	}
    if (lines.length > 2){
        var player = parseInt(lines[1]);
        var lclick = last_click_decode(player, lines[2]);
        
        if (player == params.player && lclick.bombed) {
	        params.tnt_used = true;
	        tnt.active = false;
        }
        
        var parser = /(\d+),(\d+):(.)/;
        for(var i = 3; i < lines.length; ++i) {
    	    var res = parser.exec(lines[i]);
	        if(res) {
	            var m = parseInt(res[1]);
	            var n = parseInt(res[2]);

	            // Just assume correct valid values were delivered...

	            mine[m][n].set_state(res[3]);
		        if (mine[m][n].ai) {
			        mine[m][n].ai.clear();
		        } else {
			        mine[m][n].draw();
		        }
		    }
        }
		if(last_click[player-1])
		    last_click[player-1].clear();
		last_click[player-1] = lclick;
		lclick.draw();
	}    
    update_points();
    reset_counter();
}

function register_event() {
    if(params.state >= 3 || register_event.last_status == 410)
	return; // Game is over

    event_request.open('GET', '/event/' + params.channel, true);
    if(register_event.etag)
	event_request.setRequestHeader('If-None-Match', register_event.etag);
    event_request.setRequestHeader('If-Modified-Since', params.last_change);
    event_request.onreadystatechange = function(ev){
	if (event_request.readyState == 4) {
	    register_event.last_status = event_request.status;
	    if(event_request.status == 200) {
		register_event.error_count = 0;
		register_event.etag = event_request.getResponseHeader('Etag')
		params.last_change = event_request.getResponseHeader('Last-Modified')

		handle_event_game(event_request.responseText);
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

function mouse_tile(ev) {
    var m;
    var n;
    if (ev.offsetX !== undefined && ev.offsetY !== undefined) {
	m = ev.offsetX;
	n = ev.offsetY;
    } else {
	var totalOffsetX = 0;
	var totalOffsetY = 0;
	var currentElement = ev.target;

	while(currentElement.offsetParent) {
	    totalOffsetX += currentElement.offsetLeft - currentElement.scrollLeft;
	    totalOffsetY += currentElement.offsetTop - currentElement.scrollTop;
	    currentElement = currentElement.offsetParent;
	}

	// Caveat: On Firefox, with XHTML, <body> scroll is 0 and we must use window scroll...
	totalOffsetX -= window.scrollX;
	totalOffsetY -= window.scrollY;

	m = ev.clientX - totalOffsetX;
	n = ev.clientY - totalOffsetY;
    }

    m = Math.floor(m / 26);
    n = Math.floor(n / 26);
    
    return {'m': m, 'n': n};
}

function on_click(ev) {
    if(ev.button != 0 || params.player != params.state)
	return;

    var pos = mouse_tile(ev);
    if(!tnt.active && mine[pos.m][pos.n].s != '?')
	return;

    close_last_nt();

    new ActivityIndicator(mine[pos.m][pos.n]);

    var url = '/game/'+ params.game_id + '/move/?m=' + pos.m + '&n=' + pos.n;
    if(tnt.active) {
	url += '&tnt=y';
    }

    var move_request = new XMLHttpRequest();
    move_request.open('POST', url, true);
    move_request.onreadystatechange = function(ev){
	if (ev.target.readyState == 4) {
	    if(ev.target.status != 200) {
		// Error: server didn't accept click, probably just a
		// syncronization error due to network delay that will
		// correct itself automatically.

		if (mine[pos.m][pos.n].ai) {
		    mine[pos.m][pos.n].ai.clear();
		}
	    }
	}
    };
    move_request.send(null);
}

// Hover effect on tile
function highlight_tile(ev) {
    var pos = mouse_tile(ev);
    var to_redraw = Array();

    if(highlight_tile.old) {
	var old = highlight_tile.old;
	if(tnt.active == old.active && old.m == pos.m && old.n == pos.n) {
	    return;
	}

	highlight_tile.set_hover(old.active, old, false, to_redraw);
    }
    highlight_tile.set_hover(tnt.active, pos, true, to_redraw);

    highlight_tile.old = {'active': tnt.active, 'm': pos.m, 'n': pos.n};

    // Redraw affected tiles.
    highlight_tile.redraw_hidden(to_redraw);
}

highlight_tile.redraw_hidden = function(to_redraw) {
    for (var k in to_redraw) {
	pos = to_redraw[k];
	var tile = mine[pos.m][pos.n];
	if (tile.s == '?')
	    tile.draw();
    }
}

highlight_tile.set_hover = function(tnt, bpos, hover, to_redraw) {
    if(tnt) {
	for(var dm = -2; dm <= 2; ++dm) {
	    for(var dn = -2; dn <= 2; ++dn) {
		var m = bpos.m + dm;
		var n = bpos.n + dn;
		if (m >= 0 && m <= 15 && n >= 0 && n <= 15) {
		    mine[m][n].hover = hover;
		    to_redraw[m + ',' + n] = {'m': m, 'n': n};
		}
	    }
	}
    } else {
	    mine[bpos.m][bpos.n].hover = hover;
	    to_redraw[bpos.m + ',' + bpos.n] = bpos;
    }
}

highlight_tile.clear = function() {
    if(!highlight_tile.old)
	return;

    var to_redraw = Array();
    var old = highlight_tile.old;
    highlight_tile.set_hover(old.active, old, false, to_redraw);
    highlight_tile.redraw_hidden(to_redraw);
}

function init() 
{
    // TODO: find a better way to deal with sound
    // Bogus browsers won't allow me to play the sound repeatedely
    // without reloading it.
    var ring = document.getElementById('ring');
    ring.addEventListener('ended', function() { ring.load(); }, false);

    var canvas = document.getElementById('game_canvas');
    
    if (!canvas || !canvas.getContext) 
    {
	    // Panic return
	    // TODO: add friendly message explaining why IE sucks
	    return;
    }

    mine = new Array(16);
    for (var i=0; i < 16; ++i) 
    {
	    mine[i] = new Array(16);
	    for (var j=0; j < 16; ++j)
	        mine[i][j] = new Tile(i,j);
    }

    if(params.mine)
	    for(var i = 0; i < 256; ++i)
	        mine[Math.floor(i/16)][i%16].set_state(params.mine.charAt(i));

    // Text presets
    ctx = canvas.getContext('2d');
    ctx.font = "17pt Arial, Helvetica, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    // Strokes presets
    ctx.lineJoin = 'round';
    ctx.lineWidth = 3;

    // Shadows presets
    ctx.shadowOffsetX = 1;
    ctx.shadowOffsetY = 1;
    ctx.shadowColor = "black";

    // Draw map
    for(var i = 0; i < 16; ++i)
	      for(var j = 0; j < 16; ++j)
	        mine[i][j].draw();

    // Draw movement marks
    if(params.p1_last_move) 
    {
	    last_click[0] = last_click_decode(1, params.p1_last_move);
	    last_click[0].draw();
    }
    if(params.p2_last_move) 
    {
	    last_click[1] = last_click_decode(2, params.p2_last_move);
	    last_click[1].draw();
    }

    // Put display in current state
    set_state(params.state);
    update_points();

    // Set title alert if must
    your_turn_blinker.setBlinking(params.state == params.player);

    // Receive updates from server
    event = new Event(
	(/^https/.test(location.protocol) ? "wss://" : "ws://")
	+ location.hostname + (location.port ? (":" + location.port) : "")
	+ location.pathname + "event/");
    event.register_handler('g', handle_event, params.seq_num);
    event.register_handler('p', handle_player_data_event);
    event.register_handler('r', handle_event_rematch);

    // Init chat stuff
    chat.init(
	document.getElementById("chat_textfield"),
	document.getElementById("input_field"),
	document.getElementById("send_button"),
	event
    );

    if(params.player) 
    { 
      // Not a spectator
	    // Expect for user input
	    canvas.addEventListener('click', on_click, false);
	    document.getElementById('tnt').addEventListener('click', toggle_tnt, false);
    }
    
    // Everything is setup, show the canvas
    canvas.style.setProperty('visibility', 'visible', null);
    if ((params.state == 1) || (params.state == 2)){
        turn_timeout.start_time = (new Date()).getTime();
        reset_counter.int = window.setInterval(turn_timeout, 1000);
        turn_timeout();
    }

	// loading game menu
    $('#overlay').fadeIn('fast',function(){
        $('#load_menu').animate({'top':'160px'},500);
    });
    load_text_animation("#loading");
}

function load_img(name)
{
    var img = new Image();
    img.src = "/static/images/" + name + ".png";
    images[name] = img;
}

function turn_timeout()
{
	var timeleft = params.time_left - ((new Date()).getTime() - turn_timeout.start_time) / 1000;
	if (timeleft <= 10)
	  document.getElementById("clock").style.setProperty('color', '#ff0000');
	if (timeleft <= 0)
	{
		clearInterval(reset_counter.int);
		timeleft = 0;
		if (params.player && (params.player != params.state) && (params.state == 1 || params.state == 2)) {
			document.getElementById("timer_box").style.setProperty('visibility', 'hidden', null);
//			document.getElementById("timeout_buttons").style.display = 'block';
			$("#timeout_buttons").animate({
			width: "toggle",
			left: "126px",
			opacity: "toggle"}, 200);
		}
	}
	document.getElementById("clock").innerHTML = Math.round(timeleft);
}

function reset_counter()
{
  document.getElementById("timeout_buttons").style.display = 'none';
  if (reset_counter.int)
    clearInterval(reset_counter.int);
  if (params.state == 1 || params.state == 2)
  {
    turn_timeout.start_time = (new Date()).getTime();
    params.time_left = 45;
    turn_timeout();
    document.getElementById("clock").style.setProperty('color', '#000000');
    document.getElementById("timeout_buttons").style.display = 'none';
    reset_counter.int = window.setInterval(turn_timeout, 1000);
  }
  else
    document.getElementById("clock").innerHTML = "";
  document.getElementById("timer_box").style.setProperty('visibility', 'visible');
}

function claim_game(terminate)
{
	var url = '/game/' + params.game_id + '/claim/';
	button_request.open('POST', url, true);
	var data = null;
	if (terminate == 1)
	{
		data = "terminate=y";
		button_request.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
	}
  if (terminate == 2)
  {
    data = "terminate=z";
    button_request.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
  }
	button_request.send(data);
}

function request_friends() {
    FB.ui({method: 'apprequests',
		title: gettext('Challenge friends!'),
		message: gettext('Choose your possible oponents.'),
		data: params.game_id,
    },
	function (response){
		if (response && response.request) {
			var notifier = new XMLHttpRequest();
			notifier.open("POST", "fb_notify_request/", true);
			notifier.setRequestHeader("Content-type", "application/json");
			notifier.send(JSON.stringify(response));
		}
	});
}

function rematch(game_id)
{
    var url = '/game/' + game_id + '/rematch/';
    button_request.open('POST', url, true);
    button_request.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    button_request.send(null);
    document.getElementById("rematch_button").style.display = 'none';
}

// Load resources
load_img("saphire");
load_img("ruby");
load_img("crate");
load_img("tnt");
load_img("explosion");
load_img("shovel");

window.addEventListener('load', init, false);
