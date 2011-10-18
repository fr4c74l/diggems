// Copyright 2011 Lucas Clemente Vella
// Software distributed under Affero GPL, see http://gnu.org/licenses/agpl.txt

var ctx;
var mine = Array();
var move_request = new XMLHttpRequest();
var event_request = new XMLHttpRequest();

var images = {};
var fps = 60;
var inc = 0.4;
var direction = 1;
var dy = 0;
var dmax = 10;
var t = 0.01;

// Bomb things:
var bomb = {
    'allowed': false,
    'active': false
};

/* Displays the bomb if it is to be shown. */
function display_bomb() {
  var visible = !params.bomb_used && bomb.allowed;
  document.getElementById('bomb')
  .style.setProperty('visibility', visible ? 'visible' : 'hidden', null);
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
    //TODO: quando o jogador clicar na bomba, chamar animação que queima o pavil e caso ele nao clique no tabuleiro a tempo de explodir, a bomba falha.
    button.style.setProperty('background-color', 'red', null);
    //toggle_bomb.move_event = canvas.addEventListener('move', on_click, false);
  }
  else {
    bomb.active = false;
    //button.style.setProperty('background-color', 'green', null);
  }
}

// Class Tile
function Tile(x0,y0) {
  this.x = x0;
  this.y = y0;
}

Tile.prototype.draw = function(name, hover) {
  if(hover)
    ctx.drawImage(images[name+"_on"], this.x + 2.5, this.y + 2.5, 20, 20);
  else
    ctx.drawImage(images[name+"_off"], this.x + 2.5, this.y + 2.5, 20, 20);
};

function create_tile_matrix(r,c) {
  var i;
  var j;
  var m = new Array(r);
  for (i=0; i < r; ++i) {
    m[i] = new Array(c);
    for (j=0; j < c; ++j)
      m[i][j] = new Tile(i,j);
  }
  return(m);
}

function idx(m, n) {
  return mine[m*16 + n];
}

function load_img(name) {
  images[name] = new Image();
  images[name].src = "/static/images/" + name + ".png";
}

function drawShadow(cx, cy, width, height) {
  ctx.beginPath();
  ctx.moveTo(cx, cy - height/2);
  ctx.bezierCurveTo(
  cx + width/2, cy - height/2,
  cx + width/2, cy + height/2,
  cx, cy + height/2);
  ctx.bezierCurveTo(
  cx - width/2, cy + height/2,
  cx - width/2, cy - height/2,
  cx, cy - height/2);
  ctx.fillStyle = "black";
  ctx.fill();
  ctx.closePath();
}

function draw_tile(name, x, y, w, h) {
  ctx.drawImage(images[name], x, y, w, h);
}

function update_anim(name) {
  // control
  if (direction === 1) {
    dy -= inc;
    t -= 0.01;
    if (dy < -dmax) {
      direction = -1;
    }
  } else {
    dy += inc;
    t += 0.01;
    if(dy > dmax) {
      direction = 1;
    }
  }
  //clear_canvas(); //FIXME: clear ???
  //ctx.translate(canvas.width/2, canvas.height/2);
  ctx.save()
  //ctx.scale(1-(t/2),1+t);
  // redraw image
  ctx.drawImage(images[name], x0 + 2.5, y0 + 2.5 -dy, 20, 20);
  ctx.restore();
  // shadow
  //drawShadow(x0, y0 + 16, 15 - dy, 6);
}


function draw_square(m,n) {
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

  x0 = m * 26;
  y0 = n * 26;
  tile = idx(m, n);

  function draw() { ctx.fillRect(x0,y0,25,25); }

  if(tile >= 0 && tile <= 8) {
    ctx.fillStyle = 'rgb(139,121,94)';
    draw();
    if(tile > 0) {
      ctx.fillStyle = TEXT_COLOR[tile-1];
      ctx.fillText(tile, x0 + 12.5, y0 + 12.5);
    }
  }
  else {
    if(tile == 'r' || tile == 'b') {
      ctx.fillStyle = 'rgb(109,101,74)';
      draw();
      (tile == 'b') ? name="saphire" : name="ruby";
//      anim_interval = setInterval(update_anim, 1000 / fps, name);
//FIXME: comenta a linha de cima e descomenta a de baixo para so aparecer as imagens
      (tile == 'b') ? draw_tile("saphire", x0 + 2.5, y0 + 2.5, 20, 20) : draw_tile("ruby", x0 + 2.5, y0 + 2.5, 20, 20);
    }
    else {
      ctx.fillStyle = 'rgb(155,205,155)';
      draw();
    }
  }
}

function cleartimer(){
  if (window.anim_interval) 
    clearInterval(anim_interval);
}

function clear_canvas() {
  // Store the current transformation matrix
  ctx.save();
  // Use the identity matrix while clearing the canvas
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  // Restore the transform
  ctx.restore();
}

function update_points() {
    var p1 = 0;
    var p2 = 0;

    for(var i = 0; i < 256; ++i) {
        if(mine[i] == 'r'){
            ++p1;
        }
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
  var seq_num = parseInt(changes[0]);

  if(seq_num <= params.seq_num)
    return;
  params.seq_num = seq_num;

  set_state(parseInt(changes[1]));

  for(var i = 2; i < changes.length; ++i) {
    var res = parser.exec(changes[i]);
    if(res) {
      var m = parseInt(res[1]);
      var n = parseInt(res[2]);
      // TODO: validate data
      mine[m*16 + n] = res[3];
      draw_square(m,n);
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

function mousemove(ev) {
  var m;
  var n;
  m = ev.clientX + document.body.scrollLeft +
document.documentElement.scrollLeft - this.offsetLeft;
  n = ev.clientY + document.body.scrollTop +
      document.documentElement.scrollTop - this.offsetTop;
  m = Math.floor(m / 26);
  n = Math.floor(n / 26);
  ctx.save();
  ctx.fillStyle = 'rgb(155,255,155)';
  ctx.fillRect(m*26,n*26,25,25);
  ctx.restore();

ctx.save();
  ctx.fillStyle = 'black';
  ctx.font = "bold 12px sans-serif";
  ctx.fillText("Mouse position: m:" + m + " n: " + n, 40, 200);
ctx.restore();
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

  if(!bomb.active && mine[m*16 + n] != '?')
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

  ctx.shadowOffsetX = 1;
  ctx.shadowOffsetY = 1;
  ctx.shadowBlur = 1;
  ctx.shadowColor = "black";

  // Load Images
//  load_img("grass1");
  load_img("saphire");
  load_img("ruby");

  // Draw map
  for(var i = 0; i < 16; ++i)
    for(var j = 0; j < 16; ++j){
      draw_square(i,j);
    }

  // Put display in current state
  set_state(params.state);
  update_points();

  // Receive updates from server
  register_event();

  // Wait for user
  canvas.addEventListener('click', on_click, false);
  //TODO: hover the tiles on mouse move
  //canvas.addEventListener('mousemove',mousemove,false);
  document.getElementById('bomb').addEventListener('click', toggle_bomb, false);
  //TODO: de tempo em tempo aplicar efeito de luz nas gemas
  //setInterval(draw,100); 

}
window.addEventListener('load', init, false);
