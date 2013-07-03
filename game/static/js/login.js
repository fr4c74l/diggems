// Copyright 2011 Lucas Clemente Vella
// Software distributed under Affero GPL, see http://gnu.org/licenses/agpl.txt

/* Return XmlHttpRequest object ready for POST. */
function new_post_request(url) {
    var request = new XMLHttpRequest();
    request.open('POST', url, true);
    request.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    return request;
}

/* Based on the state of "auth", updates the user interface. */
function auth_render() {
    var fb_button = document.getElementById('auth_fb_button');
    var username = document.getElementById('auth_username');
    var picture = document.getElementById('auth_user_pic');
    var logout = document.getElementById('auth_logout')

    if(auth.fb) {
	username.innerHTML = auth.fb.name;

	picture.src = 'https://graph.facebook.com/' + auth.fb.uid + '/picture';
	picture.style.setProperty('visibility', 'visible', null);

	fb_button.style.setProperty('display', 'none', null);
	logout.style.setProperty('visibility', 'visible', null);
    } else {
	username.innerHTML = 'Visitante';

	picture.style.setProperty('visibility', 'hidden', null);
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
		    auth.fb = JSON.parse(request.responseText);
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
    FB.logout();
    server_fb_logout();
}

/* Initial check of login status. */
window.addEventListener('load', function() {
    FB.Event.subscribe('auth.authResponseChange', on_fb_login);
}, false);
