var chat = (function (){
	var chat_ul;
	var input_field;
	var msg_length = 80;
	var open = true;
	var blink_id = 0;
	var event;
	var sec_in_day = (24 * 60 * 60);

	function toggle_chat() {
		$("#chat_area").animate({
		height: "toggle",
		opacity: "toggle"
		}, 300);
		open = !open;
		if (open){
			clearInterval(blink_id);
			blink_id = 0;
			input_field.focus();
		}
		return false;
	}


	function send_message()
	{
		var msg = input_field.value;
		if (msg != "")
		{
			event.send('c', msg);
		}

		// Clean input field
		input_field.value = "";
	}

	function max_length_warn() {
		if ($("#length_notify").is(":hidden")) {
			$("#length_notify").show("slow").delay(2000).slideUp();
		}
	}

	function handle_key_press(e) {
		var key = e.keyCode || e.which;
		if (key == 13)  //enter keycode
			(input_field.value.length > msg_length) ? max_length_warn() : send_message();
	}

	function format_date_string(hours, minutes, seconds){
		function pad(n){return n<10 ? '0'+n : n}
		return pad(hours)+':'
			+ pad(minutes)+':'
			+ pad(seconds);
	}

	function handle_event(msg) {
		data = JSON.parse(msg);

		var date = new Date();
		var offset = data['time_in_sec'] - (date.getTimezoneOffset() * 60) + sec_in_day;
		offset %= sec_in_day;
		var seconds = offset % 60;
		var minutes = Math.floor(offset / 60) % 60;
		var hours = Math.floor(offset / 3600);
		var time_fmt = "(" + format_date_string(hours, minutes, seconds) + ") ";
		var li = document.createElement('li');
		var li_text;
		
        li.className = "message";
		var li_text;
		if(data['msg']) {
			li_text = "<span style='color:#999;font-size:small;'>" + time_fmt
			+ "</span><span style='color:#000;font-size:small;font-weight: bold;'>"
			+ data['username'] + ' : ' + "</span>"
			+ "<span style='color:#000'>" + data['msg'] + "</span>";
		} else {
			li_text = "<span style='color:#999;font-size:small;'>" + time_fmt
			+ " " + data['status'] + "</span>";
		}
		li.innerHTML = li_text;

		chat_ul.appendChild(li);
		chat_ul.scrollTop = chat_ul.scrollHeight;
		if(!open && blink_id == 0){
			blink_id = blink("#chat_window");
		}
    }
    
	function blink(id) {
		return setInterval( function() {
			$(id).css("-webkit-transition","all 0.5s ease")
			.css("-moz-transition","all 0.5s ease")
			.css("-o-transition","all 0.5s ease")
			.css("transition", "all 0.5s ease")
			.css("backgroundColor","#08c308").delay(200).queue(function() {
				$(this).css({ background: 'rgba(255,255,255,0.5)' }); 
				$(this).dequeue();
			}); 
		}, 800);
	}

	return {
		init: function(chat_listing, input, button, ev) {
			chat_ul = chat_listing;
			input_field = input;
			event = ev;

			input_field.addEventListener("keypress", handle_key_press, false);
			//button.addEventListener("click", send_message, false);

			// click or press <ESC> to show/hide game chat
			if ($("#toggle_game_chat").length>0) {
				$("#toggle_game_chat").click(toggle_chat);
			}

			ev.register_handler('c', handle_event, 0);
		}
	}
})();

(function() {
  function in_game_init() {
		if ($("#toggle_game_chat").length > 0) {
			$(document).keydown(function(e) { 
				if (e.which == 27 ) {
					$("#toggle_game_chat").trigger("click");
				}
			});
		}
	}

	window.addEventListener('load', in_game_init, false);
})();
