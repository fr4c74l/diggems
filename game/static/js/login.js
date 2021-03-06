// Copyright 2011 Lucas Clemente Vella
// Software distributed under Affero GPL, see http://gnu.org/licenses/agpl.txt

/* Return XmlHttpRequest object ready for POST. */
function new_post_request(url) {
    var request = new XMLHttpRequest();
    request.open('POST', url, true);
    request.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    return request;
}

String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

function is_fb_auth() {
    return auth && auth.fb;
}

/* Based on the state of "user", updates the user interface. */
function user_info_render(user) {
    var fb_button = document.getElementById('auth_fb_button');
    var username = document.getElementById('auth_username');
    var victories = document.getElementById('_victories');
    var points = document.getElementById('_points');

    var picture = document.getElementById('auth_user_pic');
    var logout = document.getElementById('auth_logout');

    username.innerHTML = user.name.capitalize();
    picture.src = user.pic_url;

    var victories_text = user.stats.victories;
    if (user.stats.win_ratio) {
	victories_text += " (" + user.stats.win_ratio + "%)";
    }
    victories.innerHTML = victories_text;
    points.innerHTML = user.stats.score;

    if (is_fb_auth()) {
	fb_button.style.setProperty('display', 'none', null);
	logout.style.setProperty('visibility', 'visible', null);
    } else {
	fb_button.style.setProperty('display', 'inline-block', null);
	logout.style.setProperty('visibility', 'hidden', null);
    }
}

var on_login_callback = null;

/* Handle event from server login/out response. */
function server_handle_response(ev) {
    if (ev.target.readyState == 4) {
        if(ev.target.status == 200) {
	    var user = JSON.parse(ev.target.responseText);
	    auth = user.auth ? user.auth : null;
	    user_info_render(user);
	    if (on_login_callback) {
		on_login_callback();
	    }
	}
    }
}

/* Updates the server with Facebook login info, and retrieves
 * correct auth information. */
function server_fb_login(fb_login)
{
    var request = new_post_request('/fb/login/')
    request.onreadystatechange = server_handle_response;
    request.send('token='+fb_login.accessToken);
}

/* Turn the player back into a guest user on server. */
function server_fb_logout()
{
    var request = new_post_request('/fb/logout/');
    request.onreadystatechange = server_handle_response;
    request.send();
}

/* Handle response from Facebook login events. */
function on_fb_login(res) 
{
	if(res.authResponse) 
	{
		if(!is_fb_auth() || auth.fb.uid != res.authResponse.userID) 
		{
			server_fb_login(res.authResponse);
		}
	}
	else if(is_fb_auth())
	{
		server_fb_logout();
	}
}

/* Button callback to logout the user. */
function fb_logout() {
    if(FB) {
	FB.logout();
	server_fb_logout();
    } else {
	// Retry in half second...
	setTimeout(fb_logout, 500);
    }
}
