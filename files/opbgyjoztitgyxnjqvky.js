
			function loadScriptAsync(url, callback, id) { 

				var script = document.createElement("script")
				script.type = "text/javascript";

				// Some scripts require id's
				if (typeof id !== "undefined") { 
					script.id = id;
				}

				// if we have a callback, let's run it after the script is loaded
				if (typeof callback === "function") { 
					if (script.readyState) {   //For IE
						script.onreadystatechange = function() { 
							if (script.readyState == "loaded" || script.readyState == "complete") { 
								script.onreadystatechange = null;
								callback();
							}
						};
					} else {   //Other browsers
						script.onload = function() { 
							callback();
						};
					}
				}

				script.src = url;
				document.body.appendChild(script);
			}