function add_system_utterance_to_chat(response_json) {
	const listItem = document.createElement('li');
	const aux_data = 'aux_data' in response_json ? JSON.stringify(response_json.aux_data) : ''
	listItem.textContent = "System: " + response_json.system_utterance + 
		"  [aux_data: " + aux_data + "]";
	document.getElementById('chat').appendChild(listItem);
}

function add_system_utterance_to_chat_and_save_session_id(response_json) {
	const listItem = document.createElement('li');
	const aux_data = 'aux_data' in response_json ? JSON.stringify(response_json.aux_data) : ''
	listItem.textContent = "System: " + response_json.system_utterance + 
		"  [aux_data: " + aux_data + "]";
	document.getElementById('chat').appendChild(listItem);
	sessionStorage.setItem('session_id', response_json.session_id);
}

function post_init() {
    const obj = {
        "user_id": document.getElementById("user_id").value
    };
	document.getElementById('chat').innerHTML = '';
	const method = "POST";
	const body = JSON.stringify(obj);
	const headers = {
	    'Accept': 'application/json',
	    'Content-Type': "application/json;charset=utf-8"
	    };
	fetch("./init", {method, headers, body})
	    .then(response => response.json())
	    .then(response_json => add_system_utterance_to_chat_and_save_session_id(response_json))
		.catch(console.error);
}

function post_user_utterance() {
	const session_id = sessionStorage.getItem("session_id");
	if (session_id === null) {
		window.alert("push \"start dialogue\" first.")
	}
    const user_id = document.getElementById('user_id').value;
    const user_utterance = document.getElementById('user_utterance').value;
	const aux_data = '{' + document.getElementById('aux_data').value + '}'
    try {
		// Check json formatting?
		JSON.parse(aux_data)
	} catch (e) {
		alert("Please set in JSON format.")
		return
	}
	const listItem = document.createElement('li');
    listItem.textContent = "User: " + user_utterance + "  [aux_data: " + aux_data + "]";
    document.getElementById('chat').appendChild(listItem);
    const obj = {
		"user_id" : user_id,
		"session_id" : session_id,
        "user_utterance": user_utterance,
        "aux_data": JSON.parse(aux_data)
    };
	const method = "POST";
	const body = JSON.stringify(obj);
	const headers = {
	    'Accept': 'application/json',
	    'Content-Type': "application/json;charset=utf-8"
	    };
	//fetch("./dialog", {method, headers, body}).then((res)=> res.json()).then(console.log).catch(console.error);
	fetch("./dialogue", {method, headers, body})
	    .then(response => response.json())
	    .then(response_json => add_system_utterance_to_chat(response_json))
        .catch(console.error);
	document.getElementById('user_utterance').value = "";
	document.getElementById('aux_data').value = "";

}

var input = document.getElementById("user_utterance");
input.addEventListener("keypress", function(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    document.getElementById("submit_button").click();
  }
});
