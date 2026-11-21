.pragma library

// The logout screen has a window on every screen. A key pressed on any of them
// stops the countdown on all of them, so this is shared between the windows.

var stops = [];

function onKey(stop) {
    stops.push(stop);
}

function keyPressed() {
    stops.forEach(function (stop) {
        if (stop) {
            stop();
        }
    });
}
