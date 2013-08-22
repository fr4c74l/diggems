function accept_terms() {
	var agreed = document.getElementById('agreed');
	var code = document.getElementById('code');
	code.style.visibility = agreed.checked ? 'visible' : 'hidden';
}
accept_terms();
