// Initially a copy of https://timbrady.org/turk/TimTurkTools.js, copied by Chaz Firestone on 2/24/16, last modified on 2/24/16

function GetWorkerId() {
	var workerId = turkGetParam( 'workerId', 'NONE' );
	return workerId;
}

function IsTurkPreview() {
	return GetWorkerId() == "NONE";
}

function IsOnTurk() {
  try {
    return ((window.location.host.indexOf('mturk')!=-1) || document.forms["mturk_form"] ||
      (top != self && window.parent.location.host.indexOf("mturk") != -1));
  } catch(err) {
    // insecure content trying to access https://turk probably, so say yes:
    return true;
  }
}

function GetAssignmentId() {
	var assignmentId = turkGetParam( 'assignmentId', 'NONE' );
	return assignmentId;
}

// Check if this worker's actual ID is on the block list or not
function CheckBlockList(blockListName, funcForBlocked) {
	if (!IsTurkPreview()) {
		$.ajax({
			crossDomain: true,
			dataType: 'jsonp',
			url: 'https://timbrady.org/turk/checkDuplicates.pl',
			data:{'workerId': GetWorkerId(),
			 'blockListName': blockListName},
			success: function(data) {
				$('#serverContacted').val(1);
				if (data.blocked == 1) {
					funcForBlocked();
				}
			},
			error: function(jx, status, error) {
				$('#serverContacted').val(0);
			}
		});
	}
}

function RandomOrder(num) {
  var order = new Array();
  for (var i=0; i<num; i++) {
    order.push(i);
  }
  return Shuffle(order);
}

Shuffle = function(o) {
	for(var j, x, i = o.length; i; j = parseInt(Math.random() * i), x = o[--i], o[i] = o[j], o[j] = x);
	return o;
};

//For todays date;
Date.prototype.today = function(){
    return ((this.getDate() < 10)?"0":"") + this.getDate() +"/"+(((this.getMonth()+1) < 10)?"0":"") + (this.getMonth()+1) +"/"+ this.getFullYear()
};
//For the time now
Date.prototype.timeNow = function(){
     return ((this.getHours() < 10)?"0":"") + this.getHours() +":"+ ((this.getMinutes() < 10)?"0":"") + this.getMinutes() +":"+ ((this.getSeconds() < 10)?"0":"") + this.getSeconds();
};

/**
 * Gets a URL parameter from the query string
 */
function turkGetParam( name, defaultValue ) {
   var regexS = "[\?&]"+name+"=([^&#]*)";
   var regex = new RegExp( regexS );
   var tmpURL = window.location.href;
   var results = regex.exec( tmpURL );
   if( results == null ) {
     return defaultValue;
   } else {
     return results[1];
   }
}

/**
 * URL decode a parameter
 */
function decode(strToDecode)
{
  var encoded = strToDecode;
  return unescape(encoded.replace(/\+/g,  " "));
}


/**
 * Returns the Mechanical Turk Site to post the HIT to (sandbox. prod)
 */
function turkGetSubmitToHost() {
  return decode(turkGetParam("turkSubmitTo", "https://www.mturk.com"));
}


/**
 * Sets the assignment ID in the form. Defaults to use mturk_form and submitButton
 */
function turkSetAssignmentID( form_name, button_name ) {

  if (form_name == null) {
    form_name = "mturk_form";
  }

  if (button_name == null) {
    button_name = "submitButton";
  }

  assignmentID = turkGetParam('assignmentId', "");
  document.getElementById('assignmentId').value = assignmentID;

  if (assignmentID == "ASSIGNMENT_ID_NOT_AVAILABLE") {
    // If we're previewing, disable the button and give it a helpful message
    btn = document.getElementById(button_name);
    if (btn) {
      btn.disabled = true;
      btn.value = "You must ACCEPT the HIT before you can submit the results.";
    }
  }

  form = document.getElementById(form_name);
  if (form) {
     form.action = turkGetSubmitToHost() + "/mturk/externalSubmit";
  }
}

/**
 * Port of the Python range() function. Copied by Chaz Firestone on 2/25/16 from http://underscorejs.org/docs/underscore.html
 */
function Range(start, stop, step) {
    if (stop == null) {
      stop = start || 0;
      start = 0;
    }
    step = step || 1;

    var length = Math.max(Math.ceil((stop - start) / step), 0);
    var rng = Array(length);

    for (var idx = 0; idx < length; idx++, start += step) {
      rng[idx] = start;
    }

    return rng;
};

/**
 * Get browser info, copied from https://css-tricks.com/snippets/jquery/display-browser-and-version/
 */
