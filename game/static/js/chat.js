(function (){ 
var chat_request = new XMLHttpRequest();
var event_request = new XMLHttpRequest();

var input_field;

function send_message()
{
	var url  = '/main_chat/';
	chat_request.open('POST',url,true);

	var msg = input_field.value;
	if (msg != "")
	{
		var data = msg;
		chat_request.setRequestHeader("Content-type", "text/plain");
		chat_request.send(data);
	}
}

function handle_key_press(e)
{
	var key = e.keyCode || e.which;
	if (key == 13)  //enter keycode
		send_message();
}

var sec_in_day = (24 * 60 * 60);

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

	var ul = document.getElementById("chat_window");
	var li = document.createElement('li');
	li.className = "message";
	var li_text = "<span style='color:#999;font-size:small;'>" + time_fmt + "</span><span style='color:#000;font-weight: bold;'>" + data['user_id'] + ' : ' + "</span>" +
					"<span style='color:#000'>" + data['msg'] + "</span>";
	li.innerHTML = li_text;

	ul.appendChild(li);
	ul.scrollTop = ul.scrollHeight;

	// Clean input field
	input_field.value="";
}

function register_event() {
	event_request.open('GET', '/event/main_channel', true);
	if(register_event.etag)
		event_request.setRequestHeader('If-None-Match', register_event.etag);
	if(register_event.last_change)
		event_request.setRequestHeader('If-Modified-Since', register_event.last_change);
	event_request.onreadystatechange = function(ev){
		if (event_request.readyState == 4) {
			register_event.last_status == event_request.status;
			if(event_request.status == 200) {
			register_event.error_count = 0;
			register_event.etag = event_request.getResponseHeader('Etag')
			register_event.last_change = event_request.getResponseHeader('Last-Modified')

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

var init = function()
{
	input_field = document.getElementById("input_field");
	send_button = document.getElementById("send_button");

	input_field.addEventListener("keypress", handle_key_press, false);
	send_button.addEventListener("click", send_message, false);

	register_event();
}

window.addEventListener('load', init, false);
})();
