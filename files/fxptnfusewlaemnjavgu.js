
		(function(c,h,a,f,i,e){ c[a]=c[a]||function(){ (c[a].q=c[a].q||[]).push(arguments)};
		 c[a].a=i;c[a].e=e;var g=h.createElement("script");g.async=true;g.type="text/javascript";
		g.src=f+'?aid='+i;var b=h.getElementsByTagName("script")[0];b.parentNode.insertBefore(g,b);
		})(window,document,"rtp","//abrtp1-cdn.marketo.com/rtp-api/v1/rtp.js","intermedia");
 
		rtp('send','view');
		rtp('get', 'campaign',true);