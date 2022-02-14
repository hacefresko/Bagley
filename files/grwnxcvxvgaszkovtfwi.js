/**
  2012-04-13
  Created by Konstantin Ermakov <kermakov@intermedia.net> to track views of YouTube videos on the website.
  2012-06-01
  Updated by Maria Golubeva <mgolubeva@intermedia.net> to track views of YouTube videos on the website.
  **/
/* function to embed video */

var tag = document.createElement('script');
tag.src = "https://www.youtube.com/player_api";
var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag); 
var YTState = [],YTTime = [],players = [];
var YTSt={'-1':'Unstarted',0:'Ended',1:'Playing',2:'Paused'};

var tmt;
var addTracking = function() {
	if ($('.fancybox-iframe').length > 0 && $('.fancybox-opened').length > 0) {
		if ($('.fancybox-iframe').attr('src').indexOf('vimeo') > -1) return;
		if ($('.fancybox-iframe').attr('src').indexOf('http') < 0 && $('.fancybox-iframe').attr('src').indexOf('https') < 0) {
			$('.fancybox-iframe').attr('src', 'https:' + $('.fancybox-iframe').attr('src'));
		}
		clearTimeout(tmt);
		var video = $('.fancybox-iframe');
		var hr = video.attr('src').split('/'); 
		var url = hr[4];
		var idL = url.indexOf('?') >= 0 ? url.indexOf('?') : url.length;
		var id = url.substr(0, idL);
		var width = video.width();
		var height = video.height();
		var iframeId = video.attr('id');
		$('.fancybox-inner').html('<div data-ytid="'+ id +'"></div>');
		players[id] = new YT.Player($('div[data-ytid="'+id+'"]')[0], {
			videoId: id,
			width: width,
			height: height,
			playerVars: {
				'autoplay': 1,
				'autohide': 1,
				'controls': 1,
				'modestbranding': 1,
				'showinfo' : 0,
				'theme' : 'light',
				'rel' : 0,
				'wmode' : 'opaque'
			},
			events: {
				'onReady': function() {
					YTState[id]=-1; YTTime[id]=0; 
				},
				'onStateChange': function (e){
					if(e.data>-1 & e.data<3 & e.data!=YTState[YTState[id]]){
						ga("send", "event", "YouTube", e.target.getVideoUrl()+': '+YTSt[YTState[id]]+' -> '+YTSt[e.data], YTTime[id]+'-'+e.target.getCurrentTime());
						YTState[id]=e.data;
						YTTime[id]=e.target.getCurrentTime();
					}
				}
			}
		});
		$('iframe[data-ytid="'+id+'"]').addClass('fancybox-iframe');
		$('iframe[data-ytid="'+id+'"]').attr('id', iframeId);
		$('iframe[data-ytid="'+id+'"]').attr('name', iframeId);
		$('iframe[data-ytid="'+id+'"]').attr('scrolling', 'auto');
		$('iframe[data-ytid="'+id+'"]').attr('hspace', 0);
		$('iframe[data-ytid="'+id+'"]').attr('vspace', 0);
		$('.fancybox-close').click(function(){
			delete players[id];
		});
	} else {
		tmt = setTimeout('addTracking()', 200);
	}
};

function trackVideo(videoContainer) {
	var video = videoContainer.children('iframe').first();
	// Make sure video contains elements before moving on to prevent errors.
	if (video.length) {
		var hr = video.attr('src').split('/'); 
		var url = hr[4];
		var idL = url.indexOf('?') >= 0 ? url.indexOf('?') : url.length;
		var id = url.substr(0, idL);
		var width = video.width();
		var height = video.height();
		// Let's get any divs and classes that the container had
		var containerID = (typeof video.attr('id') !== "undefined" ? video.attr('id') : "");
		var containerClasses = (typeof video.attr('class') !== "undefined" ? video.attr('class') : "");

		videoContainer.html('<div id="'+ containerID +'" class="'+ containerClasses +'" data-ytid="'+ id +'"></div>');
		players[id] = new YT.Player($('div[data-ytid="'+id+'"]')[0], {
			videoId: id,
			width: width,
			height: height,
			playerVars: { 'controls': 1, 'modestbranding': 1, 'showinfo' : 0, 'theme' : 'light', 'rel' : 0 },
			events: {
				'onReady': function() {
					YTState[id]=-1; YTTime[id]=0; 
				},
				'onStateChange': function (e) {
					if(e.data>-1 & e.data<3 & e.data!=YTState[YTState[id]]) {
						ga("send", "event", "YouTube", e.target.getVideoUrl()+': '+YTSt[YTState[id]]+' -> '+YTSt[e.data], YTTime[id]+'-'+e.target.getCurrentTime());
						YTState[id]=e.data;
						YTTime[id]=e.target.getCurrentTime();
					}
				}
			}
	  	});
	}
}

function onYouTubePlayerAPIReady() {
	function onTimer() {
		$(document).ready(function () {
			var videoContainer = $('.video-container');
			var videoContainer1 = $('.video-tracking');

			videoContainer.each(function () {
				trackVideo($(this));
			});

			videoContainer1.each(function () {
				trackVideo($(this));
			});

			if ($('.fancybox-media').length) {
				$('.fancybox-media').click(function (e) {
					addTracking();
				});
			}
		});
	}

	if (window.JQuery) {
		onTimer();
	} else {
		setTimeout(onYouTubePlayerAPIReady, 50);
	}
}

/* function to embed video */
  