function getBrowser() {
	var userAgent = navigator.userAgent.toLowerCase(),
		browser   = '',
		version   = 0;

	$.browser.chrome = /chrome/.test(navigator.userAgent.toLowerCase());

	// Is this a version of IE?
	if ($.browser.msie) {
	  userAgent = $.browser.version;
	  userAgent = userAgent.substring(0,userAgent.indexOf('.'));
	  version = userAgent;
	  browser = "Internet Explorer";
	}

	// Is this a version of Chrome?
	if ($.browser.chrome) {
	  userAgent = userAgent.substring(userAgent.indexOf('chrome/') + 7);
	  userAgent = userAgent.substring(0,userAgent.indexOf('.'));
	  version = userAgent;
	  // If it is chrome then jQuery thinks it's safari so we have to tell it it isn't
	  $.browser.safari = false;
	  browser = "Chrome";
	}

	// Is this a version of Safari?
	if ($.browser.safari) {
	  userAgent = userAgent.substring(userAgent.indexOf('safari/') + 7);
	  userAgent = userAgent.substring(0,userAgent.indexOf('.'));
	  version = userAgent;
	  browser = "Safari";
	}

	// Is this a version of Mozilla?
	if ($.browser.mozilla) {
		//Is it Firefox?
		if (navigator.userAgent.toLowerCase().indexOf('firefox') != -1) {
			userAgent = userAgent.substring(userAgent.indexOf('firefox/') + 8);
			userAgent = userAgent.substring(0,userAgent.indexOf('.'));
			version = userAgent;
			browser = "Firefox"
		}
		// If not then it must be another Mozilla
		else {
		  browser = "Mozilla (not Firefox)"
		}
	}

	// Is this a version of Opera?
	if ($.browser.opera) {
		userAgent = userAgent.substring(userAgent.indexOf('version/') + 8);
		userAgent = userAgent.substring(0,userAgent.indexOf('.'));
		version = userAgent;
		browser = "Opera";
	}

	// Now you have two variables, browser and version
	// which have the right info

	return [browser,version];
}


/*
 * jQuery Hotkeys Plugin
 * Copyright 2010, John Resig
 * Dual licensed under the MIT or GPL Version 2 licenses.
 *
 * Based upon the plugin by Tzury Bar Yochay:
 * http://github.com/tzuryby/hotkeys
 *
 * Original idea by:
 * Binny V A, http://www.openjs.com/scripts/events/keyboard_shortcuts/
*/

(function(jQuery){

	jQuery.hotkeys = {
		version: "0.8",

		specialKeys: {
			8: "backspace", 9: "tab", 13: "return", 16: "shift", 17: "ctrl", 18: "alt", 19: "pause",
			20: "capslock", 27: "esc", 32: "space", 33: "pageup", 34: "pagedown", 35: "end", 36: "home",
			37: "left", 38: "up", 39: "right", 40: "down", 45: "insert", 46: "del",
			96: "0", 97: "1", 98: "2", 99: "3", 100: "4", 101: "5", 102: "6", 103: "7",
			104: "8", 105: "9", 106: "*", 107: "+", 109: "-", 110: ".", 111 : "/",
			112: "f1", 113: "f2", 114: "f3", 115: "f4", 116: "f5", 117: "f6", 118: "f7", 119: "f8",
			120: "f9", 121: "f10", 122: "f11", 123: "f12", 144: "numlock", 145: "scroll", 191: "/", 224: "meta"
		},

		shiftNums: {
			"`": "~", "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&",
			"8": "*", "9": "(", "0": ")", "-": "_", "=": "+", ";": ": ", "'": "\"", ",": "<",
			".": ">",  "/": "?",  "\\": "|"
		}
	};

	function keyHandler( handleObj ) {
		// Only care when a possible input has been specified
		if ( typeof handleObj.data !== "string" ) {
			return;
		}

		var origHandler = handleObj.handler,
			keys = handleObj.data.toLowerCase().split(" ");

		handleObj.handler = function( event ) {
			// Don't fire in text-accepting inputs that we didn't directly bind to
			if ( this !== event.target && (/textarea|select/i.test( event.target.nodeName ) ||
				 event.target.type === "text") ) {
				return;
			}

			// Keypress represents characters, not special keys
			var special = event.type !== "keypress" && jQuery.hotkeys.specialKeys[ event.which ],
				character = String.fromCharCode( event.which ).toLowerCase(),
				key, modif = "", possible = {};

			// check combinations (alt|ctrl|shift+anything)
			if ( event.altKey && special !== "alt" ) {
				modif += "alt+";
			}

			if ( event.ctrlKey && special !== "ctrl" ) {
				modif += "ctrl+";
			}

			// TODO: Need to make sure this works consistently across platforms
			if ( event.metaKey && !event.ctrlKey && special !== "meta" ) {
				modif += "meta+";
			}

			if ( event.shiftKey && special !== "shift" ) {
				modif += "shift+";
			}

			if ( special ) {
				possible[ modif + special ] = true;

			} else {
				possible[ modif + character ] = true;
				possible[ modif + jQuery.hotkeys.shiftNums[ character ] ] = true;

				// "$" can be triggered as "Shift+4" or "Shift+$" or just "$"
				if ( modif === "shift+" ) {
					possible[ jQuery.hotkeys.shiftNums[ character ] ] = true;
				}
			}

			for ( var i = 0, l = keys.length; i < l; i++ ) {
				if ( possible[ keys[i] ] ) {
					return origHandler.apply( this, arguments );
				}
			}
		};
	}

	jQuery.each([ "keydown", "keyup", "keypress" ], function() {
		jQuery.event.special[ this ] = { add: keyHandler };
	});

})( jQuery );
