jQuery(document).ready(function($) {
    var status_ws = new ReconnectingWebSocket(ws_uri);
    status_ws.onmessage = receiveMessage;
    status_ws.onopen =  on_connected;
    status_ws.onclose = on_disconnected;
    // attach this function to an event handler on your site
    function sendMessage(msg) {
        status_ws.send(JSON.stringify(msg));
    }

    function on_connected() {
        console.info('connected.');
    }

    function on_disconnected(evt) {
        console.info('disconnected.');
        //===to do====
        //Need to produce some colour indication on screen to display this
    }

    // receive a message though the websocket from the server
    function receiveMessage(event) {
        msg = event.data;
        console.info('recieved: '+ msg);
        msg = JSON.parse(msg); //expecting JSON msg
        if(msg.msg_type='notice')
        switch(msg.context) {
            case 'download-data':
                //handle data updates
                updateDownloadStatus(msg)
                break;
            //in the future we can have other update type
        }
    }

var downloadStatus = {};
var indeterminateProgress = undefined;
get_status_update = function(status) {
    switch(status) {
        case 'DONE':
            return 1;
        case 'WIP':
            return 0;
        default:
            return -1;
    };
};
updateDownloadStatus = function(msg) {
    var status_msg = $('#status-msg');
    if(msg.expired)
        return status_msg.html('...');
    //handle status update on screen
    status_update = get_status_update(msg.status);
    present_status = get_status_update(downloadStatus[msg.context_id]); //naturally defaults to -1 if undefined
    if(status_update > present_status) {
        var status_bar = $('#status-bar');
        status_bar.show();
        switch(msg.status){
            case 'WIP':
                status_msg.html(msg.content);
                var intObj = {
                  template: 3,
                  parent: '#status-bar' // this option will insert bar HTML into this parent Element
                };
                indeterminateProgress = new Mprogress(intObj);
                indeterminateProgress.start();
                break;
            case 'DONE':
                if(indeterminateProgress != undefined)
                    indeterminateProgress.end();
                status_msg.html('<a href="' + msg.content +'" class="blue">download-' + msg.description + '</a>');
        };
    };

    downloadStatus[msg.context_id] = msg.status;
};


});

