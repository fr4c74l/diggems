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

/* Based on the state of "user", updates the user interface. */
function auth_render() {
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
	victories_text += " (" + win_ratio + "%)";
    }
    victories.innerHTML = victories_text;
    points.innerHTML = user.stats.score;

    if (user.auth.fb) {
	fb_button.style.setProperty('display', 'none', null);
	logout.style.setProperty('visibility', 'visible', null);
    } else {
	fb_button.style.setProperty('display', 'inline-block', null);
	logout.style.setProperty('visibility', 'hidden', null);
    }
}

/* Updates the server with Facebook login info, and retrieves
 * correct auth information. */
function server_fb_login(fb_login)
{
    var request = new_post_request('/fb/login/')
    request.onreadystatechange = function(ev){
	if (request.readyState == 4) {
	    if(request.status == 200) {
		try {
		    user = JSON.parse(request.responseText);
		} catch(err) {
		    auth.fb = null;
		}
	    } else {
		auth.fb = null;
	    }

	    auth_render();
	}
    }
    request.send('token='+fb_login.accessToken);
}

/* Turn the player back into a guest user on server. */
function server_fb_logout()
{
    auth.fb = null;
    var request = new_post_request('/fb/logout/');
    request.send();
    auth_render();
}

/* Handle response from Facebook login events. */
function on_fb_login(res) {
  if(res.authResponse) {
      if(auth.fb && auth.fb.uid == res.authResponse.userID) {
	  auth_render();
      } else {
	  auth.fb = null;
	  server_fb_login(res.authResponse);
      }
  } else {
      if(auth.fb) {
	  server_fb_logout();
      } else {
	  auth_render();
      }
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
