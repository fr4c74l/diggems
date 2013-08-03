var chat = (function (){
	var chat_ul;
	var input_field;
	var url;

	var chat_request = new XMLHttpRequest();
	var sec_in_day = (24 * 60 * 60);

	function send_message()
	{
		chat_request.open('POST',url,true);

		var msg = input_field.value;
		if (msg != "")
		{
			chat_request.setRequestHeader("Content-type", "text/plain");
			chat_request.send(msg);
		}
	}

	function handle_key_press(e)
	{
		var key = e.keyCode || e.which;
		if (key == 13)  //enter keycode
			send_message();
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
		li.className = "message";
		var li_text = "<span style='color:#999;font-size:small;'>" + time_fmt + "</span><span style='color:#000;font-size:small;font-weight: bold;'>" + data['user_id'] + ' : ' + "</span>" +
						"<span style='color:#000'>" + data['msg'] + "</span>";
		li.innerHTML = li_text;

		chat_ul.appendChild(li);
		chat_ul.scrollTop = chat_ul.scrollHeight;

		// Clean input field
		input_field.value="";
	}

	return {
		init: function(chat_listing, input, button, event, post_url) {
			chat_ul = chat_listing;
			input_field = input;
			url = post_url;

			input_field.addEventListener("keypress", handle_key_press, false);
			button.addEventListener("click", send_message, false);

			event.register_handler('c', handle_event);
		}
	}
})();

(function() {
	function toggle(hidden_area, toggle_button) {
		var chat_window = document.getElementById("chat_window");
		var popup_window = document.getElementById("popup_window");
		var element = document.getElementById(hidden_area);
		var button = document.getElementById(toggle_button);
		if(element.style.display == "block") {
			element.style.display = "none";
			chat_window.style.height = "0em";
			popup_window.style.bottom = "4em";
			button.innerHTML = gettext("Chat");
		} else {
			element.style.display = "block";
			chat_window.style.height = "10em";
			popup_window.style.bottom = "7em";
			button.innerHTML = "-";
		}
	}
	
	function in_game_init()
	{
		toggle_window = document.getElementById("toggle");
		if(toggle_window)
			toggle_window.addEventListener("click",  function (ev) {toggle('chat_area' ,'toggle'); }, false);
	}
	
	window.addEventListener('load', in_game_init, false);
})();
