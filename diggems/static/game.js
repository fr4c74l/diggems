var ctx;
var mine = Array();
var move_request = new XMLHttpRequest();
var event_request = new XMLHttpRequest();

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
	button.style.setProperty('background-color', 'green', null);
    }
}

function idx(m, n) {
    return mine[m*16 + n];
}

function draw_square(m, n) {
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
    var x0 = m * 26;
    var y0 = n * 26;
    function draw() { ctx.fillRect(x0,y0,25,25); }

    tile = idx(m, n)
    if(tile >= 0 && tile <= 8) {
	ctx.fillStyle = 'rgb(255,216,161)';
	draw();
	if(tile > 0) {
	    ctx.fillStyle = TEXT_COLOR[tile-1];
	    ctx.fillText(tile, x0 + 12.5, y0 + 12.5);
	}
    }
    else {
	ctx.fillStyle = 'rgb(227,133,0)';
	draw();

	if(tile == 'r' || tile == 'b') {
	    ctx.fillStyle = (tile == 'b') ? 'rgb(50,50,200)' : 'rgb(200,50,50)';
	    ctx.beginPath();
	    ctx.arc(x0+12.5, y0+12.5, 5, 0, Math.PI*2, true);
	    ctx.closePath();
	    ctx.fill();
	}
    }
}

function update_points() {
    var p1 = 0;
    var p2 = 0;

    for(var i = 0; i < 256; ++i) {
	if(mine[i] == 'r')
	    ++p1;
	else if(mine[i] == 'b')
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

    document.getElementById('message').innerHTML = msg;
    params.state = state;
}

function handle_event(msg) {
    var parser = /(\d+),(\d+):(.)/;
    var changes = msg.split('\n');

    set_state(parseInt(changes[0]));

    for(var i = 1; i < changes.length; ++i) {
	var res = parser.exec(changes[i]);
	if(res) {
	    var m = parseInt(res[1]);
	    var n = parseInt(res[2]);
	    // TODO: validate data
	    mine[m*16 + n] = res[3];
	    draw_square(m, n);
	    update_points();
	}
    }
}

function register_event() {
    if(params.state >= 3 || register_event.last_status == 410)
	return; // Game is over

    event_request.open('GET', '/event?id='+ params.channel, true);
    if(register_event.etag)
	event_request.setRequestHeader('If-None-Match', register_event.etag);
    if(register_event.last_modified)
	event_request.setRequestHeader('If-Modified-Since', register_event.last_modified);
    event_request.onreadystatechange = function(ev){
	if (event_request.readyState == 4) {
	    register_event.last_status == event_request.status;
	    if(event_request.status == 200) {
		register_event.error_count = 0;
		register_event.etag = event_request.getResponseHeader('Etag')
		register_event.last_modified = event_request.getResponseHeader('Last-Modified')

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
		handle_event(move_request.responseText);
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

    if(!params.mine) {
	for(var i = 0; i < 256; ++i)
	    mine[i] = '?';
    } else {
	mine = params.mine.split('');
    }

    ctx = canvas.getContext('2d');
    ctx.font = "17pt Arial, Helvetica, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    // Draw map
    for(var i = 0; i < 16; ++i)
	for(var j = 0; j < 16; ++j)
	    draw_square(i, j);

    // Put display in current state
    set_state(params.state);
    update_points();

    // Receive updates from server
    register_event();

    // Wait for user
    canvas.addEventListener('click', on_click, false);
    document.getElementById('bomb').addEventListener('click', toggle_bomb, false);
}

window.addEventListener('load', init, false);